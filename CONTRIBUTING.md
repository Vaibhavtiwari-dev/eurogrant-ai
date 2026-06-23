# Contributing to EUROGRANT

> **This repository is proprietary.** The following conventions apply to
> authorized contributors (employees, contractors under a signed
> agreement, and approved external collaborators). Third-party pull
> requests from outside the organization are not accepted.

## Quick start

1. **Branch from `main`.** Branch name format: `<type>/<short-kebab-slug>`
   - `feat/<slug>`, `fix/<slug>`, `refactor/<slug>`, `chore/<slug>`, `docs/<slug>`.
2. **Follow the [Conventional Commits](https://www.conventionalcommits.org/)
   format** for all commit messages.
3. **Run all quality gates locally before opening a PR:**
   - `cd backend && ruff check . && ruff format --check . && pytest -q`
   - `cd frontend && npm run lint && npm run test:unit -- --coverage && npx tsc --noEmit`
   - **Use npm 10 for the frontend.** CI (`node:20`) and the frontend Docker
     image (`node:20-alpine`) both ship npm 10. A `package-lock.json`
     regenerated under npm 11+ omits the platform-specific optional
     dependency entries npm 10 requires, so `npm ci` passes locally but
     fails in CI with `EUSAGE … out of sync`. If you change frontend
     dependencies, regenerate the lock with npm 10
     (`npx -y npm@10 install --package-lock-only`) and verify with
     `npx -y npm@10 ci`.
4. **Open a PR** using the `.github/PULL_REQUEST_TEMPLATE.md` checklist.
5. **Pass CI.** All jobs (lint, type-check, unit, integration, Docker
   build) must be green. Coverage must stay at or above 80% lines.

## Code review

- Every PR requires one reviewer who owns the affected area. See
  `CODEOWNERS` for the routing table.
- Address all `CRITICAL` and `HIGH` review findings before merge.
- `MEDIUM` and `LOW` items are tracked as follow-up issues; they do not
  block merge.

## Architecture decisions

- For backend architecture, consult `.planning/codebase/ARCHITECTURE.md`.
- ADRs are stored in `backend/docs/adr/` (e.g., `0001-local-storage-fallback.md`,
  `0002-secure-cookie-session-management.md`).
- For new ADRs, copy an existing ADR and link any superseded decisions.

## Coding standards

Project-level standards are documented in `.claude/CLAUDE.md`. Highlights:

- **Backend:** Python 3.12, FastAPI async, SQLAlchemy 2.0 `Mapped`
  types, Pydantic v2 schemas, parameterized queries, bcrypt for
  password hashing, no `passlib`. Functions < 50 lines, files
  < 800 lines.
- **Frontend:** TypeScript strict, zero `any`, zero `console.log` in
  production, all `apiFetch` responses validated with Zod, semantic
  HTML, WCAG 2.2 AA, no `alert()`.
- **Secrets:** never hardcoded; sourced from environment variables.
- **Tests:** 80% line coverage target on new code; AAA pattern;
  deterministic — no sleeping, no real network calls.

## Security

Found a vulnerability? Follow `SECURITY.md` for the disclosure
process. Do not open a public issue.
