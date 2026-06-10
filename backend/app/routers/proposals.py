import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..auth import get_current_user
from ..errors import error_response
from ..worker import generate_proposal_task

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


@router.post("/", response_model=schemas.ProposalOut, status_code=202)
def create_proposal(
    payload: schemas.ProposalCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
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
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)

    # --- Dispatch the async Celery task ---
    try:
        generate_proposal_task.delay(proposal.id)  # type: ignore
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
    proposal = (
        db.query(models.Proposal)
        .filter(
            models.Proposal.id == proposal_id,
            models.Proposal.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not proposal:
        error_response("NOT_FOUND", f"Proposal with id {proposal_id} not found.", status_code=404)
    return proposal
