'use client';

/**
 * Nicole V7 - Google OAuth Authentication
 * 
 * Provides Google Sign-In functionality and auth context for the entire app.
 * Stores the ID token in localStorage and provides it for API calls.
 * 
 * Usage:
 *   // In layout.tsx:
 *   <GoogleAuthProvider clientId="...">
 *     {children}
 *   </GoogleAuthProvider>
 * 
 *   // In components:
 *   const { user, token, signIn, signOut, isLoading } = useGoogleAuth();
 *   
 *   // For API calls:
 *   headers: { 'Authorization': `Bearer ${token}` }
 */

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

// Google Identity Services types
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: GoogleInitConfig) => void;
          renderButton: (element: HTMLElement, config: GoogleButtonConfig) => void;
          prompt: () => void;
          revoke: (email: string, callback: () => void) => void;
        };
      };
    };
  }
}

interface GoogleInitConfig {
  client_id: string;
  callback: (response: GoogleCredentialResponse) => void;
  auto_select?: boolean;
  cancel_on_tap_outside?: boolean;
}

interface GoogleButtonConfig {
  type?: 'standard' | 'icon';
  theme?: 'outline' | 'filled_blue' | 'filled_black';
  size?: 'large' | 'medium' | 'small';
  text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin';
  shape?: 'rectangular' | 'pill' | 'circle' | 'square';
  logo_alignment?: 'left' | 'center';
  width?: number;
}

interface GoogleCredentialResponse {
  credential: string;
  select_by: string;
}

// User info extracted from Google ID token
interface GoogleUser {
  id: string;        // Google's unique user ID (sub)
  email: string;
  name: string;
  picture: string;
  email_verified: boolean;
}

// Auth context value
interface GoogleAuthContextValue {
  user: GoogleUser | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isGoogleReady: boolean;
  signIn: () => void;
  signOut: () => void;
  renderSignInButton: (elementId: string) => void;
}

const GoogleAuthContext = createContext<GoogleAuthContextValue | null>(null);

// Decode JWT payload (no verification - server does that)
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

// Check if token is expired
function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return true;
  const exp = payload.exp as number;
  return Date.now() >= exp * 1000;
}

// Check if token expires soon (within 5 minutes)
function isTokenExpiringSoon(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return true;
  const exp = payload.exp as number;
  const fiveMinutes = 5 * 60 * 1000;
  return Date.now() >= (exp * 1000) - fiveMinutes;
}

// Get time until token expires (in minutes)
function getTokenExpiryMinutes(token: string): number {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return 0;
  const exp = payload.exp as number;
  const msRemaining = (exp * 1000) - Date.now();
  return Math.max(0, Math.floor(msRemaining / 60000));
}

// Extract user info from token
function getUserFromToken(token: string): GoogleUser | null {
  const payload = decodeJwtPayload(token);
  if (!payload) return null;
  
  const email = payload.email as string | undefined;
  
  return {
    id: payload.sub as string,
    email: email || '',
    name: (payload.name as string) || email?.split('@')[0] || 'User',
    picture: (payload.picture as string) || '',
    email_verified: (payload.email_verified as boolean) || false,
  };
}

const STORAGE_KEY = 'nicole_google_token';

interface GoogleAuthProviderProps {
  clientId: string;
  children: ReactNode;
}

