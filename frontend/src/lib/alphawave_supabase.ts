import { createClientComponentClient } from '@supabase/auth-helpers-nextjs';

/**
 * Supabase client for the frontend application.
 * Configured for client-side operations with the provided environment variables.
 */
export const supabase = createClientComponentClient({
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL!,
  supabaseKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
});
