/**
 * Next.js Middleware for Route Management
 * 
 * Note: With Google OAuth tokens stored client-side (localStorage),
 * route protection is handled client-side in the GoogleAuthProvider.
 * This middleware handles basic routing and redirects.
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  
  // Redirect root to chat or login
  if (pathname === '/') {
    return NextResponse.redirect(new URL('/chat', req.url));
  }
  
  return NextResponse.next();
}

// Configure which routes trigger middleware
export const config = {
  matcher: [
    /*
     * Match only the root path for redirects
     */
    '/',
  ],
};
