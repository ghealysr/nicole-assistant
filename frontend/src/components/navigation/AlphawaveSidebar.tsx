'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';

interface AlphawaveSidebarProps {
  onVibeClick?: () => void;
  isVibeOpen?: boolean;
  onMemoryClick?: () => void;
  onDocumentsClick?: () => void;
  onHistoryClick?: () => void;
  isMemoryOpen?: boolean;
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
  onDocumentsClick, 
  onHistoryClick,
  isMemoryOpen 
}: AlphawaveSidebarProps) {
  const pathname = usePathname();

  const menuItems = [
    { 
      href: '/chat', 
      label: 'New Chat',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
          <path d="M12 5v14M5 12h14"/>
        </svg>
      )
    },
    { 
      href: '/journal', 
      label: 'Journal',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
        </svg>
      )
    },
  ];

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
        {menuItems.map((item) => {
          const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`menu-item ${isActive ? 'active' : ''}`}
            >
              {item.icon}
              {item.label}
            </Link>
          );
        })}
        
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

        {/* Documents Button - Opens Memory Dashboard to Documents tab */}
        <button
          onClick={onDocumentsClick}
          className="menu-item"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          Documents
        </button>

        {/* History Button - Opens Memory Dashboard to History tab */}
        <button
          onClick={onHistoryClick}
          className="menu-item"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
          History
        </button>
      </nav>
      
      {/* Version indicator at bottom */}
      <div className="p-3 text-xs text-[#a1a1aa] border-t border-[#333]">
        Nicole V7 • Alphawave Tech
      </div>
    </aside>
  );
}
