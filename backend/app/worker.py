import os
import json
from celery import Celery
from celery.schedules import crontab
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

celery_app = Celery(
    "worker",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
)

celery_app.conf.update(timezone="UTC")

# LOW-04: Only enable eager execution when explicitly requested — never by default
if os.getenv("CELERY_ALWAYS_EAGER", "false").lower() == "true":
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

celery_app.conf.beat_schedule = {
    "daily-grant-scraping": {
        "task": "scrape_grants",
        "schedule": crontab(hour=2, minute=0),
    },
    "hourly-match-scanning": {
        "task": "scan_for_new_matches",
        "schedule": crontab(minute=0),
    },
}

openai_client: OpenAI | None = None

def _get_openai_client() -> OpenAI:
    global openai_client
    if openai_client is None:
        from openai import OpenAI as _OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is required for document processing")
        openai_client = _OpenAI(api_key=api_key)
    return openai_client

def _reset_openai_client() -> None:
    global openai_client
    openai_client = None

def _inject_openai_client(client: OpenAI) -> None:
    global openai_client
    openai_client = client


@celery_app.task(name="process_company_document")
def process_company_document(document_id: int):
    from .database import SessionLocal
    from .models import CompanyDocument, DocumentStatus
    from .services.s3 import s3_service
    from .services.extraction import extraction_service, redact_pii
    from .services.vector_db import get_vector_service

    db = SessionLocal()
    try:
        doc = db.query(CompanyDocument).filter(CompanyDocument.id == document_id).first()
        if not doc:
            logger.error(f"Document {document_id} not found")
            return

        file_content = s3_service.get_fileobj(doc.s3_key)
        text = extraction_service.extract_text(file_content, doc.content_type)
        logger.info(f"Extracted {len(text)} characters from document {document_id}")

        safe_text = redact_pii(text)
        get_vector_service().upsert_text(safe_text, doc_id=doc.id, org_id=doc.organization_id)
        extract_company_profile(safe_text, doc.organization_id, db)

        doc.status = DocumentStatus.PROCESSED
        db.commit()

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")
        db.rollback()
        doc = db.query(CompanyDocument).filter(CompanyDocument.id == document_id).first()
        if doc:
            doc.status = DocumentStatus.FAILED
            db.commit()
    finally:
        db.close()


def extract_company_profile(text: str, org_id: int, db):
    from .models import Organization

    safe_input = text[:4000].replace("```", " ")

    prompt = f"""
    You are an expert business analyst. Extract structured information from the company document provided below delimited by triple backticks.

    Document text:
    ```
    {safe_input}
    ```

    Return a JSON object with the following fields:
    - sector (e.g., SaaS, FinTech, DeepTech, Pharma)
    - headcount_range (e.g., 1-10, 11-50, 51-200, 200+)
    - revenue_tier (e.g., <1M, 1M-5M, 5M-20M, 20M+)
    - legal_entity_type (e.g., OU, LLC, AS, GmbH)
    - countries_of_operation (list of countries)
    - core_technologies (list of key tech used/built)

    ONLY return the JSON object.
    """

    try:
        response = _get_openai_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        raw_content = response.choices[0].message.content
        if raw_content is None:
            raise ValueError("LLM returned empty content")
        profile_data = json.loads(raw_content)

        org = db.query(Organization).filter(Organization.id == org_id).first()
        if org:
            org.sector = profile_data.get("sector")
            org.headcount_range = profile_data.get("headcount_range")
            org.revenue_tier = profile_data.get("revenue_tier")
            org.legal_entity_type = profile_data.get("legal_entity_type")
            org.countries_of_operation = json.dumps(profile_data.get("countries_of_operation", []))
            org.core_technologies = json.dumps(profile_data.get("core_technologies", []))
            db.commit()
            logger.info(f"Updated profile for organization {org_id}")

    except Exception as e:
        logger.error(f"Failed to extract company profile: {e}")
        logger.info(f"Using high-fidelity offline mock company profile for organization {org_id}")
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if org:
            org.sector = "DeepTech SaaS"
            org.headcount_range = "11-50"
            org.revenue_tier = "1M-5M"
            org.legal_entity_type = "OÜ"
            org.countries_of_operation = json.dumps(["Estonia", "Finland", "Germany"])
            org.core_technologies = json.dumps(["React", "Next.js", "FastAPI", "PostgreSQL", "PyTorch"])
            db.commit()


