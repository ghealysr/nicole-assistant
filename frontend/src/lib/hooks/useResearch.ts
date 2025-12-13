/**
 * useResearch Hook - Gemini 3 Pro Deep Research Integration
 * 
 * Manages research state, API calls, and streaming updates for:
 * - General research queries
 * - Vibe project inspiration search
 * - Competitor analysis
 * 
 * @author Nicole V7 Architecture
 */

import { useState, useCallback, useRef } from 'react';
import { API_URL } from '@/lib/alphawave_config';

// ============================================================================
// TYPES
// ============================================================================

export type ResearchType = 'general' | 'vibe_inspiration' | 'competitor' | 'technical';

export type ResearchStatus = 'idle' | 'pending' | 'researching' | 'synthesizing' | 'complete' | 'failed';

export interface ResearchFinding {
  content: string;
  source_url?: string;
  source_title?: string;
  relevance_score?: number;
}

export interface ResearchSource {
  url: string;
  title: string;
  relevance_score?: number;
}

export interface ResearchMetadata {
  cost_usd: number;
  elapsed_seconds: number;
  model: string;
  input_tokens?: number;
  output_tokens?: number;
}

export interface ResearchResponse {
  request_id: number;
  query: string;
  research_type: ResearchType;
  executive_summary: string;
  findings: ResearchFinding[];
  sources: ResearchSource[];
  recommendations: string[];
  nicole_synthesis: string;
  metadata: ResearchMetadata;
  created_at?: string;
  completed_at?: string;
}

export interface InspirationImage {
  id: string;
  url: string;
  screenshot_url: string;
  source_site: string;
  design_elements: {
    colors: string[];
    typography_style: string;
    layout_pattern: string;
    notable_features: string[];
  };
  relevance_notes: string;
}

export interface ImageFeedback {
  imageId: string;
  liked: boolean;
  likedElements: string[];
  dislikedElements: string[];
  comments: string;
}

export interface VibeInspirationResponse {
  project_id: number;
  query: string;
  inspirations: InspirationImage[];
  design_patterns: string[];
  recommendations: string[];
  sources: ResearchSource[];
  metadata: ResearchMetadata;
}

export interface UseResearchReturn {
  // State
  research: ResearchResponse | null;
  vibeInspirations: VibeInspirationResponse | null;
  status: ResearchStatus;
  statusMessage: string;
  error: string | null;
  progress: number;
  
  // Actions
  executeResearch: (query: string, type?: ResearchType, context?: object) => Promise<ResearchResponse | null>;
  executeVibeInspiration: (
    query: string,
    projectId: number,
    brief?: object,
    previousFeedback?: ImageFeedback[]
  ) => Promise<VibeInspirationResponse | null>;
  analyzeCompetitor: (
    competitorUrl: string,
    projectId: number,
    analysisFocus?: string[]
  ) => Promise<ResearchResponse | null>;
  clearResearch: () => void;
  cancelResearch: () => void;
}

// ============================================================================
// STATUS MESSAGES
// ============================================================================

