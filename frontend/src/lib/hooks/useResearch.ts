'use client';

/**
 * useResearch - Hook for Gemini Deep Research Integration
 * 
 * Provides:
 * - Deep research execution with Google Search grounding
 * - Vibe inspiration search for design research
 * - Competitor website analysis
 * - Real-time progress tracking
 * - Research history
 * 
 * Uses Gemini 3 Pro with search grounding (FREE until Jan 2026)
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { API_URL as CONFIG_API_URL } from '@/lib/alphawave_config';

// API base URL
const API_URL = CONFIG_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Research types
export type ResearchType = 'general' | 'vibe_inspiration' | 'competitor' | 'technical';

// Research status
export type ResearchStatus = 'idle' | 'pending' | 'researching' | 'synthesizing' | 'complete' | 'failed' | 'cancelled';

// Research finding
export interface ResearchFinding {
  content: string;
  source_url?: string;
  source_title?: string;
}

// Research source
export interface ResearchSource {
  url: string;
  title: string;
}

// Full research response
export interface ResearchResponse {
  request_id: number;
  query: string;
  research_type: ResearchType;
  executive_summary: string;
  findings: ResearchFinding[];
  sources: ResearchSource[];
  recommendations: string[];
  nicole_synthesis: string;
  metadata: {
    model: string;
    input_tokens: number;
    output_tokens: number;
    cost_usd: number;
    elapsed_seconds: number;
    timestamp: string;
  };
  project_id?: number;
  competitor_url?: string;
}

// Vibe inspiration image - matches InspirationGallery component expectations
export interface InspirationImage {
  id?: string;
  url: string;
  screenshot_url?: string;
  thumbnail_url?: string;
  title?: string;
  description?: string;
  source_url?: string;
  source_site?: string;
  color_palette?: string[];
  design_notes?: string;
  relevance_notes?: string;
  design_elements?: {
    layout_pattern?: string;
    colors?: string[];
    typography?: string[];
    typography_style?: string;
    style_tags?: string[];
    notable_features?: string[];
  };
}

// Vibe inspiration response
export interface VibeInspirationResponse {
  project_id: number;
  query: string;
  inspirations: InspirationImage[];
  design_patterns: string[];
  recommendations: string[];
  sources: ResearchSource[];
  metadata: {
    model: string;
    cost_usd: number;
    elapsed_seconds: number;
  };
}

// Image feedback
export interface ImageFeedback {
  image_url: string;
  liked: boolean;
  notes?: string;
}

// Hook configuration
interface UseResearchConfig {
  authToken?: string;
  onError?: (error: string) => void;
}

// Hook return type
interface UseResearchReturn {
  // State
  research: ResearchResponse | null;
  vibeInspirations: VibeInspirationResponse | null;
  status: ResearchStatus;
  statusMessage: string;
  progress: number;
  error: string | null;
  history: { request_id: number; query: string; type: ResearchType; created_at: string }[];
  
  // Actions
  executeResearch: (query: string, type?: ResearchType, context?: object) => Promise<ResearchResponse | null>;
  executeVibeInspiration: (projectId: number, query: string, brief?: object, feedback?: ImageFeedback[]) => Promise<VibeInspirationResponse | null>;
  analyzeCompetitor: (projectId: number, url: string, focus?: string[]) => Promise<ResearchResponse | null>;
  getResearch: (requestId: number) => Promise<ResearchResponse | null>;
  loadHistory: () => Promise<void>;
  clearResearch: () => void;
  cancelResearch: () => void;
}

/**
 * Hook for Gemini Deep Research
 */
