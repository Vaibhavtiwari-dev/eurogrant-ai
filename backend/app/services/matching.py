import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from .. import models, schemas
from ..errors import error_response
from ..services.extraction import extraction_service
from ..services.vector_db import get_vector_service

# Fallback scoring constants for SQL-based matching path
BASE_FALLBACK_SCORE = 0.88
FALLBACK_SCORE_DECAY = 0.05

logger = logging.getLogger(__name__)


class GrantMatchingService:
    """Service that ranks grant opportunities against an organization's profile.

    Orchestrates vector similarity search, AI-generated match explanations
    (with persistent caching in the GrantMatch table), and a SQL fallback
    path when the vector database is unavailable.
    """

    def __init__(self, db: Session) -> None:
        """Initialise the service with a database session.

        Args:
            db: Active SQLAlchemy session (injected via FastAPI dependency).
        """
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_matches(self, current_user: models.User) -> list[schemas.GrantMatchOut]:
        """Return ranked grant matches for the current user's organisation.

        Flow:
        1. Look up the user's organisation.
        2. Build a query string from the organisation profile.
        3. Attempt vector similarity search.
        4. If vector results exist, build GrantMatchOut objects (with
           explanation caching).
        5. If vector search returned nothing (exception, empty results, or
           all scores below threshold), fall back to a simple SQL listing
           with calculated scores.
        6. Return results sorted descending by score.

        Args:
            current_user: Authenticated user whose organisation is used for
                matching.

        Returns:
            List of GrantMatchOut objects sorted by score (highest first).
        """
        org = self._get_organization(current_user)
        query_str = self._build_query_parts(org)
        matches_data = self._get_vector_matches(query_str)
        results = self._build_results_from_matches(org, matches_data) if matches_data else []
        if not results:
            results = self._fallback_results(org)
        return sorted(results, key=lambda x: x.score, reverse=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_organization(self, current_user: models.User) -> models.Organization:
        """Fetch the organisation linked to the current user.

        Raises:
            HTTPException (404): When no organisation is found for the user.

        Returns:
            The user's Organisation record.
        """
        org = (
            self.db.query(models.Organization)
            .filter(models.Organization.id == current_user.organization_id)
            .first()
        )
        if not org:
            error_response(
                code="NOT_FOUND",
                message="Organization not found",
                status_code=404,
            )
        return org

    def _build_query_parts(self, org: models.Organization) -> str:
        """Construct a text query from the organisation's profile fields.

        Uses sector, core technologies, and countries of operation.
        Falls back to a generic catch-all query when none are set.

        Args:
            org: The organisation whose profile fields to read.

        Returns:
            A concatenated query string suitable for vector search.
        """
        parts = []
        if org.sector:
            parts.append(f"Sector: {org.sector}")
        if org.core_technologies:
            parts.append(f"Technologies: {org.core_technologies}")
        if org.countries_of_operation:
            parts.append(f"Countries: {org.countries_of_operation}")
        return " | ".join(parts) if parts else "General startup business grant"

    @staticmethod
    def _format_org_profile(org: models.Organization) -> str:
        """Format an organisation's profile into a human-readable string.

        Args:
            org: The organisation whose profile to format.

        Returns:
            A comma-separated description of the organisation's sector,
            technologies, and countries of operation.
        """
        parts = []
        if org.sector:
            parts.append(f"Sector: {org.sector}")
        if org.core_technologies:
            parts.append(f"Technologies: {org.core_technologies}")
        if org.countries_of_operation:
            parts.append(f"Countries: {org.countries_of_operation}")
        return ", ".join(parts) if parts else "General startup business grant"

    def _get_vector_matches(self, query_str: str) -> list[dict[str, Any]]:
        """Query the vector database for semantically similar grants.

        Failures are logged and swallowed, returning an empty list so the
        caller can fall back to SQL.

        Args:
            query_str: The natural-language query built from the org profile.

        Returns:
            A list of dicts with keys ``grant_id``, ``score``, and ``text``,
            or an empty list on failure.
        """
        try:
            return get_vector_service().search_grants(query_str, top_k=10)
        except Exception:
            # Capture the exception with full context (traceback + org_id
            # requires the caller; we log query length as a stable proxy).
            logger.exception(
                "matching: vector search failed (query_len=%d); falling back to SQL",
                len(query_str),
            )
            return []

    def _build_results_from_matches(
        self,
        org: models.Organization,
        matches_data: list[dict[str, Any]],
    ) -> list[schemas.GrantMatchOut]:
        """Build GrantMatchOut results from vector search matches.

        Caches AI-generated explanations in the GrantMatch table.  Both
        Grant and GrantMatch records are batch-loaded to avoid N+1 queries.

        Args:
            org: The organisation to match for.
            matches_data: Vector search results (list of dicts with at least
                ``grant_id`` and ``score`` keys).

        Returns:
            List of GrantMatchOut objects (may be empty if all scores are
            below the organisation's match threshold or no grants are found).
        """
        if not matches_data:
            return []

        grant_ids = [m["grant_id"] for m in matches_data]

        # --- Batch-load existing GrantMatch records (N+1 fix) ---
        existing_rows: dict[int, models.GrantMatch] = {
            row.grant_id: row
            for row in self.db.query(models.GrantMatch)
            .filter(
                models.GrantMatch.organization_id == org.id,
                models.GrantMatch.grant_id.in_(grant_ids),
            )
            .all()
        }

        # --- Batch-load Grant records (N+1 fix) ---
        grants: dict[int, models.Grant] = {
            g.id: g
            for g in self.db.query(models.Grant).filter(models.Grant.id.in_(grant_ids)).all()
        }

        org_profile_text = self._format_org_profile(org)
        results: list[schemas.GrantMatchOut] = []

        for match in matches_data:
            gid = match["grant_id"]
            grant = grants.get(gid)
            if not grant or match["score"] < org.match_threshold:
                continue

            # --- Explanation: use cached or generate new one ---
            existing = existing_rows.get(gid)
            if existing:
                explanation = existing.explanation
            else:
                explanation = self._generate_explanation(org_profile_text, grant, gid)
                self._save_match(org, gid, match["score"], explanation)

            results.append(
                schemas.GrantMatchOut(
                    id=grant.id,
                    organization_id=org.id,
                    grant_id=gid,
                    score=match["score"],
                    explanation=explanation,
                    created_at=datetime.now(UTC),
                    grant=schemas.GrantOut.model_validate(grant),
                )
            )

        return results

    def _fallback_results(
        self,
        org: models.Organization,
    ) -> list[schemas.GrantMatchOut]:
        """Return scored results from a plain SQL query when vector search is unavailable.

        Assigns descending scores (0.88, 0.83, 0.78, ...) and caches
        explanations just like the vector path.

        Args:
            org: The organisation to match for.

        Returns:
            List of GrantMatchOut objects (may be empty).
        """
        grants = self.db.query(models.Grant).limit(5).all()
        if not grants:
            return []

        grant_ids = [g.id for g in grants]

        # --- Batch-load existing GrantMatch records (N+1 fix) ---
        existing_rows: dict[int, models.GrantMatch] = {
            row.grant_id: row
            for row in self.db.query(models.GrantMatch)
            .filter(
                models.GrantMatch.organization_id == org.id,
                models.GrantMatch.grant_id.in_(grant_ids),
            )
            .all()
        }

        org_profile_text = self._format_org_profile(org)
        results: list[schemas.GrantMatchOut] = []

        for i, grant in enumerate(grants):
            score = BASE_FALLBACK_SCORE - (i * FALLBACK_SCORE_DECAY)
            if score < org.match_threshold:
                continue

            existing = existing_rows.get(grant.id)
            if existing:
                explanation = existing.explanation
            else:
                explanation = self._generate_explanation(org_profile_text, grant, grant.id)
                self._save_match(org, grant.id, score, explanation)

            results.append(
                schemas.GrantMatchOut(
                    id=grant.id,
                    organization_id=org.id,
                    grant_id=grant.id,
                    score=score,
                    explanation=explanation,
                    created_at=datetime.now(UTC),
                    grant=schemas.GrantOut.model_validate(grant),
                )
            )

        return results

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    def _generate_explanation(
        self,
        org_profile_text: str,
        grant: models.Grant,
        grant_id: int,
    ) -> str:
        """Ask the AI extraction service for a match explanation.

        Args:
            org_profile_text: Pre-formatted organisation profile string.
            grant: The Grant record to explain a match for.
            grant_id: Grant ID (for logging).

        Returns:
            A human-readable explanation string.
        """
        try:
            return extraction_service.explain_match(org_profile_text, grant.description)
        except Exception:
            logger.exception(
                "matching: explanation generation failed for grant %s",
                grant_id,
            )
            return "This grant is highly compatible with your organization's core profile."

    def _save_match(
        self,
        org: models.Organization,
        grant_id: int,
        score: float,
        explanation: str,
    ) -> None:
        """Persist a GrantMatch record to cache the explanation.

        Args:
            org: The organisation the match is for.
            grant_id: The matched grant's ID.
            score: Compatibility score.
            explanation: Explanation text to cache.
        """
        new_match = models.GrantMatch(
            organization_id=org.id,
            grant_id=grant_id,
            score=score,
            explanation=explanation,
            created_at=datetime.now(UTC),
        )
        self.db.add(new_match)
        self.db.commit()