const STATUS_MESSAGES: Record<ResearchStatus, string> = {
  idle: '',
  pending: 'Starting research...',
  researching: 'Searching across multiple sources...',
  synthesizing: 'Analyzing findings and preparing report...',
  complete: 'Research complete!',
  failed: 'Research failed. Please try again.',
};

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export function useResearch(): UseResearchReturn {
  const [research, setResearch] = useState<ResearchResponse | null>(null);
  const [vibeInspirations, setVibeInspirations] = useState<VibeInspirationResponse | null>(null);
  const [status, setStatus] = useState<ResearchStatus>('idle');
  const [statusMessage, setStatusMessage] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Get auth token from localStorage
   */
  const getAuthToken = useCallback((): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('token');
  }, []);

  /**
   * Make authenticated API request
   */
  const apiRequest = useCallback(async <T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> => {
    const token = getAuthToken();
    
    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        ...options.headers,
      },
      signal: abortControllerRef.current?.signal,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }, [getAuthToken]);

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
    setStatusMessage(STATUS_MESSAGES.pending);
    setProgress(10);
    setError(null);
    setResearch(null);

    try {
      // Simulate progress during request
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 80) {
            clearInterval(progressInterval);
            return 80;
          }
          const increment = prev < 30 ? 5 : prev < 60 ? 3 : 1;
          const newProgress = prev + increment;
          
          // Update status based on progress
          if (newProgress > 20 && newProgress <= 60) {
            setStatus('researching');
            setStatusMessage(STATUS_MESSAGES.researching);
          } else if (newProgress > 60) {
            setStatus('synthesizing');
            setStatusMessage(STATUS_MESSAGES.synthesizing);
          }
          
          return newProgress;
        });
      }, 500);

      const result = await apiRequest<{ data: ResearchResponse }>('/research/execute', {
        method: 'POST',
        body: JSON.stringify({
          query,
          research_type: type,
          context,
        }),
      });

      clearInterval(progressInterval);
      setProgress(100);
      setStatus('complete');
      setStatusMessage(STATUS_MESSAGES.complete);
      setResearch(result.data);
      
      return result.data;

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return null;
      }
      
      const message = err instanceof Error ? err.message : 'Research failed';
      setError(message);
      setStatus('failed');
      setStatusMessage(message);
      setProgress(0);
      return null;
    }
  }, [apiRequest]);

  /**
   * Execute Vibe inspiration search
   */
  const executeVibeInspiration = useCallback(async (
    query: string,
    projectId: number,
    brief?: object,
    previousFeedback?: ImageFeedback[]
  ): Promise<VibeInspirationResponse | null> => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    setStatus('pending');
    setStatusMessage('Searching for design inspiration...');
    setProgress(10);
    setError(null);
    setVibeInspirations(null);

    try {
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 3, 80));
      }, 400);

      setStatus('researching');
      setStatusMessage('Analyzing design patterns...');

      const result = await apiRequest<VibeInspirationResponse>(
        `/research/vibe/${projectId}/inspiration`,
        {
          method: 'POST',
          body: JSON.stringify({
            query,
            project_brief: brief,
            previous_feedback: previousFeedback,
          }),
        }
      );

      clearInterval(progressInterval);
      setProgress(100);
      setStatus('complete');
      setStatusMessage(`Found ${result.inspirations?.length || 0} design inspirations`);
      setVibeInspirations(result);
      
      return result;

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return null;
      }
      
      const message = err instanceof Error ? err.message : 'Inspiration search failed';
      setError(message);
      setStatus('failed');
      setStatusMessage(message);
      setProgress(0);
      return null;
    }
  }, [apiRequest]);

  /**
   * Analyze competitor
   */
  const analyzeCompetitor = useCallback(async (
    competitorUrl: string,
    projectId: number,
    analysisFocus?: string[]
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

    try {
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 80) return 80;
          if (prev > 40) {
            setStatus('synthesizing');
            setStatusMessage('Evaluating strengths and weaknesses...');
          }
          return prev + 4;
        });
      }, 500);

      setStatus('researching');
      setStatusMessage('Scanning website and features...');

      const params = new URLSearchParams({ competitor_url: competitorUrl });
      if (analysisFocus?.length) {
        params.append('analysis_focus', JSON.stringify(analysisFocus));
      }

      const result = await apiRequest<{ analysis: ResearchResponse }>(
        `/research/vibe/${projectId}/competitor?${params}`,
        { method: 'POST' }
      );

      clearInterval(progressInterval);
      setProgress(100);
      setStatus('complete');
      setStatusMessage('Competitor analysis complete');
      
      // Transform to ResearchResponse format
      const transformed: ResearchResponse = {
        request_id: 0,
        query: `Competitor: ${competitorUrl}`,
        research_type: 'competitor',
        executive_summary: result.analysis?.executive_summary || '',
        findings: result.analysis?.findings || [],
        sources: result.analysis?.sources || [],
        recommendations: result.analysis?.recommendations || [],
        nicole_synthesis: result.analysis?.nicole_synthesis || '',
        metadata: result.analysis?.metadata || { cost_usd: 0, elapsed_seconds: 0, model: '' },
      };
      
      setResearch(transformed);
      return transformed;

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        return null;
      }
      
      const message = err instanceof Error ? err.message : 'Competitor analysis failed';
      setError(message);
      setStatus('failed');
      setStatusMessage(message);
      setProgress(0);
      return null;
    }
  }, [apiRequest]);

  /**
   * Clear research state
   */
  const clearResearch = useCallback(() => {
    setResearch(null);
    setVibeInspirations(null);
    setStatus('idle');
    setStatusMessage('');
    setError(null);
    setProgress(0);
  }, []);

  /**
   * Cancel ongoing research
   */
  const cancelResearch = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setStatus('idle');
    setStatusMessage('Research cancelled');
    setProgress(0);
  }, []);

  return {
    research,
    vibeInspirations,
    status,
    statusMessage,
    error,
    progress,
    executeResearch,
    executeVibeInspiration,
    analyzeCompetitor,
    clearResearch,
    cancelResearch,
  };
}