export function GoogleAuthProvider({ clientId, children }: GoogleAuthProviderProps) {
  const [user, setUser] = useState<GoogleUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGsiLoaded, setIsGsiLoaded] = useState(false);

  // Handle credential response from Google
  const handleCredentialResponse = useCallback((response: GoogleCredentialResponse) => {
    const credential = response.credential;
    
    // Extract user info
    const userInfo = getUserFromToken(credential);
    
    if (userInfo) {
      // Store token and user
      localStorage.setItem(STORAGE_KEY, credential);
      setToken(credential);
      setUser(userInfo);
      
      // Redirect to chat after login
      window.location.href = '/chat';
    }
  }, []);

  // Load Google Identity Services script
  useEffect(() => {
    // If Google API is already available, we're good
    if (typeof window !== 'undefined' && window.google?.accounts?.id) {
      setIsGsiLoaded(true);
      return;
    }

    // Check if script already exists
    const existingScript = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
    
    if (existingScript) {
      // Script exists - poll for window.google to be ready
      const checkGoogle = setInterval(() => {
        if (window.google?.accounts?.id) {
          setIsGsiLoaded(true);
          clearInterval(checkGoogle);
        }
      }, 100);
      // Stop polling after 10 seconds
      setTimeout(() => clearInterval(checkGoogle), 10000);
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      // Poll for window.google to be ready after script loads
      const checkGoogle = setInterval(() => {
        if (window.google?.accounts?.id) {
          setIsGsiLoaded(true);
          clearInterval(checkGoogle);
        }
      }, 50);
      setTimeout(() => clearInterval(checkGoogle), 5000);
    };
    script.onerror = () => {
      console.error('[GoogleAuth] Failed to load Google Identity Services script');
    };
    document.head.appendChild(script);
  }, []);

  // Initialize Google Sign-In when script loads
  useEffect(() => {
    if (!isGsiLoaded || !window.google) return;
    
    // Don't initialize if clientId is missing
    if (!clientId) {
      console.error('[GoogleAuth] NEXT_PUBLIC_GOOGLE_CLIENT_ID is not set');
      return;
    }

    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: handleCredentialResponse,
      auto_select: false,
      cancel_on_tap_outside: true,
    });
  }, [isGsiLoaded, clientId, handleCredentialResponse]);

  // Check for existing token on mount
  useEffect(() => {
    // Only access localStorage on client side
    if (typeof window === 'undefined') {
      setIsLoading(false);
      return;
    }

    try {
      const storedToken = localStorage.getItem(STORAGE_KEY);
      
      if (storedToken && !isTokenExpired(storedToken)) {
        const userInfo = getUserFromToken(storedToken);
        if (userInfo) {
          setToken(storedToken);
          setUser(userInfo);
        } else {
          localStorage.removeItem(STORAGE_KEY);
        }
      } else if (storedToken) {
        // Token expired, remove it
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch (e) {
      console.error('[GoogleAuth] Error checking stored token:', e);
    }
    
    setIsLoading(false);
  }, []);

  // Periodic token expiration check - warn user before expiry
  useEffect(() => {
    if (!token) return;
    
    const checkTokenExpiry = () => {
      if (isTokenExpired(token)) {
        console.warn('[GoogleAuth] Token expired, signing out');
        localStorage.removeItem(STORAGE_KEY);
        setToken(null);
        setUser(null);
        // Show alert and redirect
        alert('Your session has expired. Please sign in again.');
        window.location.href = '/login';
      } else if (isTokenExpiringSoon(token)) {
        const minutes = getTokenExpiryMinutes(token);
        console.warn(`[GoogleAuth] Token expires in ${minutes} minutes`);
        // Trigger Google One Tap to silently refresh if possible
        if (window.google && isGsiLoaded) {
          // Cast to any to use the callback overload which isn't in our type definitions
          (window.google.accounts.id.prompt as (callback?: (notification: { isNotDisplayed: () => boolean; isSkippedMoment: () => boolean }) => void) => void)((notification) => {
            if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
              console.log('[GoogleAuth] Could not auto-refresh token, user may need to re-login');
            }
          });
        }
      }
    };
    
    // Check immediately
    checkTokenExpiry();
    
    // Check every minute
    const interval = setInterval(checkTokenExpiry, 60000);
    
    return () => clearInterval(interval);
  }, [token, isGsiLoaded]);

  // Sign in - prompt Google One Tap
  const signIn = useCallback(() => {
    if (window.google) {
      window.google.accounts.id.prompt();
    }
  }, []);

  // Sign out
  const signOut = useCallback(() => {
    if (user?.email && window.google) {
      window.google.accounts.id.revoke(user.email, () => {
        localStorage.removeItem(STORAGE_KEY);
        setToken(null);
        setUser(null);
        window.location.href = '/login';
      });
    } else {
      localStorage.removeItem(STORAGE_KEY);
      setToken(null);
      setUser(null);
      window.location.href = '/login';
    }
  }, [user]);

  // Render Google Sign-In button
  const renderSignInButton = useCallback((elementId: string) => {
    if (!isGsiLoaded || !window.google) return;
    
    // Don't render if clientId is missing
    if (!clientId) {
      console.error('[GoogleAuth] Cannot render button: NEXT_PUBLIC_GOOGLE_CLIENT_ID is not set');
      return;
    }
    
    const element = document.getElementById(elementId);
    if (element) {
      window.google.accounts.id.renderButton(element, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        shape: 'rectangular',
        width: 300,
      });
    }
  }, [isGsiLoaded, clientId]);

  const value: GoogleAuthContextValue = {
    user,
    token,
    isLoading,
    isAuthenticated: !!token && !!user,
    isGoogleReady: isGsiLoaded && !!clientId,
    signIn,
    signOut,
    renderSignInButton,
  };

  return (
    <GoogleAuthContext.Provider value={value}>
      {children}
    </GoogleAuthContext.Provider>
  );
}

export function useGoogleAuth(): GoogleAuthContextValue {
  const context = useContext(GoogleAuthContext);
  if (!context) {
    throw new Error('useGoogleAuth must be used within a GoogleAuthProvider');
  }
  return context;
}

// Helper to get token for API calls (can be used outside React)
// Checks all possible token storage keys for maximum compatibility
export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  
  // Check all token keys used across the app (order: newest to oldest)
  const token = 
    localStorage.getItem(STORAGE_KEY) ||           // nicole_google_token (Google OAuth)
    localStorage.getItem('nicole_token') ||         // Legacy Nicole token
    localStorage.getItem('auth_token');             // Generic auth token
  
  if (token && !isTokenExpired(token)) {
    return token;
  }
  return null;
}

// Helper hook for API calls
export function useAuthHeaders(): Record<string, string> {
  const { token } = useGoogleAuth();
  
  if (!token) {
    return {};
  }
  
  return {
    'Authorization': `Bearer ${token}`,
  };
}

