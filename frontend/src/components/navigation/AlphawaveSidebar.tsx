'use client';

import Image from 'next/image';
import { usePathname } from 'next/navigation';

interface AlphawaveSidebarProps {
  onVibeClick?: () => void;
  isVibeOpen?: boolean;
  onMemoryClick?: () => void;
  isMemoryOpen?: boolean;
  onJournalClick?: () => void;
  isJournalOpen?: boolean;
  onChatsClick?: () => void;
  isChatsOpen?: boolean;
  onNewChat?: () => void;
}

/**
 * Sidebar component for Nicole V7.
 * 
 * Features:
 * - Dark theme sidebar
 * - Alphawave logo at top (large size)
 * - Navigation items with icons
 * - Vibe button to open coding workspace
 * - Active state highlighting
 */
export function AlphawaveSidebar({ 
  onVibeClick, 
  isVibeOpen, 
  onMemoryClick, 
  isMemoryOpen,
  onJournalClick,
  isJournalOpen,
  onChatsClick,
  isChatsOpen,
  onNewChat,
}: AlphawaveSidebarProps) {
  const pathname = usePathname();

  const isOnChat = pathname === '/chat' || pathname?.startsWith('/chat/');

  return (
    <aside className="w-60 bg-[#1a1a1a] flex flex-col shrink-0">
      {/* Logo - larger image */}
      <div className="p-5 border-b border-[#333]">
        <div className="flex items-center gap-4">
          <Image 
            src="/images/alphawave-logo.png" 
            alt="Alphawave" 
            width={56} 
            height={56}
            className="rounded-xl"
          />
          <span className="text-white text-xl font-semibold tracking-tight">Alphawave</span>
        </div>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 p-3 flex flex-col gap-1">
        {/* New Chat - clears current conversation */}
        <button
          onClick={onNewChat}
          className={`menu-item ${isOnChat ? 'active' : ''}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
            <path d="M12 5v14M5 12h14"/>
          </svg>
          New Chat
        </button>
        
        {/* Chats Button - Opens Conversations Panel */}
        <button
          onClick={onChatsClick}
          className={`menu-item ${isChatsOpen ? 'active' : ''}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          Chats
        </button>
        
        {/* Journal Button - Opens Journal Panel */}
        <button
          onClick={onJournalClick}
          className={`menu-item ${isJournalOpen ? 'active' : ''}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
          </svg>
          Journal
        </button>
        
        {/* Vibe Button - Special styling, opens workspace */}
        <button
          onClick={onVibeClick}
          className={`menu-item vibe-btn ${isVibeOpen ? 'vibe-active' : ''}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
            <polygon points="12 2 2 7 12 12 22 7 12 2"/>
            <polyline points="2 17 12 22 22 17"/>
            <polyline points="2 12 12 17 22 12"/>
          </svg>
          Vibe
        </button>

        {/* Divider and Data Section */}
        <div className="h-px bg-[#333] my-2" />
        <div className="px-4 py-1 pb-1 text-[11px] font-semibold text-[#6b7280] uppercase tracking-[0.5px]">
          Data
        </div>

        {/* Memory Button - Opens Memory Dashboard */}
        <button
          onClick={onMemoryClick}
          className={`menu-item ${isMemoryOpen ? 'active' : ''}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
            <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/>
            <path d="M8.5 8.5v.01"/>
            <path d="M16 15.5v.01"/>
            <path d="M12 12v.01"/>
            <path d="M11 17v.01"/>
            <path d="M7 14v.01"/>
          </svg>
          Memory
        </button>
      </nav>
      
      {/* Version indicator at bottom */}
      <div className="p-3 text-xs text-[#a1a1aa] border-t border-[#333]">
        Nicole V7 • Alphawave Tech
      </div>
    </aside>
  );
}
