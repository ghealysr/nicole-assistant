import type { Metadata } from 'next';
import { ToastProvider } from '@/components/ui/alphawave_toast';
import { GoogleAuthProvider } from '@/lib/google_auth';
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

// Google OAuth Client ID - hardcoded to avoid Vercel env var caching issues
// This is a CLIENT ID (not a secret) so it's safe to include in client-side code
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '510889875238-hpfcf1jr9mvb9rkoipj0u5esv2jbnk60.apps.googleusercontent.com';

/**
 * Root layout component for Nicole V7.
 * 
 * Features:
 * - GoogleAuthProvider for authentication
 * - ToastProvider for app-wide notifications
 * - Login page has its own full-screen layout
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-cream text-text-primary font-sans antialiased">
        <GoogleAuthProvider clientId={GOOGLE_CLIENT_ID}>
          <ToastProvider>
            {children}
          </ToastProvider>
        </GoogleAuthProvider>
      </body>
    </html>
  );
}
