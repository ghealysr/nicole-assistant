'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { getStoredToken } from '@/lib/google_auth';

// Types
export interface ImageJob {
  id: number;
  user_id: number;
  original_prompt: string;
  enhanced_prompt?: string;
  model: string;
  width: number;
  height: number;
  style?: string;
  batch_count: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  total_cost?: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
  preset_id?: number;
}

export interface ImageVariant {
  id: number;
  job_id: number;
  variant_number: number;
  image_url?: string;
  thumbnail_url?: string;
  enhanced_prompt?: string;
  model_used: string;
  generation_time_ms?: number;
  cost?: number;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  is_favorite: boolean;
  user_rating?: number;
  error_message?: string;
  created_at: string;
}

export interface ImagePreset {
  id: number;
  name: string;
  description?: string;
  default_model: string;
  default_width: number;
  default_height: number;
  default_style?: string;
  prompt_suffix?: string;
  slash_command?: string;
  is_system: boolean;
}

export interface ImageModel {
  key: string;
  name: string;
  cost_per_image: number;
  max_width: number;
  max_height: number;
  supports_style: boolean;
  style_options?: string[];
}

export interface GenerationProgress {
  job_id: number;
  variant_index: number;
  total_variants: number;
  progress: number;
  status: 'enhancing_prompt' | 'generating' | 'uploading' | 'complete' | 'failed';
  error?: string;
  enhanced_prompt?: string;
  image_url?: string;
}

export interface CreateJobParams {
  prompt: string;
  model: string;
  width: number;
  height: number;
  style?: string;
  batch_count: number;
  enhance_prompt: boolean;
  preset_id?: number;
}

// API helper
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.nicole.alphawavetech.com';

async function fetchWithAuth<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getStoredToken();
  
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `Request failed: ${res.status}`);
  }

  return res.json();
}

/**
 * Hook for image generation operations
 */
