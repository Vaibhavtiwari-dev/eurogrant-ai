import logging
import uuid
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any, cast

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..auth import get_current_user, require_role
from ..errors import error_response
from ..limiter import limiter
from ..services.proposal_content import (
    InvalidTipTapDocument,
    markdown_to_tiptap,
    rebuild_proposal_content,
    validate_and_normalize_tiptap_document,
)
from ..services.proposal_export import ExportSection, generate_docx, generate_pdf
from ..worker import generate_proposal_task, regenerate_proposal_section_task

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/proposals",
    tags=["Proposals"],
)

# Tier → monthly proposal limit lookup
_MONTHLY_LIMITS: dict[str, int | None] = {
    "growth": 5,
    "scale": 15,
    "agency": None,  # unlimited
}

_TRACKING_TRANSITIONS: dict[models.ApplicationStatus, set[models.ApplicationStatus]] = {
    models.ApplicationStatus.DRAFT: {
        models.ApplicationStatus.SUBMITTED,
        models.ApplicationStatus.WITHDRAWN,
    },
    models.ApplicationStatus.SUBMITTED: {
        models.ApplicationStatus.DRAFT,
        models.ApplicationStatus.WON,
        models.ApplicationStatus.LOST,
        models.ApplicationStatus.WITHDRAWN,
    },
    models.ApplicationStatus.WON: {models.ApplicationStatus.DRAFT},
    models.ApplicationStatus.LOST: {models.ApplicationStatus.DRAFT},
    models.ApplicationStatus.WITHDRAWN: {models.ApplicationStatus.DRAFT},
}


def _usage_limit_for_tier(tier: str) -> int | None:
    """Return the monthly proposal cap for a subscription tier, or ``None`` if unlimited."""
    return _MONTHLY_LIMITS.get(tier.lower(), 5)


def _count_monthly_proposals(db: Session, org_id: int) -> int:
    """Count how many proposals this org has created in the current calendar month."""
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        db.query(func.count(models.Proposal.id))
        .filter(
            models.Proposal.organization_id == org_id,
            models.Proposal.created_at >= month_start,
        )
        .scalar()
        or 0
    )


def _get_scoped_proposal(db: Session, proposal_id: int, organization_id: int | None):
    if organization_id is None:
        error_response("FORBIDDEN", "You are not assigned to an organisation.", status_code=403)
    proposal = (
        db.query(models.Proposal)
        .filter(
            models.Proposal.id == proposal_id,
            models.Proposal.organization_id == organization_id,
        )
        .first()
    )
    if not proposal:
        error_response("NOT_FOUND", f"Proposal with id {proposal_id} not found.", status_code=404)
    return proposal


def _get_scoped_section(
    db: Session, proposal_id: int, section_id: int, organization_id: int | None
):
    if organization_id is None:
        error_response("FORBIDDEN", "You are not assigned to an organisation.", status_code=403)
    section = (
        db.query(models.ProposalSection)
        .join(models.Proposal)
        .filter(
            models.ProposalSection.id == section_id,
            models.ProposalSection.proposal_id == proposal_id,
            models.Proposal.organization_id == organization_id,
        )
        .first()
    )
    if not section:
        error_response(
            "NOT_FOUND", f"Proposal section with id {section_id} not found.", status_code=404
        )
    return section


