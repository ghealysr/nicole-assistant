'use client';

import { useEffect, useState } from 'react';
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
  const { isAuthenticated, isLoading, isGoogleReady, renderSignInButton } = useGoogleAuth();
  const router = useRouter();
  const [buttonRendered, setButtonRendered] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/chat');
    }
  }, [isAuthenticated, router]);

  // Render Google Sign-In button when Google script is ready
  useEffect(() => {
    if (isGoogleReady && !isAuthenticated && !buttonRendered) {
      // Small delay to ensure DOM is ready
      const timer = setTimeout(() => {
        const container = document.getElementById('google-signin-button');
        if (container) {
          renderSignInButton('google-signin-button');
          setButtonRendered(true);
        } else if (retryCount < 5) {
          // Retry if container not found
          setRetryCount(r => r + 1);
        }
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [isGoogleReady, isAuthenticated, buttonRendered, renderSignInButton, retryCount]);

  // Retry mechanism - trigger re-render to retry button rendering
  useEffect(() => {
    if (!buttonRendered && retryCount > 0 && retryCount < 5) {
      const timer = setTimeout(() => {
        setRetryCount(r => r + 1);
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [retryCount, buttonRendered]);

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
              className="min-h-[44px] flex items-center justify-center"
            >
              {!buttonRendered && (
                <div className="flex items-center gap-2 px-6 py-3 border border-gray-300 rounded-md bg-white">
                  <svg className="w-5 h-5 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span className="text-gray-500 text-sm">Loading Google Sign-In...</span>
                </div>
              )}
            </div>
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
