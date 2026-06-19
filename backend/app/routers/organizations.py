from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import database, models, schemas
from ..auth import get_current_user, require_role

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/me", response_model=schemas.OrganizationOut)
async def get_my_organization(
    db: AsyncSession = Depends(database.get_async_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Organization:
    result = await db.execute(
        select(models.Organization).where(models.Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("/dashboard-overview", response_model=schemas.DashboardOverviewOut)
async def get_dashboard_overview(
    db: AsyncSession = Depends(database.get_async_db),
    current_user: models.User = Depends(get_current_user),
) -> schemas.DashboardOverviewOut:
    # Fetch real data where possible, use placeholders for missing features

    # 1. Stats
    from sqlalchemy import func

    doc_count_result = await db.execute(
        select(func.count(models.CompanyDocument.id)).where(
            models.CompanyDocument.organization_id == current_user.organization_id
        )
    )
    doc_count = doc_count_result.scalar() or 0

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
    db: AsyncSession = Depends(database.get_async_db),
    current_user: models.User = Depends(
        require_role([models.RoleEnum.ADMIN, models.RoleEnum.WRITER])
    ),
) -> models.Organization:
    result = await db.execute(
        select(models.Organization).where(models.Organization.id == current_user.organization_id)
    )
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    update_data = org_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(org, key, value)

    await db.flush()
    await db.refresh(org)
    return org
