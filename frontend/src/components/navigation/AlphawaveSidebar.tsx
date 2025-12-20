'use client';

import { usePathname } from 'next/navigation';
import { LotusSphere } from '@/components/chat/LotusSphere';

interface AlphawaveSidebarProps {
  onFazCodeClick?: () => void;
  isFazCodeOpen?: boolean;
  onMemoryClick?: () => void;
  isMemoryOpen?: boolean;
  onJournalClick?: () => void;
  isJournalOpen?: boolean;
  onChatsClick?: () => void;
  isChatsOpen?: boolean;
  onImageStudioClick?: () => void;
  isImageStudioOpen?: boolean;
  onResearchClick?: () => void;
  isResearchOpen?: boolean;
  onNewChat?: () => void;
}

/**
 * Sidebar component for Nicole V7.
 * 
 * Features:
 * - Dark theme sidebar
 * - Alphawave logo at top (large size)
 * - Navigation items with icons
 * - Faz Code button to open coding workspace panel
 * - Active state highlighting
 */
export function AlphawaveSidebar({ 
  onFazCodeClick,
  isFazCodeOpen,
  onMemoryClick, 
  isMemoryOpen,
  onJournalClick,
  isJournalOpen,
  onChatsClick,
  isChatsOpen,
  onImageStudioClick,
  isImageStudioOpen,
  onResearchClick,
  isResearchOpen,
  onNewChat,
}: AlphawaveSidebarProps) {
  const pathname = usePathname();

  const isOnChat = pathname === '/chat' || pathname?.startsWith('/chat/');

  return (
    <aside className="w-60 bg-[#1a1a1a] flex flex-col shrink-0">
      {/* Logo - LotusSphere in idle state */}
      <div className="p-3 border-b border-[#333] flex justify-center">
        <LotusSphere 
          state="default"
          size={160}
          isActive={true}
        />
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
        
        {/* Image Studio Button - Opens Image Generation Panel */}
        <button
          onClick={onImageStudioClick}
          className={`menu-item ${isImageStudioOpen ? 'active' : ''}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <circle cx="8.5" cy="8.5" r="1.5"/>
            <path d="M21 15l-5-5L5 21"/>
          </svg>
          Images
        </button>

        {/* Research Button - Opens Deep Research Panel */}
        <button
          onClick={onResearchClick}
          className={`menu-item ${isResearchOpen ? 'active' : ''}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          Research
        </button>

        {/* Faz Code Button - Opens AI coding workspace panel */}
        <button
          onClick={onFazCodeClick}
          className={`menu-item vibe-btn ${isFazCodeOpen ? 'vibe-active' : ''}`}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
            <polyline points="16 18 22 12 16 6"/>
            <polyline points="8 6 2 12 8 18"/>
          </svg>
          Faz Code
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
      <div className="p-3 text-xs text-white border-t border-[#333] text-center">
        Nicole V7 • AlphaWave
      </div>
    </aside>
  );
}
