'use client';

import { useState, useCallback } from 'react';
import { AlphawaveSidebar } from '@/components/navigation/AlphawaveSidebar';
import { AlphawaveVibeWorkspace } from '@/components/vibe/AlphawaveVibeWorkspace';
import { AlphawaveMemoryDashboard } from '@/components/memory/AlphawaveMemoryDashboard';

/**
 * Authenticated app layout with sidebar, Vibe workspace, and Memory Dashboard.
 * 
 * QA NOTES:
 * - Sidebar: 240px fixed width (dark theme)
 * - Main content area fills remaining space
 * - Vibe workspace and Memory Dashboard are MUTUALLY EXCLUSIVE
 *   (opening one closes the other - only one dashboard at a time)
 * - Header is now managed per-page (e.g., chat has its own header with dashboard toggle)
 * - Used for all authenticated routes (chat, dashboard, journal, etc.)
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [isVibeOpen, setIsVibeOpen] = useState(false);
  const [isMemoryOpen, setIsMemoryOpen] = useState(false);

  // Toggle Vibe - closes Memory if open
  const toggleVibe = useCallback(() => {
    if (isVibeOpen) {
      setIsVibeOpen(false);
    } else {
      setIsVibeOpen(true);
      setIsMemoryOpen(false); // Close memory when opening vibe
    }
  }, [isVibeOpen]);

  // Toggle Memory - closes Vibe if open
  const toggleMemory = useCallback(() => {
    if (isMemoryOpen) {
      setIsMemoryOpen(false);
    } else {
      setIsMemoryOpen(true);
      setIsVibeOpen(false); // Close vibe when opening memory
    }
  }, [isMemoryOpen]);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar: 240px fixed */}
      <AlphawaveSidebar 
        onVibeClick={toggleVibe} 
        isVibeOpen={isVibeOpen}
        onMemoryClick={toggleMemory}
        isMemoryOpen={isMemoryOpen}
      />

      {/* Main content area */}
      <main className="flex-1 min-w-0 overflow-hidden">
        {children}
      </main>

      {/* Vibe Workspace - slides in from right */}
      <AlphawaveVibeWorkspace isOpen={isVibeOpen} onClose={() => setIsVibeOpen(false)} />

      {/* Memory Dashboard - slides in from right */}
      <AlphawaveMemoryDashboard isOpen={isMemoryOpen} onClose={() => setIsMemoryOpen(false)} />
    </div>
  );
}