export function useImageGeneration() {
  const [jobs, setJobs] = useState<ImageJob[]>([]);
  const [variants, setVariants] = useState<ImageVariant[]>([]);
  const [presets, setPresets] = useState<ImagePreset[]>([]);
  const [models, setModels] = useState<ImageModel[]>([]);
  const [progress, setProgress] = useState<GenerationProgress | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    const eventSource = eventSourceRef.current;
    const abortController = abortControllerRef.current;
    return () => {
      if (eventSource) {
        eventSource.close();
      }
      if (abortController) {
        abortController.abort();
      }
    };
  }, []);

  // Fetch jobs
  const fetchJobs = useCallback(async () => {
    try {
      const response = await fetchWithAuth<{ success: boolean; jobs: ImageJob[] }>('/images/jobs');
      setJobs(response.jobs || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch jobs');
    }
  }, []);

  // Fetch variants for a job
  const fetchVariants = useCallback(async (jobId: number) => {
    try {
      const response = await fetchWithAuth<{ success: boolean; variants: ImageVariant[] }>(`/images/jobs/${jobId}/variants`);
      const newVariants = response.variants || [];
      setVariants(prev => {
        const filtered = prev.filter(v => v.job_id !== jobId);
        return [...filtered, ...newVariants];
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch variants');
    }
  }, []);

  // Fetch presets
  const fetchPresets = useCallback(async () => {
    try {
      const response = await fetchWithAuth<{ success: boolean; presets: ImagePreset[] }>('/images/presets');
      setPresets(response.presets || []);
    } catch (err) {
      console.error('Failed to fetch presets:', err);
      // Use default presets if API fails
      setPresets([
        { id: 1, name: 'Logo', description: 'Square logo designs', default_model: 'recraft', default_width: 1024, default_height: 1024, default_style: 'vector_illustration', slash_command: '/logo', is_system: true },
        { id: 2, name: 'Hero Banner', description: 'Wide hero images', default_model: 'recraft', default_width: 1920, default_height: 1080, slash_command: '/hero', is_system: true },
        { id: 3, name: 'Social Post', description: 'Square social posts', default_model: 'recraft', default_width: 1080, default_height: 1080, slash_command: '/ig', is_system: true },
        { id: 4, name: 'Poster', description: 'Portrait posters', default_model: 'recraft', default_width: 1024, default_height: 1365, slash_command: '/poster', is_system: true },
        { id: 5, name: 'Thumbnail', description: 'YouTube thumbnails', default_model: 'recraft', default_width: 1280, default_height: 720, slash_command: '/thumb', is_system: true },
      ]);
    }
  }, []);

  // Fetch models
  const fetchModels = useCallback(async () => {
    try {
      const response = await fetchWithAuth<{ success: boolean; models: ImageModel[] }>('/images/models');
      setModels(response.models || []);
    } catch (err) {
      console.error('Failed to fetch models:', err);
      // Use default models if API fails
      setModels([
        { key: 'recraft', name: 'Recraft V3', cost_per_image: 0.04, max_width: 2048, max_height: 2048, supports_style: true, style_options: ['realistic_image', 'digital_illustration', 'vector_illustration', 'icon'] },
        { key: 'flux_pro', name: 'FLUX Pro', cost_per_image: 0.055, max_width: 1440, max_height: 1440, supports_style: false },
        { key: 'flux_schnell', name: 'FLUX Schnell', cost_per_image: 0.003, max_width: 1440, max_height: 1440, supports_style: false },
        { key: 'ideogram', name: 'Ideogram V2', cost_per_image: 0.08, max_width: 2048, max_height: 2048, supports_style: true, style_options: ['Auto', 'Realistic', 'Design', 'Render 3D', 'Anime'] },
      ]);
    }
  }, []);

  // Create a new job
  const createJob = useCallback(async (params: CreateJobParams): Promise<ImageJob | null> => {
    try {
      setError(null);
      const response = await fetchWithAuth<{ success: boolean; job: ImageJob }>('/images/jobs', {
        method: 'POST',
        body: JSON.stringify(params),
      });
      const job = response.job;
      if (job) {
        setJobs(prev => [job, ...prev]);
      }
      return job || null;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create job');
      return null;
    }
  }, []);

  // Start generation with SSE streaming
  const startGeneration = useCallback((jobId: number) => {
    setIsGenerating(true);
    setProgress(null);
    setError(null);

    const token = getStoredToken();
    
    // Using fetch for SSE since EventSource doesn't support custom headers
    abortControllerRef.current = new AbortController();
    
    fetch(`${API_BASE}/images/generate/stream?job_id=${jobId}`, {
      method: 'POST',
      headers: {
        'Accept': 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      signal: abortControllerRef.current.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          // Try to get error message from response body
          let errorMsg = `Generation failed: ${response.status}`;
          try {
            const errorBody = await response.json();
            errorMsg = errorBody.detail || errorBody.error || errorBody.message || errorMsg;
            if (typeof errorMsg === 'object') {
              errorMsg = JSON.stringify(errorMsg);
            }
          } catch {
            // Ignore JSON parse errors
          }
          throw new Error(errorMsg);
        }
        
        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body');
        }
        
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          
          buffer += decoder.decode(value, { stream: true });
          
          // Process complete SSE events
          const events = buffer.split('\n\n');
          buffer = events.pop() || '';
          
          for (const event of events) {
            if (!event.trim()) continue;
            
            const lines = event.split('\n');
            let eventType = '';
            let data = '';
            
            for (const line of lines) {
              if (line.startsWith('event:')) {
                eventType = line.slice(6).trim();
              } else if (line.startsWith('data:')) {
                data = line.slice(5).trim();
              }
            }
            
            if (data) {
              try {
                const parsed = JSON.parse(data);
                
                if (eventType === 'progress' || eventType === 'enhancing' || eventType === 'generating') {
                  setProgress(parsed);
                } else if (eventType === 'variant_complete') {
                  // Add completed variant
                  setVariants(prev => {
                    const existing = prev.findIndex(v => v.id === parsed.id);
                    if (existing >= 0) {
                      const updated = [...prev];
                      updated[existing] = parsed;
                      return updated;
                    }
                    return [...prev, parsed];
                  });
                  setProgress(prev => prev ? { ...prev, progress: Math.round(((parsed.variant_number) / prev.total_variants) * 100) } : null);
                } else if (eventType === 'complete') {
                  setIsGenerating(false);
                  setProgress(null);
                  // Refresh job data
                  fetchJobs();
                } else if (eventType === 'error') {
                  const errorMsg = typeof parsed.error === 'string' 
                    ? parsed.error 
                    : (parsed.error?.message || parsed.message || JSON.stringify(parsed.error) || 'Generation failed');
                  setError(errorMsg);
                  setIsGenerating(false);
                  setProgress(null);
                }
              } catch (e) {
                console.error('Failed to parse SSE data:', e);
              }
            }
          }
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(err instanceof Error ? err.message : 'Generation failed');
          setIsGenerating(false);
        }
      });
  }, [fetchJobs]);

  // Cancel generation
  const cancelGeneration = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    setIsGenerating(false);
    setProgress(null);
  }, []);

  // Toggle favorite
  const toggleFavorite = useCallback(async (variantId: number) => {
    try {
      const response = await fetchWithAuth<{ success: boolean; is_favorite: boolean }>(`/images/variants/${variantId}/favorite`, {
        method: 'POST',
        body: JSON.stringify({ is_favorite: true }), // Toggle - backend will handle the actual toggle
      });
      setVariants(prev =>
        prev.map(v => (v.id === variantId ? { ...v, is_favorite: response.is_favorite } : v))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle favorite');
    }
  }, []);

  // Rate variant
  const rateVariant = useCallback(async (variantId: number, rating: number) => {
    try {
      await fetchWithAuth<void>(`/images/variants/${variantId}/rate`, {
        method: 'POST',
        body: JSON.stringify({ user_rating: rating }),
      });
      setVariants(prev =>
        prev.map(v => (v.id === variantId ? { ...v, user_rating: rating } : v))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rate variant');
    }
  }, []);

  return {
    // State
    jobs,
    variants,
    presets,
    models,
    progress,
    isGenerating,
    error,
    // Actions
    fetchJobs,
    fetchVariants,
    fetchPresets,
    fetchModels,
    createJob,
    startGeneration,
    cancelGeneration,
    toggleFavorite,
    rateVariant,
    setError,
  };
}

/**
 * Detect slash commands in chat input
 */
export function parseSlashCommand(input: string): { command: string; prompt: string } | null {
  const match = input.match(/^\/(\w+)\s+(.+)$/);
  if (!match) return null;
  
  const [, command, prompt] = match;
  const validCommands = ['logo', 'hero', 'poster', 'thumb', 'ig', 'image'];
  
  if (validCommands.includes(command.toLowerCase())) {
    return { command: command.toLowerCase(), prompt };
  }
  
  return null;
}

/**
 * Get preset for slash command
 */
export function getPresetForCommand(command: string, presets: ImagePreset[]): ImagePreset | undefined {
  const commandMap: Record<string, string> = {
    logo: '/logo',
    hero: '/hero',
    poster: '/poster',
    thumb: '/thumb',
    ig: '/ig',
    image: '/logo', // default
  };
  
  const slashCommand = commandMap[command];
  return presets.find(p => p.slash_command === slashCommand);
}

