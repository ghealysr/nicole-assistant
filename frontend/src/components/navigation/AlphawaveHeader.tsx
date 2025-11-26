'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/alphawave_supabase';

interface User {
  email?: string;
  user_metadata?: {
    full_name?: string;
    name?: string;
    avatar_url?: string;
  };
}

/**
 * Header component for Nicole V7.
 * 
 * Features:
 * - Fixed height of 80px
 * - Displays user profile info from Supabase auth
 * - Logout functionality
 * - Clean, minimal design
 */
export function AlphawaveHeader() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => subscription.unsubscribe();
  }, []);

  /**
   * Handles user logout.
   */
  async function handleLogout() {
    await supabase.auth.signOut();
    window.location.href = '/login';
  }

  // Get display name from user data
  const displayName = user?.user_metadata?.full_name 
    || user?.user_metadata?.name 
    || user?.email?.split('@')[0] 
    || 'User';

  // Get first letter for avatar
  const avatarLetter = displayName.charAt(0).toUpperCase();

  return (
    <header className="bg-white border-b border-border-line h-20 flex items-center justify-between px-6 shrink-0">
      {/* Logo/Brand */}
      <div className="flex items-center">
        <div className="w-10 h-10 rounded-full bg-lavender/20 flex items-center justify-center mr-3">
          <span className="text-lavender-text text-lg font-serif">N</span>
        </div>
        <h1 className="text-xl font-serif text-lavender-text">Nicole</h1>
      </div>

      {/* User info and actions */}
      <div className="flex items-center space-x-4">
        {/* User profile */}
        <div className="flex items-center space-x-3">
          {user?.user_metadata?.avatar_url ? (
            <img 
              src={user.user_metadata.avatar_url} 
              alt={displayName}
              className="w-8 h-8 rounded-full"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-mint flex items-center justify-center">
              <span className="text-mint-dark text-sm font-medium">{avatarLetter}</span>
            </div>
          )}
          <span className="text-text-secondary text-sm hidden sm:inline">
            {displayName}
          </span>
        </div>

        {/* Logout button */}
        <button
          onClick={handleLogout}
          className="px-3 py-2 text-text-secondary hover:text-text-primary hover:bg-light-gray rounded-lg text-sm transition-colors"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
