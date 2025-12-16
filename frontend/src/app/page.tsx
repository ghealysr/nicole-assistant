'use client';

import { useEffect } from 'react';
import { isAuthenticated } from '@/lib/alphawave_utils';

/**
 * Home page component.
 * Redirects to login if not authenticated, otherwise to chat.
 */
export default function HomePage() {
  useEffect(() => {
    const checkAuth = () => {
      if (isAuthenticated()) {
        window.location.href = '/chat';
      } else {
        window.location.href = '/login';
      }
    };

    checkAuth();
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0A0A0F]">
      <div className="flex flex-col items-center gap-4">
        <div className="w-8 h-8 border-2 border-[#6366F1] border-t-transparent rounded-full animate-spin" />
        <p className="text-[#94A3B8]">Loading...</p>
      </div>
    </div>
  );
}
