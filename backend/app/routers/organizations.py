from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..auth import get_current_user, require_role

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me", response_model=schemas.OrganizationOut)
async def get_my_organization(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Organization:
    org = (
        db.query(models.Organization)
        .filter(models.Organization.id == current_user.organization_id)
        .first()
    )
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("/dashboard-overview", response_model=schemas.DashboardOverviewOut)
async def get_dashboard_overview(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
) -> schemas.DashboardOverviewOut:
    # Fetch real data where possible, use placeholders for missing features

    # 1. Stats
    # active_high_matches: Count of company documents that are processed (placeholder for real matches)
    doc_count = (
        db.query(models.CompanyDocument)
        .filter(models.CompanyDocument.organization_id == current_user.organization_id)
        .count()
    )

    stats = schemas.DashboardStatsOut(
        active_high_matches=doc_count,  # Placeholder: using doc count as active matches for now
        ai_generation_quality=94,  # Static placeholder
        total_pipeline_value=1.5 * doc_count,  # Placeholder multiplier
    )

    # 2. Pipelines (returns empty until proposal generation is live)
    pipelines: list[schemas.PipelineOut] = []

    # 3. Hot Matches (returns empty until semantic matching is live)
    hot_matches: list[schemas.MatchOut] = []

    return schemas.DashboardOverviewOut(stats=stats, pipelines=pipelines, hot_matches=hot_matches)


@router.put("/me", response_model=schemas.OrganizationOut)
async def update_my_organization(
    org_update: schemas.OrganizationUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(
        require_role([models.RoleEnum.ADMIN, models.RoleEnum.WRITER])
    ),
) -> models.Organization:
    org = (
        db.query(models.Organization)
        .filter(models.Organization.id == current_user.organization_id)
        .first()
    )
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    update_data = org_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(org, key, value)

    db.commit()
    db.refresh(org)
    return org
