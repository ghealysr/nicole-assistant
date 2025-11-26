'use client';

import { useState } from 'react';

/**
 * Sidebar component for Nicole V7.
 * Collapses to 60px and expands to 240px.
 */
export function AlphawaveSidebar() {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <aside
      className={`bg-white border-r border-border-line transition-all duration-300 ${
        isExpanded ? 'w-60' : 'w-15'
      }`}
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => setIsExpanded(false)}
    >
      <nav className="p-4">
        <ul className="space-y-2">
          <li>
            <a
              href="/chat"
              className="flex items-center px-3 py-2 text-text-primary hover:bg-light-gray rounded-lg"
            >
              <span className="mr-3">💬</span>
              {isExpanded && <span>Chat</span>}
            </a>
          </li>
          <li>
            <a
              href="/dashboard"
              className="flex items-center px-3 py-2 text-text-primary hover:bg-light-gray rounded-lg"
            >
              <span className="mr-3">📊</span>
              {isExpanded && <span>Dashboard</span>}
            </a>
          </li>
        </ul>
      </nav>
    </aside>
  );
}
