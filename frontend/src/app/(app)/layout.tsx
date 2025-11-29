'use client';

import { useState, useCallback } from 'react';
import { AlphawaveSidebar } from '@/components/navigation/AlphawaveSidebar';
import { AlphawaveVibeWorkspace } from '@/components/vibe/AlphawaveVibeWorkspace';
import { AlphawaveMemoryDashboard } from '@/components/memory/AlphawaveMemoryDashboard';
import { AlphawaveJournalPanel } from '@/components/journal/AlphawaveJournalPanel';

/**
 * Authenticated app layout with sidebar and slide-out panels.
 * 
 * QA NOTES:
 * - Sidebar: 240px fixed width (dark theme)
 * - Main content area fills remaining space
 * - All slide-out panels are MUTUALLY EXCLUSIVE:
 *   Vibe, Memory, and Journal (only one open at a time)
 * - Header is managed per-page (e.g., chat has its own header)
 * - Used for all authenticated routes (chat, dashboard, journal, etc.)
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [isVibeOpen, setIsVibeOpen] = useState(false);
  const [isMemoryOpen, setIsMemoryOpen] = useState(false);
  const [isJournalOpen, setIsJournalOpen] = useState(false);

  // Close all panels helper
  const closeAllPanels = useCallback(() => {
    setIsVibeOpen(false);
    setIsMemoryOpen(false);
    setIsJournalOpen(false);
  }, []);

  // Toggle Vibe - closes others if open
  const toggleVibe = useCallback(() => {
    if (isVibeOpen) {
      setIsVibeOpen(false);
    } else {
      closeAllPanels();
      setIsVibeOpen(true);
    }
  }, [isVibeOpen, closeAllPanels]);

  // Toggle Memory - closes others if open
  const toggleMemory = useCallback(() => {
    if (isMemoryOpen) {
      setIsMemoryOpen(false);
    } else {
      closeAllPanels();
      setIsMemoryOpen(true);
    }
  }, [isMemoryOpen, closeAllPanels]);

  // Toggle Journal - closes others if open
  const toggleJournal = useCallback(() => {
    if (isJournalOpen) {
      setIsJournalOpen(false);
    } else {
      closeAllPanels();
      setIsJournalOpen(true);
    }
  }, [isJournalOpen, closeAllPanels]);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar: 240px fixed */}
      <AlphawaveSidebar 
        onVibeClick={toggleVibe} 
        isVibeOpen={isVibeOpen}
        onMemoryClick={toggleMemory}
        isMemoryOpen={isMemoryOpen}
        onJournalClick={toggleJournal}
        isJournalOpen={isJournalOpen}
      />

      {/* Main content area */}
      <main className="flex-1 min-w-0 overflow-hidden">
        {children}
      </main>

      {/* Vibe Workspace - slides in from right */}
      <AlphawaveVibeWorkspace isOpen={isVibeOpen} onClose={() => setIsVibeOpen(false)} />

      {/* Memory Dashboard - slides in from right */}
      <AlphawaveMemoryDashboard isOpen={isMemoryOpen} onClose={() => setIsMemoryOpen(false)} />

      {/* Journal Panel - slides in from right */}
      <AlphawaveJournalPanel isOpen={isJournalOpen} onClose={() => setIsJournalOpen(false)} />
    </div>
  );
}
