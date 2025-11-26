import type { Metadata } from 'next';
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
 * - Layout structure handled by individual pages/route groups
 * - Login page has its own full-screen layout
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-cream text-text-primary font-sans antialiased">
        <ToastProvider>
          {children}
        </ToastProvider>
      </body>
    </html>
  );
}
