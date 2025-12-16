/**
 * AlphaWave Utility Functions
 * 
 * Authentication and request utilities shared across the application.
 * Works with Nicole's existing auth system (JWT in localStorage).
 */

/**
 * Get authentication headers for API requests.
 * Retrieves JWT from localStorage and formats as Bearer token.
 */
export function getAuthHeaders(): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  // Check for auth token in localStorage (Nicole's auth system + Google OAuth)
  if (typeof window !== 'undefined') {
    const token =
      localStorage.getItem('nicole_token') ||
      localStorage.getItem('auth_token') ||
      localStorage.getItem('nicole_google_token'); // Google OAuth token
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  return headers;
}

/**
 * Get auth token directly
 */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('nicole_token') || localStorage.getItem('auth_token');
}

/**
 * Set auth token
 */
export function setAuthToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem('nicole_token', token);
}

/**
 * Clear auth token (logout)
 */
export function clearAuthToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('nicole_token');
  localStorage.removeItem('auth_token');
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return !!getAuthToken();
}

/**
 * Make an authenticated fetch request with error handling
 */
export async function authFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers = {
    ...getAuthHeaders(),
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle 401 - redirect to login
  if (response.status === 401) {
    clearAuthToken();
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    throw new Error('Authentication required');
  }

  return response;
}

/**
 * Parse API error response
 */
export async function parseApiError(response: Response): Promise<string> {
  try {
    const data = await response.json();
    return data.detail || data.message || data.error || 'An error occurred';
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

/**
 * Format API response with consistent error handling
 */
export async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorMessage = await parseApiError(response);
    throw new Error(errorMessage);
  }
  return response.json();
}

