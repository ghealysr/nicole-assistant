'use client';

import { useState } from 'react';
import { AlphawaveSidebar } from '@/components/navigation/AlphawaveSidebar';
import { AlphawaveVibeWorkspace } from '@/components/vibe/AlphawaveVibeWorkspace';

/**
 * Authenticated app layout with sidebar and Vibe workspace.
 * 
 * QA NOTES:
 * - Sidebar: 240px fixed width (dark theme)
 * - Main content area fills remaining space
 * - Vibe workspace slides in from right when toggled
 * - Header is now managed per-page (e.g., chat has its own header with dashboard toggle)
 * - Used for all authenticated routes (chat, dashboard, journal, etc.)
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [isVibeOpen, setIsVibeOpen] = useState(false);

  const toggleVibe = () => {
    setIsVibeOpen(prev => !prev);
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar: 240px fixed */}
      <AlphawaveSidebar onVibeClick={toggleVibe} isVibeOpen={isVibeOpen} />

      {/* Main content area */}
      <main className="flex-1 min-w-0 overflow-hidden">
        {children}
      </main>

      {/* Vibe Workspace - slides in from right */}
      <AlphawaveVibeWorkspace isOpen={isVibeOpen} onClose={() => setIsVibeOpen(false)} />
    </div>
  );
}
