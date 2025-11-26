'use client';

import { useEffect } from 'react';
import { supabase } from '@/lib/alphawave_supabase';

/**
 * Home page component.
 * Redirects to login if not authenticated, otherwise to chat.
 */
export default function HomePage() {
  useEffect(() => {
    const checkAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        window.location.href = '/chat';
      } else {
        window.location.href = '/login';
      }
    };

    checkAuth();
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-text-secondary">Loading...</p>
    </div>
  );
}
