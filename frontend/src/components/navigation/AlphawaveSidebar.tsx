'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItem {
  href: string;
  icon: string;
  label: string;
}

const navItems: NavItem[] = [
  { href: '/chat', icon: '💬', label: 'Chat' },
  { href: '/dashboard', icon: '📊', label: 'Dashboard' },
  { href: '/journal', icon: '📔', label: 'Journal' },
  { href: '/memories', icon: '🧠', label: 'Memories' },
  { href: '/settings', icon: '⚙️', label: 'Settings' },
];

/**
 * Sidebar component for Nicole V7.
 * 
 * Features:
 * - Collapses to 60px, expands to 240px on hover
 * - Active state highlighting
 * - Smooth transitions
 */
export function AlphawaveSidebar() {
  const [isExpanded, setIsExpanded] = useState(false);
  const pathname = usePathname();

  return (
    <aside
      className={`bg-white border-r border-border-line transition-all duration-300 flex flex-col shrink-0 ${
        isExpanded ? 'w-60' : 'w-16'
      }`}
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => setIsExpanded(false)}
    >
      <nav className="flex-1 p-3">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
            
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center px-3 py-3 rounded-lg transition-colors ${
                    isActive 
                      ? 'bg-lavender/10 text-lavender-text' 
                      : 'text-text-primary hover:bg-light-gray'
                  }`}
                >
                  <span className="text-xl w-8 text-center shrink-0">{item.icon}</span>
                  <span 
                    className={`ml-3 whitespace-nowrap transition-opacity ${
                      isExpanded ? 'opacity-100' : 'opacity-0 w-0 overflow-hidden'
                    }`}
                  >
                    {item.label}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      
      {/* Version indicator at bottom */}
      <div className={`p-3 text-xs text-text-tertiary ${isExpanded ? '' : 'hidden'}`}>
        Nicole V7
      </div>
    </aside>
  );
}