export function useResearch(config: UseResearchConfig = {}): UseResearchReturn {
  const { authToken, onError } = config;
  
  // State
  const [research, setResearch] = useState<ResearchResponse | null>(null);
  const [vibeInspirations, setVibeInspirations] = useState<VibeInspirationResponse | null>(null);
  const [status, setStatus] = useState<ResearchStatus>('idle');
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<{ request_id: number; query: string; type: ResearchType; created_at: string }[]>([]);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * API Response shape from backend
   */
  interface APIResponseWrapper<T = unknown> {
    success: boolean;
    data?: T;
    error?: string;
  }

  /**
   * Make authenticated API request with wrapped response handling
   */
  const apiRequest = useCallback(async <T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<{ success: boolean; data?: T; error?: string }> => {
    if (!authToken) {
      return { success: false, error: 'Authorization header required' };
    }
    
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
        ...options.headers,
      },
      signal: abortControllerRef.current?.signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Request failed' }));
      return { success: false, error: errorData.detail || errorData.error || `HTTP ${response.status}` };
    }

    const result: APIResponseWrapper<T> = await response.json();
    return result;
  }, [authToken]);

  /**
   * Execute general research
   */
  const executeResearch = useCallback(async (
    query: string,
    type: ResearchType = 'general',
    context?: object
  ): Promise<ResearchResponse | null> => {
    // Cancel any existing request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setStatus('pending');
    setStatusMessage('Preparing research request...');
    setProgress(10);
    setError(null);
    setResearch(null);
    setVibeInspirations(null);

    try {
      // Update status
      setStatus('researching');
      setStatusMessage('Searching with Gemini + Google...');
      setProgress(30);

      const result = await apiRequest<{ data: ResearchResponse }>('/research/execute', {
        method: 'POST',
        body: JSON.stringify({
          query,
          research_type: type,
          context,
        }),
      });

      if (!result.success || !result.data) {
        throw new Error(result.error || 'Research failed');
      }

      // Handle nested data structure from backend
      const researchData = result.data.data || result.data as unknown as ResearchResponse;

      setStatus('synthesizing');
      setStatusMessage('Nicole is analyzing findings...');
      setProgress(80);

      // Simulate small delay for UX
      await new Promise(resolve => setTimeout(resolve, 500));

      setResearch(researchData);
      setStatus('complete');
      setStatusMessage('Research complete!');
      setProgress(100);

      return researchData;
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        setStatus('cancelled');
        setStatusMessage('Research cancelled');
        return null;
      }

      const errorMessage = (err as Error).message || 'Unknown error';
      setError(errorMessage);
      setStatus('failed');
      setStatusMessage('Research failed');
      onError?.(errorMessage);
      return null;
    }
  }, [apiRequest, onError]);

  /**
   * Execute Vibe inspiration search
   */
  const executeVibeInspiration = useCallback(async (
    projectId: number,
    query: string,
    brief?: object,
    feedback?: ImageFeedback[]
  ): Promise<VibeInspirationResponse | null> => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setStatus('pending');
    setStatusMessage('Searching for design inspiration...');
    setProgress(10);
    setError(null);
    setResearch(null);
    setVibeInspirations(null);

    try {
      setStatus('researching');
      setStatusMessage('Finding visual references...');
      setProgress(40);

      const result = await apiRequest<{ data: VibeInspirationResponse }>(`/research/vibe/${projectId}/inspiration`, {
        method: 'POST',
        body: JSON.stringify({
          query,
          project_brief: brief,
          previous_feedback: feedback,
        }),
      });

      if (!result.success || !result.data) {
        throw new Error(result.error || 'Inspiration search failed');
      }

      const inspirationData = result.data.data || result.data as unknown as VibeInspirationResponse;

      setVibeInspirations(inspirationData);
      setStatus('complete');
      setStatusMessage('Inspiration found!');
      setProgress(100);

      return inspirationData;
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        setStatus('cancelled');
        return null;
      }

      const errorMessage = (err as Error).message || 'Inspiration search failed';
      setError(errorMessage);
      setStatus('failed');
      setStatusMessage('Failed');
      onError?.(errorMessage);
      return null;
    }
  }, [apiRequest, onError]);

  /**
   * Analyze competitor website
   */
  const analyzeCompetitor = useCallback(async (
    projectId: number,
    url: string,
    focus?: string[]
  ): Promise<ResearchResponse | null> => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setStatus('pending');
    setStatusMessage('Analyzing competitor...');
    setProgress(10);
    setError(null);
    setResearch(null);
    setVibeInspirations(null);

    try {
      setStatus('researching');
      setStatusMessage(`Analyzing ${new URL(url).hostname}...`);
      setProgress(30);

      const result = await apiRequest<{ data: ResearchResponse }>(`/research/vibe/${projectId}/competitor`, {
        method: 'POST',
        body: JSON.stringify({
          competitor_url: url,
          analysis_focus: focus,
        }),
      });

      if (!result.success || !result.data) {
        throw new Error(result.error || 'Competitor analysis failed');
      }

      const competitorData = result.data.data || result.data as unknown as ResearchResponse;

      setResearch(competitorData);
      setStatus('complete');
      setStatusMessage('Analysis complete!');
      setProgress(100);

      return competitorData;
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        setStatus('cancelled');
        return null;
      }

      const errorMessage = (err as Error).message || 'Analysis failed';
      setError(errorMessage);
      setStatus('failed');
      setStatusMessage('Failed');
      onError?.(errorMessage);
      return null;
    }
  }, [apiRequest, onError]);

  /**
   * Get research by ID
   */
  const getResearch = useCallback(async (requestId: number): Promise<ResearchResponse | null> => {
    try {
      const result = await apiRequest<ResearchResponse>(`/research/${requestId}`, {
        method: 'GET',
      });

      if (!result.success || !result.data) {
        throw new Error(result.error || 'Failed to fetch research');
      }

      return result.data;
    } catch (err) {
      const errorMessage = (err as Error).message || 'Failed to fetch research';
      onError?.(errorMessage);
      return null;
    }
  }, [apiRequest, onError]);

  /**
   * Load research history
   */
  const loadHistory = useCallback(async (): Promise<void> => {
    try {
      const result = await apiRequest<{ request_id: number; query: string; research_type: ResearchType; created_at: string }[]>('/research/history', {
        method: 'GET',
      });

      if (result.success && result.data) {
        setHistory(result.data.map(h => ({
          ...h,
          type: h.research_type,
        })));
      }
    } catch (err) {
      console.error('Failed to load research history:', err);
    }
  }, [apiRequest]);

  /**
   * Clear current research
   */
  const clearResearch = useCallback(() => {
    setResearch(null);
    setVibeInspirations(null);
    setStatus('idle');
    setStatusMessage('');
    setProgress(0);
    setError(null);
  }, []);

  /**
   * Cancel ongoing research
   */
  const cancelResearch = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setStatus('cancelled');
    setStatusMessage('Research cancelled');
  }, []);

  // Load history when token changes
  useEffect(() => {
    if (authToken) {
      loadHistory();
    }
  }, [authToken, loadHistory]);

  return {
    // State
    research,
    vibeInspirations,
    status,
    statusMessage,
    progress,
    error,
    history,
    
    // Actions
    executeResearch,
    executeVibeInspiration,
    analyzeCompetitor,
    getResearch,
    loadHistory,
    clearResearch,
    cancelResearch,
  };
}

export default useResearch;
