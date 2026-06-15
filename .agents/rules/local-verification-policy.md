# Local Verification & Zero-Tolerance Policy

**MANDATORY BEHAVIOR FOR ALL SESSIONS:**
You must never rely solely on GitHub Actions/CI to catch test failures, lint errors, or build crashes. 
Every code modification must be verified **locally** before `git commit` or `git push` is executed.

## 1. Zero-Tolerance Gating
No task is considered complete unless local verification commands exit cleanly (exit code 0).
If a linter or test fails, you must diagnose and fix it locally before pushing.

## 2. Parallelization via Subagents
When a feature is complete and ready for commit, you MUST deploy subagents to parallelize the verification process across different domains:
- **Frontend Verifier Subagent:** Runs `npm run lint`, `npx tsc --noEmit`, and `npm run build` inside `/frontend`.
- **Backend Verifier Subagent:** Runs `ruff check .`, `ruff format --check .`, and `pytest` inside `/backend`.
- **Docker Verifier Subagent:** Runs `docker build` if any infrastructure, `requirements.txt`, or `Dockerfile` files were modified.

Use the `invoke_subagent` tool to spawn these tasks concurrently. You must wait for all subagents to report a successful execution status before staging and committing files.

## 3. Mandatory Commands
Before any commit, the following standards must be locally enforced:
* **Backend:** 
  * Linting: `ruff check .`
  * Formatting: `ruff format .`
  * Testing: `pytest`
* **Frontend:**
  * Linting: `npm run lint`
  * Types: `npm run type-check` or `npx tsc --noEmit`
  * Build: `next build` (or `npm run build`)
* **Infrastructure:**
  * If pip dependencies change: Ensure strict hashes are either fully cross-platform compatible or tested via `docker build` locally.
