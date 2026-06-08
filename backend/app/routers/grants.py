import json
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..auth import get_current_user
from ..errors import error_response
from ..limiter import limiter
from ..services.matching import GrantMatchingService
from ..services.vector_db import get_vector_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/grants", tags=["Grants Opportunities"])

# Constants
_VECTOR_OVERFETCH_MULTIPLIER = 2


def _run_vector_search(query: str, limit: int) -> list[int]:
    """Query the vector service and return matching grant IDs."""
    return get_vector_service().query_grants(query, limit=limit)


def _build_sql_query(db: Session, search_req: schemas.GrantSearchRequest, grant_ids: list[int]):
    """Build the SQLAlchemy query for grant search with optional vector IDs."""
    query = db.query(models.Grant)

    if grant_ids:
        query = query.filter(models.Grant.id.in_(grant_ids))
    elif search_req.query:
        search_pattern = f"%{search_req.query}%"
        query = query.filter(
            or_(
                models.Grant.title.ilike(search_pattern),
                models.Grant.description.ilike(search_pattern),
                models.Grant.eligibility_criteria.ilike(search_pattern),
            )
        )

    return query


def _apply_sector_filter(query, search_req: schemas.GrantSearchRequest) -> list[models.Grant]:
    """Fetch results and filter by sector tags in memory."""
    overfetch_limit = (search_req.limit or 10) * _VECTOR_OVERFETCH_MULTIPLIER
    all_results = query.offset(search_req.offset or 0).limit(overfetch_limit).all()
    filtered = []
    for grant in all_results:
        try:
            tags = json.loads(grant.sector_tags) if grant.sector_tags else []
            if any(sec in tags for sec in search_req.sectors):
                filtered.append(grant)
        except (json.JSONDecodeError, TypeError) as json_err:
            logger.warning(f"Failed to parse sector tags for grant {grant.id}: {json_err}")
            continue
    return filtered[: search_req.limit]


@router.post("/search", response_model=list[schemas.GrantOut])
@limiter.limit("15/minute")
def search_grants(
    request: Request,
    search_req: schemas.GrantSearchRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
) -> list[models.Grant]:
    """
    Search public grant opportunities. Integrates hybrid semantic vector search
    with SQL fallback to guarantee seamless offline local development.
    """
    grant_ids: list[int] = []

    # 1. Try Pinecone Vector Search if a search query is present
    if search_req.query:
        try:
            overfetch = (search_req.limit or 10) * _VECTOR_OVERFETCH_MULTIPLIER
            grant_ids = _run_vector_search(search_req.query, limit=overfetch)
        except Exception as e:
            logger.warning(
                f"Semantic search failed or bypassed: {e}. Falling back to standard SQL query."
            )

    # 2. SQL Database Retrieval
    query = _build_sql_query(db, search_req, grant_ids)

    # 3. Apply Sector/Tag Filters (if provided)
    if search_req.sectors:
        return _apply_sector_filter(query, search_req)

    # Return standard paginated results
    return query.offset(search_req.offset or 0).limit(search_req.limit or 10).all()


@router.get("/matches", response_model=list[schemas.GrantMatchOut])
def get_grant_matches(
    db: Session = Depends(database.get_db), current_user: models.User = Depends(get_current_user)
):
    """Get ranked grant opportunities matching the organization's profile.

    Delegates matching logic to GrantMatchingService, which handles vector
    similarity search, AI explanation caching, and SQL fallback.
    """
    service = GrantMatchingService(db)
    return service.get_matches(current_user)


@router.get("/{grant_id}", response_model=schemas.GrantOut)
def get_grant_by_id(
    grant_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Fetch a single grant opportunity by its database ID.

    Args:
        grant_id: The primary key of the Grant record to retrieve.

    Returns:
        The matching GrantOut schema.

    Raises:
        404 error_response: If no grant with the given ID exists.
    """
    grant = db.query(models.Grant).filter(models.Grant.id == grant_id).first()
    if not grant:
        error_response(
            code="NOT_FOUND",
            message=f"Grant opportunity with ID {grant_id} not found.",
            status_code=404,
        )
    return grant
