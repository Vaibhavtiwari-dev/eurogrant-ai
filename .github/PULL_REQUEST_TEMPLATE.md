<!--
Thanks for opening a PR! Please fill in the sections below. The PR
template is enforced via CI: if the description is empty the linter
will block. Delete any section that is not relevant.
-->

## Summary

<!--
One or two sentences describing what this PR does and why.
Link the issue or design doc (e.g. "Fixes #123", "ADR-0001").
-->

## Changes

<!--
Bullet list of the most important changes. Keep this short and
specific; reviewers can read the diff for details.
-->

- <!-- e.g. Refactored send_match_alert to use Jinja2 template -->
- <!-- e.g. Added aria-labels to icon buttons in dashboard/Sidebar.tsx -->

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing
      functionality to change)
- [ ] Refactor (no functional change)
- [ ] Documentation / CI / tooling

## Quality gates (must all be green to merge)

- [ ] `cd backend && ruff check . && ruff format --check .`
- [ ] `cd backend && mypy backend/app/`
- [ ] `cd backend && pytest -q --cov=app --cov-fail-under=80`
- [ ] `cd frontend && npm run lint`
- [ ] `cd frontend && npx tsc --noEmit`
- [ ] `cd frontend && npm run test:unit -- --coverage`
      (coverage stays at ≥80% lines / 75% branches)
- [ ] `cd frontend && npx playwright test` (if e2e is affected)
- [ ] Docker images build (`docker build backend/ frontend/`)
- [ ] No new `console.log` in production code
- [ ] No hardcoded secrets; all env-sourced
- [ ] No `any` introduced in TypeScript
- [ ] No new files > 800 lines
- [ ] No new functions > 50 lines
- [ ] New public functions have return type hints (Python) /
      explicit return types (TypeScript)
- [ ] Database migrations are additive only; backfilled data is
      idempotent

## Test plan

<!--
Describe the tests you ran to verify the change. Include curl
snippets, screenshots, or steps to reproduce.
-->

## Risks

<!--
What could break? What is the rollback plan? Have you considered the
blast radius?
-->

## Follow-ups

<!--
Optional: list of MEDIUM/LOW issues introduced or discovered, and any
work that should be tracked separately.
-->

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
