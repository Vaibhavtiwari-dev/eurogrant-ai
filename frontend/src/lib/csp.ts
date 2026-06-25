/**
 * Builds the per-request Content-Security-Policy header value.
 *
 * Pure function with no Next.js runtime dependency so it can be unit-tested
 * in isolation. Consumed by the middleware in `src/proxy.ts`.
 */
export function buildCsp(nonce: string): string {
  const connectSources = new Set(["'self'", 'https://eurogrant.ai']);
  const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL;

  if (configuredApiUrl) {
    try {
      const apiUrl = new URL(configuredApiUrl);
      if (apiUrl.protocol === 'http:' || apiUrl.protocol === 'https:') {
        connectSources.add(apiUrl.origin);
      }
    } catch {
      // Invalid deployment configuration remains blocked by the CSP.
    }
  }

  const scriptSrc = [
    "script-src 'self'",
    `'nonce-${nonce}'`,
    "'strict-dynamic'",
    // React/Turbopack require eval() for Fast Refresh and callstack
    // reconstruction in dev only; it must never reach production.
    ...(process.env.NODE_ENV === 'development' ? ["'unsafe-eval'"] : []),
  ].join(' ');

  return [
    "default-src 'self'",
    scriptSrc,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob: https:",
    "font-src 'self' data:",
    `connect-src ${Array.from(connectSources).join(' ')}`,
    "frame-ancestors 'none'",
    "form-action 'self'",
    "base-uri 'self'",
    "object-src 'none'",
  ].join('; ');
}
