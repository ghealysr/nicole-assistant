'use client';

import { useEffect, useRef } from 'react';
import { useGoogleAuth } from '@/lib/google_auth';
import { useRouter } from 'next/navigation';

/**
 * Login page component for Nicole V7.
 * 
 * Features:
 * - Google-only OAuth authentication
 * - Clean, elegant design with Nicole branding
 * - Restricted to @alphawavetech.com and allowed personal emails
 */
export default function LoginPage() {
  const { isAuthenticated, isLoading, renderSignInButton } = useGoogleAuth();
  const router = useRouter();
  const buttonContainerRef = useRef<HTMLDivElement>(null);
  const buttonRendered = useRef(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/chat');
    }
  }, [isAuthenticated, router]);

  // Render Google Sign-In button
  useEffect(() => {
    if (!isLoading && !isAuthenticated && !buttonRendered.current) {
      // Small delay to ensure Google script is loaded
      const timer = setTimeout(() => {
        renderSignInButton('google-signin-button');
        buttonRendered.current = true;
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isLoading, isAuthenticated, renderSignInButton]);

  // Show loading while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-cream">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-lavender/20 flex items-center justify-center mx-auto mb-4 animate-pulse">
            <span className="text-lavender-text text-3xl font-serif">N</span>
          </div>
          <p className="text-text-secondary">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      {/* Left side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-lavender/10 items-center justify-center p-12">
        <div className="max-w-md text-center">
          <div className="w-24 h-24 rounded-full bg-lavender/20 flex items-center justify-center mx-auto mb-8">
            <span className="text-lavender-text text-5xl font-serif">N</span>
          </div>
          <h1 className="text-4xl font-serif text-lavender-text mb-4">
            Nicole
          </h1>
          <p className="text-text-secondary text-lg leading-relaxed">
            Your personal AI companion, designed to help with life&apos;s big and small moments.
          </p>
          <div className="mt-12 flex justify-center space-x-6 text-text-tertiary text-sm">
            <span>🧠 Perfect memory</span>
            <span>💬 Natural chat</span>
            <span>📊 Smart insights</span>
          </div>
        </div>
      </div>

      {/* Right side - Login */}
      <div className="flex-1 flex items-center justify-center p-8 bg-cream">
        <div className="max-w-md w-full">
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-8">
            <div className="w-16 h-16 rounded-full bg-lavender/20 flex items-center justify-center mx-auto mb-4">
              <span className="text-lavender-text text-3xl font-serif">N</span>
            </div>
            <h1 className="text-2xl font-serif text-lavender-text">Nicole</h1>
          </div>

          <div className="text-center mb-8">
            <h2 className="text-2xl font-serif text-text-primary">
              Welcome
            </h2>
            <p className="mt-2 text-text-secondary">
              Sign in to continue your conversation
            </p>
          </div>

          {/* Google Sign-In Button Container */}
          <div className="flex justify-center mb-8">
            <div 
              id="google-signin-button" 
              ref={buttonContainerRef}
              className="min-h-[44px]"
            />
          </div>

          {/* Access info */}
          <div className="text-center">
            <p className="text-sm text-text-tertiary">
              This is a private family assistant.
            </p>
            <p className="text-sm text-text-tertiary mt-1">
              Access is restricted to authorized accounts.
            </p>
          </div>

          {/* Powered by */}
          <div className="mt-12 text-center">
            <p className="text-xs text-text-tertiary opacity-60">
              Powered by Claude AI • Built with 💜 by Alphawave
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
