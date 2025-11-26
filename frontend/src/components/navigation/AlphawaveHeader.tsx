'use client';

import { supabase } from '@/lib/alphawave_supabase';

/**
 * Header component for Nicole V7.
 * Fixed height of 80px with user profile and logout functionality.
 */
export function AlphawaveHeader() {
  /**
   * Handles user logout.
   */
  async function handleLogout() {
    await supabase.auth.signOut();
    window.location.href = '/login';
  }

  return (
    <header className="bg-white border-b border-border-line h-20 flex items-center justify-between px-6">
      <div className="flex items-center">
        <h1 className="text-xl font-serif text-lavender-text">Nicole</h1>
      </div>
      <div className="flex items-center space-x-4">
        <span className="text-text-secondary">Welcome, User</span>
        <button
          onClick={handleLogout}
          className="px-3 py-2 text-text-primary hover:bg-light-gray rounded-lg"
        >
          Logout
        </button>
      </div>
    </header>
  );
}
