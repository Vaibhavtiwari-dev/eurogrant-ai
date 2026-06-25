import createMiddleware from 'next-intl/middleware';
import {routing} from './i18n/routing';
import {NextRequest, NextResponse} from 'next/server';
import {buildCsp} from './lib/csp';

const intlMiddleware = createMiddleware(routing);

const publicPaths = ['/', '/login', '/register'];

function isPublicPath(pathname: string) {
  const stripped = pathname.replace(/^\/[a-z]{2}(\/|$)/, '/');
  return publicPaths.some(p => stripped === p || stripped.startsWith(p + '/'));
}

export default function proxy(request: NextRequest) {
  const {pathname} = request.nextUrl;

  // Per-request nonce for inline scripts (e.g. JSON-LD in layout).
  const nonce = btoa(crypto.randomUUID());
  const cspHeader = buildCsp(nonce);

  // Propagate nonce to downstream Server Components via request headers.
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-nonce', nonce);
  requestHeaders.set('Content-Security-Policy', cspHeader);
  const requestWithHeaders = new NextRequest(request, {headers: requestHeaders});

  let response: NextResponse;
  if (isPublicPath(pathname)) {
    response = intlMiddleware(requestWithHeaders);
  } else {
    const token = request.cookies.get('access_token');
    if (!token) {
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(loginUrl);
    }
    response = intlMiddleware(requestWithHeaders);
  }

  // Mirror CSP + nonce onto the outgoing response.
  response.headers.set('Content-Security-Policy', cspHeader);
  response.headers.set('x-nonce', nonce);
  return response;
}

export const config = {
  matcher: [
    '/',
    '/((?!api|_next|_vercel|.*\\..*).*)'
  ],
};
