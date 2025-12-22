/**
 * Frontend Configuration
 * 
 * QA NOTES:
 * - Uses NEXT_PUBLIC_ prefix for client-side env vars
 * - Provides defaults for development
 * - API_URL defaults to production API if not set
 */

// API Configuration
// Hardcoded for reliability - environment variables are baked at build time
// and can cause stale cache issues with Vercel
export const API_URL = 'https://api.nicole.alphawavetech.com';
export const API_VERSION = 'v1';

// Feature Flags
export const FEATURES = {
  voice: process.env.NEXT_PUBLIC_ENABLE_VOICE === 'true',
  imageGeneration: process.env.NEXT_PUBLIC_ENABLE_IMAGE_GEN === 'true',
  journal: process.env.NEXT_PUBLIC_ENABLE_JOURNAL !== 'false', // enabled by default
  sportsOracle: process.env.NEXT_PUBLIC_ENABLE_SPORTS !== 'false', // enabled by default
};

// API Endpoints
export const ENDPOINTS = {
  // Chat
  chat: {
    message: `${API_URL}/chat/message`,
    history: (conversationId: string) => `${API_URL}/chat/conversations/${conversationId}/messages`,
    conversations: `${API_URL}/chat/conversations`,
  },
  
  // Voice
  voice: {
    transcribe: `${API_URL}/voice/transcribe`,
    synthesize: `${API_URL}/voice/synthesize`,
  },
  
  // Journal
  journal: {
    entry: (date: string) => `${API_URL}/journal/entries/${date}`,
    entries: `${API_URL}/journal/entries`,
    patterns: `${API_URL}/journal/patterns`,
  },
  
  // Files
  files: {
    upload: `${API_URL}/files/upload`,
    get: (fileId: string) => `${API_URL}/files/${fileId}`,
  },
  
  // Memories
  memories: {
    search: `${API_URL}/memories/search`,
    stats: `${API_URL}/memories/stats`,
  },
  
  // Health
  health: {
    check: `${API_URL}/health/check`,
    detailed: `${API_URL}/health/detailed`,
  },
  
  // Dashboards
  dashboards: {
    list: `${API_URL}/dashboards`,
    get: (dashboardId: string) => `${API_URL}/dashboards/${dashboardId}`,
  },
  
  // Sports Oracle
  sports: {
    predictions: `${API_URL}/sports-oracle/predictions`,
    stats: `${API_URL}/sports-oracle/stats`,
  },
};

// Request Configuration
export const REQUEST_CONFIG = {
  timeout: 120000, // 120 seconds - longer for AI responses
  retries: 2,
  retryDelay: 1000, // 1 second between retries
};

// Streaming Configuration for SSE
export const STREAMING_CONFIG = {
  reconnectAttempts: 3,
  reconnectDelay: 2000, // 2 seconds
};

/**
 * Get the full API URL for a path
 */
export function getApiUrl(path: string): string {
  // Remove leading slash if present
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;
  return `${API_URL}/${cleanPath}`;
}

/**
 * Check if we're in development mode
 */
export function isDevelopment(): boolean {
  return process.env.NODE_ENV === 'development';
}

/**
 * Check if we're running on the server
 */
export function isServer(): boolean {
  return typeof window === 'undefined';
}

