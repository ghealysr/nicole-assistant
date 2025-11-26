import type { Metadata } from 'next';
import { AlphawaveSidebar } from '@/components/navigation/AlphawaveSidebar';
import { AlphawaveHeader } from '@/components/navigation/AlphawaveHeader';
import { ToastProvider } from '@/components/ui/alphawave_toast';
import './globals.css';

/**
 * Application Metadata
 */
export const metadata: Metadata = {
  title: 'Nicole - Your AI Companion',
  description: 'Nicole V7 - Personal AI assistant for the Healy family',
  icons: {
    icon: '/favicon.ico',
  },
};

/**
 * Root layout component for Nicole V7.
 * 
 * QA NOTES:
 * - Includes ToastProvider for app-wide notifications
 * - Sidebar: 60px collapsed, 240px expanded
 * - Header: 80px height
 * - Main content area fills remaining space
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-cream text-text-primary font-sans">
        <ToastProvider>
          <div className="flex h-screen">
            {/* Sidebar: 60px collapsed, 240px expanded */}
            <AlphawaveSidebar />

            <div className="flex-1 flex flex-col">
              {/* Header: 80px height */}
              <AlphawaveHeader />

              {/* Main content area */}
              <main className="flex-1 overflow-auto">
                {children}
              </main>
            </div>
          </div>
        </ToastProvider>
      </body>
    </html>
  );
}
