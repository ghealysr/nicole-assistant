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
 * - Vibe workspace slides in from right when toggled
 * - Memory Dashboard slides in from right when Memory/Documents/History clicked
 * - Header is now managed per-page (e.g., chat has its own header with dashboard toggle)
 * - Used for all authenticated routes (chat, dashboard, journal, etc.)
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [isVibeOpen, setIsVibeOpen] = useState(false);
  const [isMemoryOpen, setIsMemoryOpen] = useState(false);

  const toggleVibe = useCallback(() => {
    setIsVibeOpen(prev => !prev);
    // Close memory dashboard when opening vibe
    if (!isVibeOpen) setIsMemoryOpen(false);
  }, [isVibeOpen]);

  const openMemoryDashboard = useCallback(() => {
    setIsMemoryOpen(true);
    // Close vibe when opening memory
    setIsVibeOpen(false);
  }, []);

  const openDocuments = useCallback(() => {
    setIsMemoryOpen(true);
    setIsVibeOpen(false);
    // The Memory Dashboard will be opened to the Documents tab
    // Tab switching is handled internally via state in the Memory Dashboard
  }, []);

  const openHistory = useCallback(() => {
    setIsMemoryOpen(true);
    setIsVibeOpen(false);
    // The Memory Dashboard will be opened to the History tab
  }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar: 240px fixed */}
      <AlphawaveSidebar 
        onVibeClick={toggleVibe} 
        isVibeOpen={isVibeOpen}
        onMemoryClick={openMemoryDashboard}
        onDocumentsClick={openDocuments}
        onHistoryClick={openHistory}
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
