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
          disableAutoSelect: () => void;
          cancel: () => void;
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
  itp_support?: boolean;
  use_fedcm_for_prompt?: boolean;
}

interface GoogleButtonConfig {
  type?: 'standard' | 'icon';
  theme?: 'outline' | 'filled_blue' | 'filled_black';
  size?: 'large' | 'medium' | 'small';
  text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin';
  shape?: 'rectangular' | 'pill' | 'circle' | 'square';
  logo_alignment?: 'left' | 'center';
  width?: number;
  click_listener?: () => void;
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

// Check if token expires soon (within 15 minutes - more aggressive refresh)
function isTokenExpiringSoon(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return true;
  const exp = payload.exp as number;
  const fifteenMinutes = 15 * 60 * 1000;
  return Date.now() >= (exp * 1000) - fifteenMinutes;
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
      itp_support: true, // Support for Intelligent Tracking Prevention (Safari)
      use_fedcm_for_prompt: false, // Disable FedCM to ensure button always shows
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
      
      if (storedToken) {
        // Validate token structure first
        const parts = storedToken.split('.');
        if (parts.length !== 3) {
          console.warn('[GoogleAuth] Invalid token format, clearing');
          localStorage.removeItem(STORAGE_KEY);
          setIsLoading(false);
          return;
        }
        
        if (!isTokenExpired(storedToken)) {
          const userInfo = getUserFromToken(storedToken);
          if (userInfo && userInfo.email) {
            setToken(storedToken);
            setUser(userInfo);
          } else {
            console.warn('[GoogleAuth] Could not extract user info, clearing token');
            localStorage.removeItem(STORAGE_KEY);
          }
        } else {
          // Token expired, remove it
          console.log('[GoogleAuth] Token expired, clearing');
          localStorage.removeItem(STORAGE_KEY);
        }
      }
    } catch (e) {
      console.error('[GoogleAuth] Error checking stored token, clearing all auth state:', e);
      // Clear all possible auth tokens on error
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem('auth_token');
      localStorage.removeItem('nicole_token');
    }
    
    setIsLoading(false);
  }, []);

  // Periodic token expiration check - try to silently refresh before expiry
  useEffect(() => {
    if (!token) return;
    
    let refreshAttempted = false;
    
    const attemptSilentRefresh = () => {
      if (!window.google || !isGsiLoaded) return;
      
      console.log('[GoogleAuth] Attempting silent token refresh...');
      
      // Try Google One Tap with auto_select for silent refresh
      try {
        // Cast to callback overload which isn't in our type definitions
        (window.google.accounts.id.prompt as (callback?: (notification: { 
          isNotDisplayed: () => boolean; 
          isSkippedMoment: () => boolean 
        }) => void) => void)((notification) => {
          if (notification.isNotDisplayed()) {
            console.log('[GoogleAuth] One Tap not displayed - may need manual refresh');
          } else if (notification.isSkippedMoment()) {
            console.log('[GoogleAuth] One Tap skipped');
          } else {
            console.log('[GoogleAuth] One Tap shown for refresh');
          }
        });
      } catch (e) {
        console.error('[GoogleAuth] Silent refresh error:', e);
      }
    };
    
    const checkTokenExpiry = () => {
      const minutes = getTokenExpiryMinutes(token);
      
      if (isTokenExpired(token)) {
        console.warn('[GoogleAuth] Token expired');
        
        // Don't immediately redirect - try one more refresh attempt
        if (!refreshAttempted && window.google && isGsiLoaded) {
          refreshAttempted = true;
          attemptSilentRefresh();
          // Give it 3 seconds, then check again
          setTimeout(() => {
            const currentToken = localStorage.getItem(STORAGE_KEY);
            if (!currentToken || isTokenExpired(currentToken)) {
              console.warn('[GoogleAuth] Still expired after refresh attempt, redirecting');
              localStorage.removeItem(STORAGE_KEY);
              setToken(null);
              setUser(null);
              // Softer redirect without alert
              window.location.href = '/login?expired=true';
            }
          }, 3000);
        } else {
          localStorage.removeItem(STORAGE_KEY);
          setToken(null);
          setUser(null);
          window.location.href = '/login?expired=true';
        }
      } else if (isTokenExpiringSoon(token)) {
        console.log(`[GoogleAuth] Token expires in ${minutes} minutes, attempting refresh`);
        attemptSilentRefresh();
      } else if (minutes < 30) {
        // Also try refresh when less than 30 minutes remaining (more aggressive)
        console.log(`[GoogleAuth] Token has ${minutes} minutes left, preemptive refresh`);
        attemptSilentRefresh();
      }
    };
    
    // Check immediately
    checkTokenExpiry();
    
    // Check every 5 minutes (less frequent, less intrusive)
    const interval = setInterval(checkTokenExpiry, 5 * 60 * 1000);
    
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
    console.log('[GoogleAuth] Attempting to render button...', { isGsiLoaded, hasGoogle: !!window.google, clientId: clientId ? 'set' : 'missing' });
    
    if (!isGsiLoaded || !window.google) {
      console.warn('[GoogleAuth] Google not ready yet');
      return;
    }
    
    // Don't render if clientId is missing
    if (!clientId) {
      console.error('[GoogleAuth] Cannot render button: NEXT_PUBLIC_GOOGLE_CLIENT_ID is not set');
      return;
    }
    
    const element = document.getElementById(elementId);
    if (element) {
      try {
        // Clear any previous button content
        element.innerHTML = '';
        
        window.google.accounts.id.renderButton(element, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          text: 'signin_with',
          shape: 'rectangular',
          width: 300,
          click_listener: () => {
            console.log('[GoogleAuth] Button clicked');
          },
        });
        console.log('[GoogleAuth] Button rendered successfully');
      } catch (err) {
        console.error('[GoogleAuth] Failed to render button:', err);
      }
    } else {
      console.warn('[GoogleAuth] Element not found:', elementId);
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

