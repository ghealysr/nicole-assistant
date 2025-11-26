import { AlphawaveSidebar } from '@/components/navigation/AlphawaveSidebar';
import { AlphawaveHeader } from '@/components/navigation/AlphawaveHeader';

/**
 * Authenticated app layout with sidebar and header.
 * 
 * QA NOTES:
 * - Sidebar: 60px collapsed, 240px expanded
 * - Header: 80px height
 * - Main content area fills remaining space
 * - Used for all authenticated routes (chat, dashboard, journal, etc.)
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen">
      {/* Sidebar: 60px collapsed, 240px expanded */}
      <AlphawaveSidebar />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header: 80px height */}
        <AlphawaveHeader />

        {/* Main content area */}
        <main className="flex-1 overflow-hidden">
          {children}
        </main>
      </div>
    </div>
  );
}

