'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { supabase } from '@/lib/alphawave_supabase';

interface User {
  email?: string;
  user_metadata?: {
    full_name?: string;
    name?: string;
    avatar_url?: string;
  };
}

interface AlphawaveHeaderProps {
  onToggleDashboard?: () => void;
  isDashboardOpen?: boolean;
}

/**
 * Header component for Nicole V7.
 * 
 * Features:
 * - Nicole logo image (dashboard-header.png)
 * - User profile info from Supabase auth
 * - Dashboard toggle button
 * - Settings button
 */
export function AlphawaveHeader({ onToggleDashboard, isDashboardOpen }: AlphawaveHeaderProps) {
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

  return (
    <header className="nicole-header">
      {/* Nicole Logo - centered vertically in header */}
      <div className="flex items-center justify-center h-full">
        <Image 
          src="/images/dashboard-header.png" 
          alt="Nicole" 
          width={324} 
          height={97}
          className="h-[97px] w-auto object-contain"
          priority
        />
      </div>

      {/* Right side actions */}
      <div className="flex items-center gap-4">
        {/* User name */}
        <span className="text-sm font-medium text-[#6b7280]">
          {displayName}
        </span>
        
        {/* Settings button */}
        <button 
          onClick={handleLogout}
          className="w-9 h-9 border-0 bg-transparent rounded-lg cursor-pointer flex items-center justify-center transition-colors hover:bg-black/5"
          title="Sign out"
        >
          <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5 stroke-[#6b7280]" strokeWidth={2}>
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </button>
        
        {/* Dashboard toggle button */}
        <button 
          onClick={onToggleDashboard}
          className={`dashboard-btn ${isDashboardOpen ? 'active' : ''}`}
        >
          <svg viewBox="0 0 24 24" fill="none" className="w-4 h-4 stroke-white" strokeWidth={2}>
            <rect x="3" y="3" width="7" height="9" rx="1"/>
            <rect x="14" y="3" width="7" height="5" rx="1"/>
            <rect x="14" y="12" width="7" height="9" rx="1"/>
            <rect x="3" y="16" width="7" height="5" rx="1"/>
          </svg>
          Dashboard
        </button>
      </div>
    </header>
  );
}
