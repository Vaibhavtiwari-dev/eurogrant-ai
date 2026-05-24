# ADR-0002: Secure Cookie-Based Session Management

## Status

Proposed

## Context

Currently, JWT access tokens are stored in the browser's `localStorage` and sent via the `Authorization: Bearer <token>` header in API calls. While simple and stateless, `localStorage` is vulnerable to Cross-Site Scripting (XSS) attacks. If an attacker successfully injects a script into the application, they can retrieve the token from `localStorage` and hijack the user's session.

To resolve this, we need a secure token-storage mechanism that cannot be accessed by client-side JavaScript.

## Decision

Migrate JWT token storage from client-side `localStorage` to server-set, secure, `httpOnly` cookies. 

Specifically:
1. **Backend Cookie Handling:**
   - Update the `/auth/login` router to set an `access_token` cookie directly on the HTTP response.
   - The cookie must be configured with `httpOnly=True` (preventing client-side JS access), `secure=True` (only sent over HTTPS, except in localhost), and `samesite="lax"` or `samesite="strict"` (mitigating CSRF attacks).
   - Create a corresponding `/auth/logout` endpoint that expires the `access_token` cookie.
2. **Unified Authentication Dependency:**
   - Modify the FastAPI backend authentication dependency (`get_current_user`) to extract the JWT from the `access_token` cookie first, falling back to the standard `Authorization` header. This preserves backward compatibility for automated tests and external integrations.
3. **Frontend API Interceptor:**
   - Update `apiFetch` in `frontend/src/lib/api.ts` to include `credentials: "include"` in the fetch options, ensuring cookies are transmitted to the backend.
   - Remove token injection logic from header composition in `apiFetch`.

## Consequences

- **Positive:** Eliminates token exfiltration risks via XSS payload executions.
- **Positive:** Seamless authentication context transmission to Next.js Server Components.
- **Negative:** Requires updating backend CORS configurations (`allow_credentials=True`) and testing across subdomains.
- **Risk:** Introduces vulnerability to Cross-Site Request Forgery (CSRF). This must be mitigated using `SameSite=Lax/Strict` and verifying that mutating actions (POST/PUT/DELETE) enforce custom headers (like `X-Requested-With`) or anti-CSRF tokens.

## Alternatives Considered

1. **Short-Lived Access Tokens & Refresh Tokens in Cookies:** Keep access tokens in memory (JS state) and use a secure `httpOnly` cookie for the refresh token. While safer, it increases the state management complexity on the frontend.
2. **Next.js API Routes Proxying:** Route all backend requests through Next.js API endpoints, allowing the Next.js server to handle cookie-to-header conversion. This hides the backend behind a single origin but adds latency and processing overhead.
