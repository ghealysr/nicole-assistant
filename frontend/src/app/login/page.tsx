'use client';

import { supabase } from '@/lib/alphawave_supabase';
import { useState } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Login page component for Nicole V7.
 * 
 * Features:
 * - Google OAuth authentication
 * - Email/password fallback
 * - Clean, elegant design with Nicole branding
 * - Error handling with user feedback
 */
export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  /**
   * Handles Google OAuth login.
   */
  async function handleGoogleLogin() {
    setIsLoading(true);
    setError(null);
    
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
    
    if (error) {
      setError(error.message);
      setIsLoading(false);
    }
  }

  /**
   * Handles email/password login.
   */
  async function handleEmailLogin(e: React.FormEvent) {
    e.preventDefault();
    
    if (!email || !password) {
      setError('Please enter both email and password');
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    const { error } = await supabase.auth.signInWithPassword({ 
      email, 
      password 
    });
    
    if (error) {
      setError(error.message);
      setIsLoading(false);
    } else {
      router.push('/chat');
    }
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
            Your personal AI companion, designed to help with life's big and small moments.
          </p>
          <div className="mt-12 flex justify-center space-x-6 text-text-tertiary text-sm">
            <span>🧠 Perfect memory</span>
            <span>💬 Natural chat</span>
            <span>📊 Smart insights</span>
          </div>
        </div>
      </div>

      {/* Right side - Login form */}
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
              Welcome back
            </h2>
            <p className="mt-2 text-text-secondary">
              Sign in to continue your conversation
            </p>
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-lg text-red-600 text-sm">
              {error}
            </div>
          )}

          {/* Google login */}
          <button
            onClick={handleGoogleLogin}
            disabled={isLoading}
            className="w-full flex justify-center items-center px-4 py-3 border border-border-light rounded-lg text-text-primary bg-white hover:bg-light-gray focus:ring-2 focus:ring-lavender transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5 mr-3" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            {isLoading ? 'Signing in...' : 'Continue with Google'}
          </button>

          {/* Divider */}
          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border-line" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-cream text-text-tertiary">or sign in with email</span>
            </div>
          </div>

          {/* Email/password form */}
          <form onSubmit={handleEmailLogin} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-text-secondary mb-1.5">
                Email
              </label>
              <input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isLoading}
                className="w-full rounded-lg border border-border-light px-4 py-3 text-text-primary bg-white focus:ring-2 focus:ring-lavender focus:border-transparent transition-shadow disabled:opacity-50"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-text-secondary mb-1.5">
                Password
              </label>
              <input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                className="w-full rounded-lg border border-border-light px-4 py-3 text-text-primary bg-white focus:ring-2 focus:ring-lavender focus:border-transparent transition-shadow disabled:opacity-50"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center px-4 py-3 rounded-lg text-white bg-lavender hover:bg-lavender-text focus:ring-2 focus:ring-offset-2 focus:ring-lavender transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          {/* Footer text */}
          <p className="mt-8 text-center text-sm text-text-tertiary">
            This is a private family assistant.
            <br />
            Contact Glen if you need access.
          </p>
        </div>
      </div>
    </div>
  );
}
