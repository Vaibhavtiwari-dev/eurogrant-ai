# Security Policy

## Reporting a Vulnerability

EUROGRANT takes security seriously. We appreciate responsible disclosure
and will work with you to investigate and resolve any issue you report.

**How to report:**

- **Email:** security@eurogrant.ai
- **Subject line prefix:** `[SECURITY]`
- **Please do not open a public GitHub issue for suspected vulnerabilities.**

A security report should include:

1. A clear description of the issue and its potential impact.
2. Steps to reproduce, including any URLs, parameters, or test accounts
   used (do not include real user data).
3. The EUROGRANT version, commit SHA, or release tag affected.
4. Your contact details so we can follow up with clarifying questions.

## Response timeline

| Stage | Target |
|---|---|
| Initial acknowledgement | within 3 business days |
| Status update | every 7 days until resolved |
| Patch release | within 90 days of confirmed vulnerability |
| Public disclosure | coordinated with the reporter; default 90-day window |

We follow a **90-day disclosure window** by default. We will credit
reporters in the release notes (with their consent) once a fix is
deployed.

## Supported versions

| Version | Supported |
|---|---|
| `main` (active development) | ✅ |
| Latest tagged release | ✅ |
| Older releases | ❌ (please upgrade) |

## Out-of-scope reports

Reports that do not represent a real security risk will be closed
without a CVE, with an explanation. Examples:

- Volumetric DoS (handled at the infrastructure layer).
- Rate-limiting gaps in non-authenticated endpoints.
- User-education issues (phishing-style content hosted by users).
- Reports against forks or third-party packages not under our control
  (please report upstream).

## Security controls (overview)

The repository's defense-in-depth includes:

- bcrypt password hashing (no passlib).
- JWT with `verify_exp: true` and HS256 only.
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`.
- Content-Security-Policy with per-request nonce (no `unsafe-inline`).
- Account-lockout service backed by Redis with `/health` observability.
- SSRF guard on outbound HTTP (`services/discovery.py`).
- RAG prompt-injection mitigation (`services/extraction.py`).
- File-upload magic-byte validation, MIME cross-check, 25 MB cap
  (`routers/uploads.py`).
- Per-IP rate limiting at the application layer (slowapi) and at the
  nginx gateway.
- CSRF dual-token validation (cookie + `X-CSRF-Token` header) with
  `Origin`/`Referer` checking.
- Path traversal protection in local file storage (`services/s3.py`).
- Frontend container runs as non-root (`USER node`).
- SQLite multi-thread safety (`check_same_thread=False`, 30s timeout).

## Contact

- **General security inbox:** security@eurogrant.ai
- **Coordinated disclosure:** same address, subject `[COORDINATED-DISCLOSURE]`
- **PGP fingerprint:** (to be published; request the current key from the
  security inbox if you need it for an encrypted report)
