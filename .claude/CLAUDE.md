# EUROGRANT — Project-level Claude guidance

> **This file extends `~/.claude/CLAUDE.md` with project-specific overrides.**
> Project-level rules here win over the global CLAUDE.md and the
> `rules/ecc/` corpus for this repository only.

## Project type

EUROGRANT is a **B2B SaaS product**, not an open-source library. The
audience is paying customers in the EU grant-application space. Treat
all defaults as "production-grade" — no `print()`, no `console.log`,
no hardcoded secrets, no `dangerouslySetInnerHTML` with user data,
no `any` in TypeScript.

## Tech stack

### Backend

- **Language:** Python 3.12
- **Web framework:** FastAPI (async routes)
- **ORM:** SQLAlchemy 2.0 with `Mapped[...]` types
- **Schemas:** Pydantic v2 (`model_validate`, `ConfigDict(from_attributes=True)`)
- **Auth:** bcrypt directly (no passlib), JWT with HS256 only
- **Task queue:** Celery + Redis
- **DB:** PostgreSQL (Alembic migrations)
- **Vector:** Pinecone (mocked in tests; `USE_LOCAL_STORAGE` toggle)
- **Storage:** S3-compatible (local FS fallback for tests/dev)

### Frontend

- **Framework:** Next.js 16 (App Router)
- **UI:** React 19, TypeScript strict, Tailwind v4, framer-motion
- **State:** server state via TanStack Query, client state via Zustand
- **i18n:** `next-intl` (en, de)
- **Validation:** Zod on every `apiFetch` response
- **Tests:** Vitest (unit), Playwright (e2e)

### Infrastructure

- **CI:** GitHub Actions (no `continue-on-error: true` anywhere)
- **Containers:** Docker + docker-compose
- **Reverse proxy:** nginx with CSP, HSTS preload, gzip, rate limiting
- **Observability:** structured logging, `/health` endpoint reports
  `lockout_degraded` when Redis is down

## Mandate overrides for this project

The global CLAUDE.md `Mandate Priority Order` is preserved. Project-specific
exceptions:

1. **No second-guessing the backend's auth model.** `JWT_SECRET` is
   required at startup; do not add fallback secrets. `ALGORITHM = "HS256"`
   is intentionally hardcoded to prevent algorithm-confusion attacks.
2. **No `passlib`.** The `7f716ca` commit removed it. Use `bcrypt` directly.
3. **No `print()` in production code** — only in test files (and even
   there, prefer `caplog`).
4. **`useDocumentPolling` is dead.** Don't re-introduce polling without
   writing tests first; the deleted hook had a stale-closure bug.
5. **No `alert()` in the frontend.** Use `sonner` (already mounted at
   `app/[locale]/layout.tsx`).

## Plan status

The 7-chunk CRITICAL + HIGH remediation plan
(`C:\Users\Vaibhav\.claude\plans\check-is-the-codebase-shiny-moler.md`)
was completed on 2026-06-07. The remaining MEDIUM (M1–M54) and LOW
(L1–L10) items are tracked in `.planning/BACKLOG.md` (to be created
in a separate pass).

## Key files

- `backend/app/main.py` — middleware stack, security headers, `/health`.
- `backend/app/auth.py` — JWT + bcrypt + cookie/Bearer.
- `backend/app/services/vector_db.py` — Pinecone singleton.
- `backend/app/services/matching.py` — grant ↔ org matching.
- `backend/app/services/proposal_gen.py` — RAG proposal draft.
- `frontend/src/app/[locale]/layout.tsx` — MotionConfig, Toaster, providers.
- `frontend/src/lib/api.ts` — `apiFetch` (Zod-validated, cookie auth).
- `frontend/src/middleware.ts` — locale + auth routing.
- `frontend/next.config.ts` — CSP nonce, HSTS preload.

## Reference

- `~/.claude/CLAUDE.md` — global mandate order, hooks, workflows.
- `~/.claude/rules/ecc/common/` — language-agnostic standards.
- `~/.claude/rules/ecc/web/` — frontend-specific rules.
- `backend/docs/adr/0001-local-storage-fallback.md` — local-storage
  fallback rationale.
- `backend/docs/adr/0002-secure-cookie-session-management.md` —
  cookie + Bearer token model.
- `CONTRIBUTING.md` (root) — branch / commit / PR conventions.
- `SECURITY.md` (root) — vulnerability disclosure policy.
