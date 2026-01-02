'use client';

import { useEffect, useState, useCallback } from 'react';
import { useGoogleAuth } from '@/lib/google_auth';
import { useRouter, useSearchParams } from 'next/navigation';

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
  const searchParams = useSearchParams();
  const [buttonRendered, setButtonRendered] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [loadFailed, setLoadFailed] = useState(false);
  
  // Check if session expired
  const sessionExpired = searchParams.get('expired') === 'true';

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
          setLoadFailed(false);
        } else if (retryCount < 5) {
          // Retry if container not found
          setRetryCount(r => r + 1);
        } else {
          setLoadFailed(true);
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
    
    // If we've exhausted retries and button still not rendered, auto-clear state
    if (retryCount >= 5 && !buttonRendered && isGoogleReady) {
      console.warn('[Login] Button failed to render after retries, clearing state');
      localStorage.removeItem('nicole_google_token');
      localStorage.removeItem('auth_token');
      localStorage.removeItem('nicole_token');
    }
  }, [retryCount, buttonRendered, isGoogleReady]);

  // Clear any stale auth state on login page load
  useEffect(() => {
    // If we're on the login page and not authenticated, clear any stale tokens
    // This helps recover from corrupted state
    if (!isAuthenticated && !isLoading) {
      const storedToken = localStorage.getItem('nicole_google_token');
      if (storedToken) {
        // Check if token is valid JWT format
        const parts = storedToken.split('.');
        if (parts.length !== 3) {
          console.log('[Login] Clearing invalid token format');
          localStorage.removeItem('nicole_google_token');
          localStorage.removeItem('auth_token');
          localStorage.removeItem('nicole_token');
        }
      }
    }
  }, [isAuthenticated, isLoading]);

  // Mark as failed if Google script doesn't load after 8 seconds (reduced from 10)
  useEffect(() => {
    if (!isGoogleReady && !isLoading) {
      const timer = setTimeout(() => {
        if (!isGoogleReady) {
          console.warn('[Login] Google not ready after timeout, marking as failed');
          setLoadFailed(true);
        }
      }, 8000);
      return () => clearTimeout(timer);
    }
  }, [isGoogleReady, isLoading]);

  // Manual retry handler
  const handleRetry = useCallback(() => {
    // Clear any cached Google state
    localStorage.removeItem('nicole_google_token');
    localStorage.removeItem('auth_token');
    localStorage.removeItem('nicole_token');
    
    // Force a full page reload to re-initialize Google
    window.location.reload();
  }, []);

  // Clear and switch account - force account picker to show
  const handleSwitchAccount = useCallback(() => {
    // Clear ALL stored tokens and Google state
    localStorage.removeItem('nicole_google_token');
    localStorage.removeItem('auth_token');
    localStorage.removeItem('nicole_token');
    
    // Clear sessionStorage too
    sessionStorage.clear();
    
    // Tell Google to disable auto-select and revoke credential
    if (window.google?.accounts?.id) {
      // Disable auto-select so user must choose
      window.google.accounts.id.disableAutoSelect();
      
      // Cancel any pending prompts
      window.google.accounts.id.cancel();
    }
    
    // Clear IndexedDB Google state
    if (window.indexedDB) {
      try {
        window.indexedDB.deleteDatabase('googleApiKey');
        window.indexedDB.deleteDatabase('gsi_client');
      } catch (e) {
        console.log('IndexedDB clear failed:', e);
      }
    }
    
    // Reset button state so it re-renders
    setButtonRendered(false);
    setRetryCount(0);
    setLoadFailed(false);
    
    // Force reload to get fresh Google Sign-In with account picker
    // Add a cache buster to ensure fresh load
    window.location.href = '/login?switch=' + Date.now();
  }, []);

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

          {/* Session expired message */}
          {sessionExpired && (
            <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg text-center">
              <p className="text-amber-800 text-sm">
                Your session has expired. Please sign in again to continue.
              </p>
            </div>
          )}

          <div className="text-center mb-8">
            <h2 className="text-2xl font-serif text-text-primary">
              Welcome
            </h2>
            <p className="mt-2 text-text-secondary">
              Sign in to continue your conversation
            </p>
          </div>

          {/* Google Sign-In Button Container */}
          <div className="flex flex-col items-center gap-4 mb-8">
            <div className="min-h-[44px] flex items-center justify-center">
              {loadFailed ? (
                <div className="text-center">
                  <p className="text-red-500 text-sm mb-3">Sign-in failed to load</p>
                  <button
                    onClick={handleRetry}
                    className="px-4 py-2 bg-lavender/20 hover:bg-lavender/30 text-lavender-text rounded-md text-sm transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              ) : !buttonRendered ? (
                <div className="flex items-center gap-2 px-6 py-3 border border-gray-300 rounded-md bg-white">
                  <svg className="w-5 h-5 animate-spin text-gray-400" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  <span className="text-gray-500 text-sm">Loading Google Sign-In...</span>
                </div>
              ) : null}
              <div 
                id="google-signin-button" 
                className={buttonRendered ? '' : 'hidden'}
              />
            </div>
            
            {/* Use different account link */}
            {buttonRendered && (
              <button
                onClick={handleSwitchAccount}
                className="text-sm text-lavender-text/70 hover:text-lavender-text underline transition-colors"
              >
                Use a different account
              </button>
            )}
            
            {/* Trouble signing in link */}
            {!loadFailed && (
              <button
                onClick={handleRetry}
                className="text-xs text-text-tertiary hover:text-text-secondary transition-colors"
              >
                Trouble signing in? Click to refresh
              </button>
            )}
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