@router.post("/", response_model=schemas.ProposalOut, status_code=202)
@limiter.limit("5/minute")
def create_proposal(
    request: Request,
    payload: schemas.ProposalCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(
        require_role([models.RoleEnum.ADMIN, models.RoleEnum.WRITER])
    ),
) -> models.Proposal:
    """Trigger a new proposal generation for a grant.

    Validates the organisation's subscription usage limit (FR-21) before
    queueing the async Celery task.  Returns ``202 Accepted`` immediately
    with the proposal record; the actual generation runs in the background.
    """
    org_id = current_user.organization_id
    if not org_id:
        error_response("FORBIDDEN", "You are not assigned to an organisation.", status_code=403)

    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not org:
        error_response("NOT_FOUND", "Organisation not found.", status_code=404)

    # --- Validate the grant exists ---
    grant = db.query(models.Grant).filter(models.Grant.id == payload.grant_id).first()
    if not grant:
        error_response("NOT_FOUND", f"Grant with id {payload.grant_id} not found.", status_code=404)

    # --- Enforce usage limits (FR-21) ---
    limit = _usage_limit_for_tier(org.subscription_tier)
    if limit is not None:
        used = _count_monthly_proposals(db, org_id)
        if used >= limit:
            error_response(
                "USAGE_LIMIT",
                f"Monthly proposal limit of {limit} reached for your {org.subscription_tier} tier. "
                "Upgrade to continue generating proposals.",
                status_code=403,
            )

    # --- Create the proposal record (status = PENDING) ---
    proposal = models.Proposal(
        organization_id=org_id,
        grant_id=payload.grant_id,
        status=models.ProposalStatus.PENDING,
        generation_job_id=str(uuid.uuid4()),
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    # --- Dispatch the async Celery task ---
    try:
        cast(Any, generate_proposal_task).delay(proposal.id, proposal.generation_job_id)
        logger.info("Queued generate_proposal_task for proposal %d", proposal.id)
    except Exception as e:
        logger.error(
            "Failed to queue proposal generation task for proposal %d: %s",
            proposal.id,
            e,
        )
        # The proposal stays PENDING; a subsequent remediation flow could re-queue it.

    return proposal


@router.get("/", response_model=list[schemas.ProposalOut])
def list_proposals(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[models.Proposal]:
    """List all proposals belonging to the current user's organisation."""
    proposals = (
        db.query(models.Proposal)
        .filter(models.Proposal.organization_id == current_user.organization_id)
        .order_by(models.Proposal.created_at.desc())
        .all()
    )
    return proposals


@router.get("/{proposal_id}", response_model=schemas.ProposalOut)
def get_proposal(
    proposal_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Proposal:
    """Retrieve a single proposal by its ID (organisation-scoped)."""
    return _get_scoped_proposal(db, proposal_id, current_user.organization_id)


@router.patch("/{proposal_id}", response_model=schemas.ProposalOut)
def update_proposal_tracking(
    proposal_id: int,
    payload: schemas.ProposalTrackingUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(
        require_role([models.RoleEnum.ADMIN, models.RoleEnum.WRITER])
    ),
) -> models.Proposal:
    proposal = _get_scoped_proposal(db, proposal_id, current_user.organization_id)
    if payload.application_status == proposal.application_status:
        return proposal
    allowed = _TRACKING_TRANSITIONS[proposal.application_status]
    if payload.application_status not in allowed:
        error_response(
            "INVALID_STATUS_TRANSITION",
            (
                f"Cannot change application status from {proposal.application_status.value} "
                f"to {payload.application_status.value}."
            ),
            status_code=409,
        )
    proposal.application_status = payload.application_status
    if payload.application_status == models.ApplicationStatus.SUBMITTED:
        proposal.submitted_at = datetime.now(UTC)
    elif payload.application_status == models.ApplicationStatus.DRAFT:
        proposal.submitted_at = None
    db.commit()
    db.refresh(proposal)
    return proposal


@router.get(
    "/{proposal_id}/feedback",
    response_model=list[schemas.ProposalFeedbackOut],
)
def list_proposal_feedback(
    proposal_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[models.ProposalFeedback]:
    _get_scoped_proposal(db, proposal_id, current_user.organization_id)
    return (
        db.query(models.ProposalFeedback)
        .filter(models.ProposalFeedback.proposal_id == proposal_id)
        .order_by(models.ProposalFeedback.created_at.desc())
        .all()
    )


@router.post(
    "/{proposal_id}/feedback",
    response_model=schemas.ProposalFeedbackOut,
    status_code=201,
)
@limiter.limit("5/minute")
def create_proposal_feedback(
    request: Request,
    proposal_id: int,
    payload: schemas.ProposalFeedbackCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.ProposalFeedback:
    proposal = _get_scoped_proposal(db, proposal_id, current_user.organization_id)
    if proposal.status not in {
        models.ProposalStatus.COMPLETED,
        models.ProposalStatus.COMPLETED_WITH_ERRORS,
    }:
        error_response(
            "PROPOSAL_NOT_READY",
            "Feedback can be submitted after proposal generation finishes.",
            status_code=409,
        )
    today = datetime.now(UTC).date()
    week_start = today - timedelta(days=today.weekday())
    feedback = models.ProposalFeedback(
        proposal_id=proposal.id,
        user_id=current_user.id,
        week_start=week_start,
        rating=payload.rating,
        comments=payload.comments,
    )
    db.add(feedback)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        error_response(
            "WEEKLY_FEEDBACK_EXISTS",
            "You have already submitted feedback for this proposal this week.",
            status_code=409,
        )
    db.refresh(feedback)
    return feedback


@router.get("/{proposal_id}/export/{export_format}")
@limiter.limit("10/minute")
def export_proposal(
    request: Request,
    proposal_id: int,
    export_format: str,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
) -> StreamingResponse:
    proposal = _get_scoped_proposal(db, proposal_id, current_user.organization_id)
    normalized_format = export_format.lower()
    if normalized_format not in {"pdf", "docx"}:
        error_response(
            "UNSUPPORTED_EXPORT_FORMAT",
            "Supported export formats are pdf and docx.",
            status_code=404,
        )
    sections = (
        db.query(models.ProposalSection)
        .filter(models.ProposalSection.proposal_id == proposal.id)
        .order_by(models.ProposalSection.order, models.ProposalSection.id)
        .all()
    )
    export_sections = [
        ExportSection(name=section.name, content_json=section.content_json) for section in sections
    ]
    if not export_sections and proposal.content:
        export_sections = [
            ExportSection(
                name="Proposal",
                content_json=markdown_to_tiptap(proposal.content),
            )
        ]
    if not export_sections:
        error_response(
            "PROPOSAL_NOT_READY",
            "The proposal has no content to export.",
            status_code=409,
        )

    if normalized_format == "pdf":
        content = generate_pdf(proposal.id, proposal.grant.title, export_sections)
        media_type = "application/pdf"
    else:
        content = generate_docx(proposal.id, proposal.grant.title, export_sections)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    filename = f"eurogrant-proposal-{proposal.id}.{normalized_format}"
    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
        },
    )


@router.get("/{proposal_id}/sections", response_model=list[schemas.ProposalSectionOut])
def list_proposal_sections(
    proposal_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[models.ProposalSection]:
    _get_scoped_proposal(db, proposal_id, current_user.organization_id)
    return (
        db.query(models.ProposalSection)
        .filter(models.ProposalSection.proposal_id == proposal_id)
        .order_by(models.ProposalSection.order, models.ProposalSection.id)
        .all()
    )


@router.get("/{proposal_id}/sections/{section_id}", response_model=schemas.ProposalSectionOut)
def get_proposal_section(
    proposal_id: int,
    section_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.ProposalSection:
    return _get_scoped_section(db, proposal_id, section_id, current_user.organization_id)


@router.patch("/{proposal_id}/sections/{section_id}", response_model=schemas.ProposalSectionOut)
def update_proposal_section(
    proposal_id: int,
    section_id: int,
    payload: schemas.ProposalSectionUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(
        require_role([models.RoleEnum.ADMIN, models.RoleEnum.WRITER])
    ),
) -> models.ProposalSection:
    _get_scoped_section(db, proposal_id, section_id, current_user.organization_id)
    try:
        normalized = validate_and_normalize_tiptap_document(payload.content_json)
    except InvalidTipTapDocument as exc:
        error_response("INVALID_SECTION_CONTENT", str(exc), status_code=422)

    updated = (
        db.query(models.ProposalSection)
        .filter(
            models.ProposalSection.id == section_id,
            models.ProposalSection.proposal_id == proposal_id,
            models.ProposalSection.version == payload.expected_version,
        )
        .update(
            {
                models.ProposalSection.content_json: normalized,
                models.ProposalSection.version: models.ProposalSection.version + 1,
                models.ProposalSection.edited_at: datetime.now(UTC),
                models.ProposalSection.edited_by: current_user.id,
                models.ProposalSection.generation_job_id: None,
                models.ProposalSection.generation_base_version: None,
                models.ProposalSection.status: models.SectionStatus.COMPLETED,
                models.ProposalSection.last_error_code: None,
            },
            synchronize_session=False,
        )
    )
    if updated != 1:
        db.rollback()
        current = _get_scoped_section(db, proposal_id, section_id, current_user.organization_id)
        error_response(
            "VERSION_CONFLICT",
            "This section was changed by another operation.",
            details={"current_version": current.version},
            status_code=409,
        )
    db.expire_all()
    rebuild_proposal_content(db, proposal_id)
    db.commit()
    return _get_scoped_section(db, proposal_id, section_id, current_user.organization_id)


@router.post(
    "/{proposal_id}/sections/{section_id}/regenerate",
    response_model=schemas.ProposalSectionOut,
    status_code=202,
)
@limiter.limit("5/minute")
def regenerate_proposal_section(
    request: Request,
    proposal_id: int,
    section_id: int,
    payload: schemas.ProposalSectionRegenerate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(
        require_role([models.RoleEnum.ADMIN, models.RoleEnum.WRITER])
    ),
) -> models.ProposalSection:
    _get_scoped_section(db, proposal_id, section_id, current_user.organization_id)
    job_id = str(uuid.uuid4())
    updated = (
        db.query(models.ProposalSection)
        .filter(
            models.ProposalSection.id == section_id,
            models.ProposalSection.proposal_id == proposal_id,
            models.ProposalSection.version == payload.expected_version,
        )
        .update(
            {
                models.ProposalSection.status: models.SectionStatus.GENERATING,
                models.ProposalSection.generation_job_id: job_id,
                models.ProposalSection.generation_base_version: payload.expected_version,
                models.ProposalSection.last_error_code: None,
            },
            synchronize_session=False,
        )
    )
    if updated != 1:
        db.rollback()
        current = _get_scoped_section(db, proposal_id, section_id, current_user.organization_id)
        error_response(
            "VERSION_CONFLICT",
            "This section was changed by another operation.",
            details={"current_version": current.version},
            status_code=409,
        )
    db.commit()
    try:
        cast(Any, regenerate_proposal_section_task).delay(
            proposal_id, section_id, job_id, payload.expected_version
        )
    except Exception:
        logger.exception(
            "Failed to queue section regeneration for proposal %s section %s",
            proposal_id,
            section_id,
        )
        section = _get_scoped_section(db, proposal_id, section_id, current_user.organization_id)
        section.status = models.SectionStatus.FAILED
        section.last_error_code = "QUEUE_UNAVAILABLE"
        section.generation_job_id = None
        section.generation_base_version = None
        db.commit()
        error_response(
            "QUEUE_UNAVAILABLE",
            "Section regeneration could not be queued.",
            status_code=503,
        )
    return _get_scoped_section(db, proposal_id, section_id, current_user.organization_id)
