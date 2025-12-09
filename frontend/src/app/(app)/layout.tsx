'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { AlphawaveSidebar } from '@/components/navigation/AlphawaveSidebar';
import { AlphawaveVibeWorkspace } from '@/components/vibe/AlphawaveVibeWorkspace';
import { AlphawaveMemoryDashboard } from '@/components/memory/AlphawaveMemoryDashboard';
import { AlphawaveJournalPanel } from '@/components/journal/AlphawaveJournalPanel';
import { AlphawaveChatsPanel } from '@/components/chat/AlphawaveChatsPanel';
import { ConversationProvider, useConversation } from '@/lib/context/ConversationContext';
import { useGoogleAuth } from '@/lib/google_auth';

/**
 * Auth guard component - redirects to login if not authenticated
 */
function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useGoogleAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  // Show loading while checking auth
  if (isLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-cream">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-lavender/20 flex items-center justify-center mx-auto mb-4 animate-pulse">
            <span className="text-lavender-text text-3xl font-serif">N</span>
          </div>
          <p className="text-text-secondary">Loading...</p>
        </div>
      </div>
    );
  }

  // Don't render children if not authenticated
  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}

/**
 * Inner layout component that uses the conversation context
 */
function AppLayoutInner({ children }: { children: React.ReactNode }) {
  const [isVibeOpen, setIsVibeOpen] = useState(false);
  const [isMemoryOpen, setIsMemoryOpen] = useState(false);
  const [isJournalOpen, setIsJournalOpen] = useState(false);
  const [isChatsOpen, setIsChatsOpen] = useState(false);
  
  const { currentConversationId, setCurrentConversationId, clearConversation } = useConversation();

  // Close all panels helper
  const closeAllPanels = useCallback(() => {
    setIsVibeOpen(false);
    setIsMemoryOpen(false);
    setIsJournalOpen(false);
    setIsChatsOpen(false);
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

  // Toggle Chats - closes others if open
  const toggleChats = useCallback(() => {
    if (isChatsOpen) {
      setIsChatsOpen(false);
    } else {
      closeAllPanels();
      setIsChatsOpen(true);
    }
  }, [isChatsOpen, closeAllPanels]);

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
        onChatsClick={toggleChats}
        isChatsOpen={isChatsOpen}
        onNewChat={clearConversation}
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

      {/* Chats Panel - slides in from right */}
      <AlphawaveChatsPanel 
        isOpen={isChatsOpen} 
        onClose={() => setIsChatsOpen(false)}
        onSelectConversation={setCurrentConversationId}
        onNewChat={clearConversation}
        currentConversationId={currentConversationId}
      />
    </div>
  );
}

/**
 * Authenticated app layout with sidebar and slide-out panels.
 * 
 * QA NOTES:
 * - Protected by AuthGuard - redirects to login if not authenticated
 * - Sidebar: 240px fixed width (dark theme)
 * - Main content area fills remaining space
 * - All slide-out panels are MUTUALLY EXCLUSIVE:
 *   Vibe, Memory, Journal, and Chats (only one open at a time)
 * - Header is managed per-page (e.g., chat has its own header)
 * - Used for all authenticated routes (chat, dashboard, journal, etc.)
 * - Conversation state managed via context for cross-component access
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <ConversationProvider>
        <AppLayoutInner>{children}</AppLayoutInner>
      </ConversationProvider>
    </AuthGuard>
  );
}