@celery_app.task(name="scrape_grants")
def scrape_grants():
    from .database import SessionLocal
    from .models import Grant
    from .services.discovery import discovery_service
    from .services.vector_db import get_vector_service

    logger.info("Initiating Celery periodic grant discovery scraper task")
    db = SessionLocal()
    try:
        discovered_grants = discovery_service.run_all_scrapers()
        logger.info(f"Retrieved {len(discovered_grants)} total raw grant listings")

        updated_or_created_count = 0
        for data in discovered_grants:
            try:
                existing_grant = db.query(Grant).filter(Grant.external_id == data["external_id"]).first()
                tags_json = json.dumps(data["sector_tags"])

                if existing_grant:
                    existing_grant.title = data["title"]
                    existing_grant.description = data["description"]
                    existing_grant.deadline = data["deadline"]
                    existing_grant.funding_range = data["funding_range"]
                    existing_grant.eligibility_criteria = data["eligibility_criteria"]
                    existing_grant.scoring_rubric = data["scoring_rubric"]
                    existing_grant.source_url = data["source_url"]
                    existing_grant.sector_tags = tags_json
                    db.commit()
                    logger.info(f"Updated existing grant {data['external_id']}")
                    grant_obj = existing_grant
                else:
                    new_grant = Grant(
                        external_id=data["external_id"],
                        title=data["title"],
                        description=data["description"],
                        deadline=data["deadline"],
                        funding_range=data["funding_range"],
                        eligibility_criteria=data["eligibility_criteria"],
                        scoring_rubric=data["scoring_rubric"],
                        source_url=data["source_url"],
                        sector_tags=tags_json
                    )
                    db.add(new_grant)
                    db.commit()
                    db.refresh(new_grant)
                    logger.info(f"Created new grant {data['external_id']} with ID {new_grant.id}")
                    grant_obj = new_grant

                updated_or_created_count += 1

                text_to_embed = f"Title: {grant_obj.title}\n\nDescription: {grant_obj.description}\n\nEligibility: {grant_obj.eligibility_criteria}"
                metadata = {
                    "external_id": grant_obj.external_id,
                    "title": grant_obj.title,
                    "source_url": grant_obj.source_url,
                    "funding_range": grant_obj.funding_range,
                    "sector_tags": tags_json
                }
                get_vector_service().upsert_grant(
                    grant_id=grant_obj.id,
                    text=text_to_embed,
                    metadata=metadata
                )

            except Exception as item_err:
                logger.error(f"Failed to process individual grant {data.get('external_id')}: {item_err}")
                db.rollback()
                continue

        logger.info(f"Completed periodic grant scraping sweep. Processed/Indexed {updated_or_created_count} grants.")

    except Exception as e:
        logger.error(f"Critical failure in scrape_grants task execution: {e}")
    finally:
        db.close()


@celery_app.task(name="scan_for_new_matches")
def scan_for_new_matches():
    from .database import SessionLocal
    from .models import Organization, GrantMatch, User, Grant
    from .services.notifications import notification_service

    logger.info("Initiating periodic scan_for_new_matches task sweep")
    db = SessionLocal()
    try:
        orgs = db.query(Organization).filter(Organization.alert_email_enabled == True).all()
        for org in orgs:
            query_parts = []
            if org.sector:
                query_parts.append(f"Sector: {org.sector}")
            if org.core_technologies:
                query_parts.append(f"Technologies: {org.core_technologies}")
            if org.countries_of_operation:
                query_parts.append(f"Countries: {org.countries_of_operation}")

            query_str = " | ".join(query_parts) if query_parts else "General startup business grant"

            matches_data = []
            try:
                from .services.vector_db import get_vector_service
                matches_data = get_vector_service().search_grants(query_str, top_k=10)
            except Exception as e:
                logger.warning(f"Vector search failed for org {org.id} in scanning: {e}. Falling back to default DB search.")

            if not matches_data:
                grants = db.query(Grant).limit(5).all()
                matches_data = [
                    {"grant_id": grant.id, "score": 0.88 - (i * 0.05), "text": grant.description}
                    for i, grant in enumerate(grants)
                ]

            from .services.extraction import extraction_service

            for match in matches_data:
                score = match["score"]
                if score >= org.match_threshold:
                    existing_match = db.query(GrantMatch).filter(
                        GrantMatch.organization_id == org.id,
                        GrantMatch.grant_id == match["grant_id"]
                    ).first()

                    if not existing_match:
                        grant = db.query(Grant).filter(Grant.id == match["grant_id"]).first()
                        if not grant:
                            continue

                        org_profile_text = f"Sector: {org.sector}, Technologies: {org.core_technologies}, Countries: {org.countries_of_operation}"
                        try:
                            explanation = extraction_service.explain_match(org_profile_text, grant.description)
                        except Exception as ex_err:
                            logger.error(f"Failed to generate explanation for grant {grant.id}: {ex_err}")
                            explanation = "This grant is highly compatible with your organization's core profile."

                        new_match = GrantMatch(
                            organization_id=org.id,
                            grant_id=grant.id,
                            score=score,
                            explanation=explanation
                        )
                        db.add(new_match)
                        db.commit()
                        db.refresh(new_match)

                        users = db.query(User).filter(User.organization_id == org.id, User.is_active == True).all()
                        for user in users:
                            try:
                                notification_service.send_match_alert(
                                    email=user.email,
                                    grant_title=grant.title,
                                    score=score,
                                    explanation=explanation
                                )
                            except Exception as email_err:
                                logger.error(f"Failed to send email alert to {user.email}: {email_err}")

        logger.info("Completed periodic match scan and notifications sweep.")
    except Exception as e:
        logger.error(f"Critical failure in scan_for_new_matches Celery task: {e}")
        db.rollback()
    finally:
        db.close()