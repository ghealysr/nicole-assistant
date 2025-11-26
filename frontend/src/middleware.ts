/**
 * Next.js Middleware for Route Protection
 * 
 * QA NOTES:
 * - Protects authenticated routes from unauthenticated access
 * - Redirects to /login if no session
 * - Uses Supabase auth-helpers for server-side session validation
 * - Public routes defined in config.matcher (exclusion pattern)
 */

import { createMiddlewareClient } from '@supabase/auth-helpers-nextjs';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Routes that require authentication
const PROTECTED_ROUTES = ['/chat', '/dashboard', '/journal', '/settings', '/voice'];

export async function middleware(req: NextRequest) {
  const res = NextResponse.next();
  
  // Create Supabase client for middleware
  const supabase = createMiddlewareClient({ req, res });

  // Refresh session if expired
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const { pathname } = req.nextUrl;

  // Check if this is a protected route
  const isProtectedRoute = PROTECTED_ROUTES.some(route => 
    pathname.startsWith(route)
  );
  
  // If accessing a protected route without a session, redirect to login
  if (isProtectedRoute && !session) {
    const loginUrl = new URL('/login', req.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // If logged in and trying to access login/signup, redirect to chat
  if (session && (pathname === '/login' || pathname === '/signup')) {
    return NextResponse.redirect(new URL('/chat', req.url));
  }

  return res;
}

// Configure which routes trigger middleware
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder files
     * - api routes (handled by API middleware)
     */
    '/((?!_next/static|_next/image|favicon.ico|public/|api/).*)',
  ],
};

