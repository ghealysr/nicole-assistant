'use client';

import { supabase } from '@/lib/alphawave_supabase';
import { useState } from 'react';

/**
 * Login page component for Nicole V7.
 * Handles Google OAuth and email/password authentication.
 */
export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  /**
   * Handles Google OAuth login and redirects to the auth callback page.
   */
  async function handleGoogleLogin() {
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    });
  }

  /**
   * Handles email and password login.
   */
  async function handleEmailLogin() {
    await supabase.auth.signInWithPassword({ email, password });
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-cream">
      <div className="max-w-md w-full space-y-8 p-8">
        <div className="text-center">
          <h1 className="text-3xl font-serif text-lavender-text">
            Welcome to Nicole
          </h1>
          <p className="mt-2 text-text-secondary">
            Sign in to access your personalized assistant.
          </p>
        </div>

        <button
          onClick={handleGoogleLogin}
          className="w-full flex justify-center items-center px-4 py-3 border border-border-light rounded-lg text-text-primary bg-white hover:bg-light-gray focus:outline-none focus:ring-2 focus:ring-lavender"
        >
          <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
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
          Sign in with Google
        </button>

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-border-line" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-2 bg-cream text-text-tertiary">Or</span>
          </div>
        </div>

        <div className="space-y-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-border-light px-4 py-3 text-text-primary bg-white focus:outline-none focus:ring-2 focus:ring-lavender"
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-border-light px-4 py-3 text-text-primary bg-white focus:outline-none focus:ring-2 focus:ring-lavender"
          />

          <button
            onClick={handleEmailLogin}
            className="w-full flex justify-center px-4 py-3 border border-transparent rounded-lg text-white bg-lavender hover:bg-lavender-text focus:outline-none focus:ring-2 focus:ring-lavender"
          >
            Sign in with Email
          </button>
        </div>
      </div>
    </div>
  );
}
