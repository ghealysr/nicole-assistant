'use client';

import Link from 'next/link';
import Image from 'next/image';
import { usePathname } from 'next/navigation';

interface AlphawaveSidebarProps {
  onVibeClick?: () => void;
  isVibeOpen?: boolean;
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
export function AlphawaveSidebar({ onVibeClick, isVibeOpen }: AlphawaveSidebarProps) {
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
    { 
      href: '/memories', 
      label: 'Memories',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
          <path d="M12 2a10 10 0 1 0 10 10A10 10 0 0 0 12 2zm0 18a8 8 0 1 1 8-8 8 8 0 0 1-8 8z"/>
          <path d="M12 6v6l4 2"/>
        </svg>
      )
    },
    { 
      href: '/settings', 
      label: 'Settings',
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" className="w-[18px] h-[18px]" strokeWidth={2}>
          <circle cx="12" cy="12" r="3"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
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
      </nav>
      
      {/* Version indicator at bottom */}
      <div className="p-3 text-xs text-[#a1a1aa] border-t border-[#333]">
        Nicole V7 • Alphawave Tech
      </div>
    </aside>
  );
}
