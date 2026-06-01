import createMiddleware from 'next-intl/middleware';
import {routing} from './i18n/routing';
import {NextResponse} from 'next/server';

const intlMiddleware = createMiddleware(routing);

const publicPaths = ['/', '/login', '/register'];

function isPublicPath(pathname) {
  const stripped = pathname.replace(/^\/[a-z]{2}(\/|$)/, '/');
  return publicPaths.some(p => stripped === p || stripped.startsWith(p + '/'));
}

export default function middleware(request) {
  const {pathname} = request.nextUrl;

  if (isPublicPath(pathname)) {
    return intlMiddleware(request);
  }

  const token = request.cookies.get('access_token');
  if (!token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return intlMiddleware(request);
}

export const config = {
  matcher: [
    '/',
    '/((?!api|_next|_vercel|.*\\..*).*)'
  ]
};
