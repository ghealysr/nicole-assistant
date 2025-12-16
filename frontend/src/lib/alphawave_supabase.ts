/**
 * Legacy Supabase stub - Nicole now uses Google OAuth
 * 
 * This file exists for backwards compatibility with any legacy imports.
 * All authentication is now handled via Google OAuth in alphawave_utils.ts
 */

// Stub supabase client that does nothing
export const supabase = {
  auth: {
    getSession: async () => ({ data: { session: null }, error: null }),
    getUser: async () => ({ data: { user: null }, error: null }),
    signOut: async () => ({ error: null }),
    onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
  },
};
