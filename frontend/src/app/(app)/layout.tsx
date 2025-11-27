import { AlphawaveSidebar } from '@/components/navigation/AlphawaveSidebar';

/**
 * Authenticated app layout with sidebar.
 * 
 * QA NOTES:
 * - Sidebar: 240px fixed width (dark theme)
 * - Main content area fills remaining space
 * - Header is now managed per-page (e.g., chat has its own header with dashboard toggle)
 * - Used for all authenticated routes (chat, dashboard, journal, etc.)
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar: 240px fixed */}
      <AlphawaveSidebar />

      {/* Main content area */}
      <main className="flex-1 min-w-0 overflow-hidden">
        {children}
      </main>
    </div>
  );
}
