import { describe, it, expect, afterEach, vi } from 'vitest';
import { buildCsp } from '../src/lib/csp';

const NONCE = 'test-nonce-123';

function scriptSrcOf(csp: string): string {
  const directive = csp.split('; ').find(d => d.startsWith('script-src'));
  if (!directive) throw new Error('script-src directive missing from CSP');
  return directive;
}

describe('buildCsp', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("includes 'unsafe-eval' in development for React/Turbopack dev tooling", () => {
    vi.stubEnv('NODE_ENV', 'development');

    const scriptSrc = scriptSrcOf(buildCsp(NONCE));

    expect(scriptSrc).toContain("'unsafe-eval'");
    expect(scriptSrc).toContain(`'nonce-${NONCE}'`);
    expect(scriptSrc).toContain("'strict-dynamic'");
  });

  it("never includes 'unsafe-eval' in production", () => {
    vi.stubEnv('NODE_ENV', 'production');

    const scriptSrc = scriptSrcOf(buildCsp(NONCE));

    expect(scriptSrc).not.toContain("'unsafe-eval'");
    expect(scriptSrc).toBe(`script-src 'self' 'nonce-${NONCE}' 'strict-dynamic'`);
  });

  it('whitelists a configured NEXT_PUBLIC_API_URL origin in connect-src', () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000');

    const csp = buildCsp(NONCE);
    const connectSrc = csp.split('; ').find(d => d.startsWith('connect-src'));

    expect(connectSrc).toContain('http://localhost:8000');
    expect(connectSrc).toContain("'self'");
  });

  it('ignores a malformed NEXT_PUBLIC_API_URL without throwing', () => {
    vi.stubEnv('NODE_ENV', 'production');
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'not-a-valid-url');

    const csp = buildCsp(NONCE);
    const connectSrc = csp.split('; ').find(d => d.startsWith('connect-src'));

    expect(connectSrc).toBe("connect-src 'self' https://eurogrant.ai");
  });
});
