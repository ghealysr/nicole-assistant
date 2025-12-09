'use client';

import Image from 'next/image';
import { useGoogleAuth } from '@/lib/google_auth';

interface AlphawaveHeaderProps {
  onToggleDashboard?: () => void;
  isDashboardOpen?: boolean;
}

/**
 * Header component for Nicole V7.
 * 
 * Features:
 * - Nicole logo image (dashboard-header.png)
 * - User profile info from Google OAuth
 * - Dashboard toggle button
 * - Sign out button
 */
export function AlphawaveHeader({ onToggleDashboard, isDashboardOpen }: AlphawaveHeaderProps) {
  const { user, signOut } = useGoogleAuth();

  // Get display name from user data
  const displayName = user?.name || user?.email?.split('@')[0] || 'User';

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
        {/* User avatar and name */}
        <div className="flex items-center gap-2">
          {user?.picture && (
            <img 
              src={user.picture} 
              alt={displayName}
              className="w-8 h-8 rounded-full"
            />
          )}
          <span className="text-sm font-medium text-[#6b7280]">
            {displayName}
          </span>
        </div>
        
        {/* Sign out button */}
        <button 
          onClick={signOut}
          className="w-9 h-9 border-0 bg-transparent rounded-lg cursor-pointer flex items-center justify-center transition-colors hover:bg-black/5"
          title="Sign out"
        >
          <svg viewBox="0 0 24 24" fill="none" className="w-5 h-5 stroke-[#6b7280]" strokeWidth={2}>
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
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
