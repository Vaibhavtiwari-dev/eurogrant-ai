# Changelog

All notable changes to EUROGRANT are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Security & Compliance
- Replaced `passlib` with `bcrypt` directly for password hashing
  (commit `7f716ca`).
- Strengthened CSP — removed `unsafe-inline` / `unsafe-eval`, added
  per-request nonce propagation. (Chunk 2)
- Hardened Alembic — `DATABASE_URL` is now required, no fallback
  credentials. (Chunk 3)
- Consolidated `vector_db.py` lazy-singleton; removed module-level
  `__getattr__` that produced two parallel instances. (Chunk 3)
- Lockout service surfaces a `lockout_degraded` flag in `/health` when
  Redis is unavailable. (Chunk 3)
- `services/s3.py` blocking I/O is now offloaded with
  `asyncio.to_thread`; no event-loop stalls. (Chunk 3)

### Frontend accessibility
- Form labels are now associated with inputs (`htmlFor` + `id`).
- Native `alert()` calls replaced with `sonner` toasts (RAG draft
  proposal, account deletion). Account deletion now opens a
  destructive confirm dialog.
- All icon-only buttons have `aria-label`; a global `MotionConfig
  reducedMotion="user"` honours the OS reduced-motion preference.
- Color contrast: `text-slate-400` / `text-slate-500` on dark surfaces
  replaced with the `text-on-surface-variant` design token.
- Removed dead `useDocumentPolling` hook (zero callers; stale closure).

### Infrastructure
- CI: removed `continue-on-error: true` from frontend lint and unit
  test steps. CI now blocks on lint, type-check, unit tests, coverage,
  Docker build, and security scans. (Chunk 1)
- Backend CI: added `ruff check`, `ruff format --check`, `mypy`,
  `bandit -ll`, `pip-audit`, `gitleaks`, `pytest --cov --cov-fail-under=80`.
- Frontend Dockerfile: multi-stage build that runs `next start` in
  production (no more `npm run dev` in the prod image).
- nginx: per-server CSP, HSTS preload, gzip, and per-IP rate limiting
  on `/api/`.

### Tests
- Frontend coverage thresholds enforced at 80% lines / 75% branches /
  80% functions / 80% statements.
- New component tests: `DocumentList`, `DocumentUpload`, `CompanyProfile`,
  `MatchedGrants`, `NotificationSettings`.
- New e2e spec: `upload → match → proposal draft` flow.
- Backend: `test_organizations.py` expanded (PUT /me, GET
  /dashboard-overview, partial updates, validation). New
  `test_s3.py` covers both local and S3 paths plus boto3 error
  propagation.

### Docs
- Added `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`,
  `CODEOWNERS`, `.editorconfig`, `.prettierrc`, `codecov.yml`, project
  `.claude/CLAUDE.md` and `.claude/settings.json`.
- Dependabot configuration: weekly Python, npm, and Docker updates;
  groups minor/patch updates to keep PR noise down.

## [0.1.0] - 2026-06-01

Initial internal alpha. Backend (FastAPI + Celery + Redis + Postgres +
Pinecone) and frontend (Next.js 16 + React 19) are deployed via
docker-compose for internal demos. Not yet production-hardened.
