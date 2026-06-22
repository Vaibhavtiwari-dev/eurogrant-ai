# Changelog

All notable changes to EUROGRANT are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Phase 12: Security & Architecture Hardening (Completed)
Resolved all 11 codebase concerns from `.planning/codebase/resolved/CONCERNS.md`:
- **Async DB layer** — FastAPI routes migrated to `AsyncSession` via `create_async_engine`; Celery workers keep the sync `Session`. `database.py` exposes both `get_db` and `get_async_db`. Added `greenlet` + `aiosqlite`.
- **Secret masking** — `Settings.__repr__` masks API_KEY/SECRET/PASSWORD/TOKEN fields; added `mask_sensitive()` helper.
- **Strict environment** — `EnvironmentEnum` (development/testing/staging/production); CSRF bypass limited to TESTING only.
- **Uploads** — magic-byte-only validation (extension check removed).
- **Thread safety** — OpenAI client uses double-checked locking; Pinecone readiness uses exponential backoff.
- **Search + audit** — `ProposalSection.content_text` plain-text mirror; `Proposal.created_by` / `ProposalSection.edited_by` audit columns + per-user ACL filtering.
- **Typed client** — frontend `src/types/api.ts` generated from the backend OpenAPI spec via `openapi-typescript`.

### Security & Compliance
- Replaced `passlib` with `bcrypt` directly for password hashing (commit `7f716ca`).
- Strengthened CSP — removed `unsafe-inline` / `unsafe-eval`, added per-request nonce propagation.
- Hardened Alembic — `DATABASE_URL` is now required, no fallback credentials.
- Consolidated `vector_db.py` lazy-singleton; removed module-level `__getattr__` that produced two parallel instances.
- Lockout service surfaces a `lockout_degraded` flag in `/health` when Redis is unavailable.
- `services/s3.py` blocking I/O is now offloaded with `asyncio.to_thread`; no event-loop stalls.

### Frontend accessibility
- Form labels are now associated with inputs (`htmlFor` + `id`).
- Native `alert()` calls replaced with `sonner` toasts (RAG draft proposal, account deletion). Account deletion now opens a destructive confirm dialog.
- All icon-only buttons have `aria-label`; a global `MotionConfig reducedMotion="user"` honours the OS reduced-motion preference.
- Color contrast: `text-slate-400` / `text-slate-500` on dark surfaces replaced with design-token-based colors.
- Removed dead `useDocumentPolling` hook (zero callers; stale closure).

### Infrastructure
- CI: removed `continue-on-error: true` from frontend lint and unit test steps. CI now blocks on lint, type-check, unit tests, coverage, Docker build, and security scans.
- Backend CI: added `ruff check`, `ruff format --check`, `mypy`, `bandit -ll`, `pip-audit`, `gitleaks`, `pytest --cov --cov-fail-under=80`.
- Frontend Dockerfile: multi-stage build that runs `next start` in production (no more `npm run dev` in the prod image).
- nginx: per-server CSP, HSTS preload, gzip, and per-IP rate limiting on `/api/`.

### Tests
- Frontend coverage thresholds enforced at 80% lines / 75% branches / 80% functions / 80% statements.
- New component tests: `DocumentList`, `DocumentUpload`, `CompanyProfile`, `MatchedGrants`, `NotificationSettings`.
- New e2e spec: `upload → match → proposal draft` flow.
- Backend: `test_organizations.py` expanded (PUT /me, GET /dashboard-overview, partial updates, validation). New `test_s3.py` covers both local and S3 paths plus boto3 error propagation.

### Docs
- Added `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`, `CODEOWNERS`, `.editorconfig`, `.prettierrc`, `codecov.yml`, project `.claude/CLAUDE.md` and `.claude/settings.json`.
- Dependabot configuration: weekly Python, npm, and Docker updates; groups minor/patch updates to keep PR noise down.

## [0.1.0] - 2026-06-19

### Phase 11: Editor, Export & Billing (Completed)
- Added `ProposalSection` model with version tracking, content JSON (TipTap), and edit history.
- Implemented proposal section regeneration with optimistic locking (`expected_version`).
- Added proposal export to PDF (reportlab) and DOCX (python-docx) formats.
- Integrated Stripe billing with checkout sessions, customer portal, and webhook handling.
- Added subscription tier enforcement (Growth/Scale/Agency) with monthly proposal limits.

### Phase 10: RAG Proposal Generator (Completed)
- Built async Celery task for LLM-based proposal generation per section.
- Created TipTap ↔ Markdown conversion utilities for rich-text editing.
- Implemented proposal generation with structured sections based on grant rubrics.

### Phase 9: Semantic Matching & Alerts (Completed)
- Cosine similarity matching between organization and grant vectors.
- AI-generated match explanations.
- Configurable match threshold per organization.
- Email alert support infrastructure.

### Phase 8: Automated Grant Discovery (Completed)
- `GrantScraper` abstraction with BeautifulSoup-based parsers.
- Daily Celery Beat schedule for grant scraping.
- Grant metadata storage and vector indexing.

### Phase 7: Remediation — Frontend Quality & Performance (Completed)
- Refactored monolithic `dashboard/page.tsx` into reusable sub-components.
- Consolidated document status polling into a single mechanism.
- Replaced mock metrics with dynamic backend data.

### Phase 7.1: Visual Brand Refresh & Landing Page (Completed)
- New AI-centric aesthetic with Inter and Roboto Mono fonts.
- Updated i18n messages (`en.json`, `de.json`) with marketing copy.
- Landing page and login page visual synchronization.

### Phase 7.2: EuroGrant AI Dashboard Redesign (Completed)
- "Emerald & Copper B2B" design system.
- Deep Charcoal sidebar with Emerald Green (#064e3b) icons.
- Executive Overview with high-fidelity Stats Cards.
- RAG Pipeline Progress and Hot Matches widgets.

### Phase 6: Remediation — Compliance & Security Updates (Completed)
- Updated `postcss` to >= 8.5.14.
- Audited `ecdsa` usage; migrated from `python-jose` to `PyJWT`.
- PII redaction before LLM processing.

### Phase 5: Remediation — Backend & Infrastructure (Completed)
- Alembic initialized with full schema migration.
- Organization hijacking protection (invite code or admin approval).
- RBAC enforced at router level.
- Removed unused dependencies (Playwright, Anthropic from backend).

### Phase 4: Profile Dashboard & UI (Completed)
- Dashboard displays structured company data.
- Real-time updates as document processing completes.

### Phase 3: Company Profiling Pipeline (Completed)
- Document upload (PDF/DOCX) with S3/local storage.
- AI profile extraction and vectorization.
- Pinecone namespace isolation by organization.

### Phase 2: Core Infrastructure & Auth (Completed)
- Docker environment with FastAPI, Next.js, Postgres, Redis, Celery.
- JWT authentication with role-based access control (Admin/Writer/Viewer).
- CSRF dual-token validation and security headers.

### Phase 1: Legal & Incorporation (Completed)
- Estonian OÜ incorporated.
- Wise Business account active.
