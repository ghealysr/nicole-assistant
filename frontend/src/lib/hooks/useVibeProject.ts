/**
 * useVibeProject - React hooks for Vibe project management
 * 
 * Production-grade implementation with:
 * - Type-safe operations with proper error handling
 * - Operation-specific loading states
 * - Memoized callbacks to prevent stale closures
 * - Debounced actions for rapid inputs
 * - Consistent API response handling
 * 
 * Version: 2.0.0
 */

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { getStoredToken } from '@/lib/google_auth';
import { API_URL } from '@/lib/alphawave_config';

// ============================================================================
// TYPES
// ============================================================================

export type ProjectType = 'website' | 'chatbot' | 'assistant' | 'integration';

export type ProjectStatus = 
  | 'intake' 
  | 'planning' 
  | 'building' 
  | 'qa' 
  | 'review' 
  | 'approved' 
  | 'deploying' 
  | 'deployed' 
  | 'delivered'
  | 'archived';

export interface VibeProject {
  project_id: number;
  name: string;
  project_type: ProjectType;
  client_name?: string;
  client_email?: string;
  status: ProjectStatus;
  brief?: Record<string, unknown>;
  architecture?: Record<string, unknown>;
  config?: Record<string, unknown>;
  preview_url?: string;
  production_url?: string;
  github_repo?: string;
  estimated_price?: number;
  api_cost?: number;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface VibeAgent {
  id: string;
  name: string;
  icon: string;
  status: 'idle' | 'working' | 'complete' | 'error';
  progress: number;
  task: string;
}

export interface VibeWorkflowStep {
  id: number;
  name: string;
  desc: string;
  status: 'pending' | 'active' | 'complete';
}

export interface VibeFile {
  file_id: number;
  file_path: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface VibeFileTreeItem {
  name: string;
  type: string;
  path?: string;
  children?: VibeFileTreeItem[];
}

export interface VibeLesson {
  lesson_id: number;
  project_type: string;
  lesson_category: string;
  issue: string;
  solution: string;
  impact: string;
  times_applied: number;
}

export interface VibeActivity {
  activity_id: number;
  project_id: number;
  activity_type: string;
  description: string;
  user_id?: number;
  agent_name?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export type ActivityType = 
  | 'project_created'
  | 'intake_message'
  | 'brief_extracted'
  | 'architecture_generated'
  | 'build_started'
  | 'build_completed'
  | 'qa_passed'
  | 'qa_failed'
  | 'review_approved'
  | 'review_rejected'
  | 'manually_approved'
  | 'deployment_started'
  | 'deployment_completed'
  | 'status_changed'
  | 'file_updated'
  | 'error';

// API Response types
interface APIResponse<T = Record<string, unknown>> {
  success: boolean;
  data?: T;
  error?: string;
  meta?: {
    total?: number;
    limit?: number;
    offset?: number;
    has_more?: boolean;
    api_cost?: number;
    count?: number;
  };
}

interface IntakeData {
  response: string;
  brief?: Record<string, unknown>;
  status: ProjectStatus;
  brief_complete: boolean;
}

interface BuildData {
  status: ProjectStatus;
  files_generated?: string[];
  file_count?: number;
  preview_url?: string;
  passed?: boolean;
  issues?: Array<{ severity: string; file: string; message: string }>;
  suggestions?: string[];
  score?: number;
  approved?: boolean;
  recommendation?: string;
  needs_rebuild?: boolean;
}

// Operation states
type OperationName = 'intake' | 'planning' | 'build' | 'qa' | 'review' | 'approve' | 'deploy';

interface OperationState {
  loading: boolean;
  error: string | null;
}

// Pipeline error surface for UI
export interface PipelineError {
  phase: OperationName | 'planning' | 'build' | 'qa' | 'review' | 'pipeline';
  message: string;
  raw_preview?: string;
}

// ============================================================================
// USER-FRIENDLY ERROR MESSAGES
// ============================================================================

/**
 * Convert technical error messages to user-friendly messages
 */
function getFriendlyErrorMessage(error: string, operation?: OperationName): string {
  const lowercaseError = error.toLowerCase();
  
  // Authentication errors
  if (lowercaseError.includes('not authenticated') || lowercaseError.includes('401')) {
    return 'Please sign in to continue.';
  }
  if (lowercaseError.includes('forbidden') || lowercaseError.includes('403')) {
    return "You don't have permission to perform this action.";
  }
  
  // Network errors
  if (lowercaseError.includes('failed to fetch') || lowercaseError.includes('network')) {
    return 'Unable to connect to the server. Please check your internet connection.';
  }
  if (lowercaseError.includes('timeout')) {
    return 'The request took too long. Please try again.';
  }
  
  // Status transition errors
  if (lowercaseError.includes('status') && lowercaseError.includes('requires')) {
    return 'Cannot perform this action in the current project state. Please complete the previous step first.';
  }
  if (lowercaseError.includes('invalid status')) {
    return 'The project is in an unexpected state. Try refreshing the page.';
  }
  
  // Project errors
  if (lowercaseError.includes('project not found')) {
    return 'This project no longer exists or you may not have access to it.';
  }
  if (lowercaseError.includes('no architecture') || lowercaseError.includes('run planning first')) {
    return 'Please complete the planning phase before building.';
  }
  if (lowercaseError.includes('no files') || lowercaseError.includes('no code')) {
    return 'No code files were generated. Please try running the build again.';
  }
  
  // AI/Claude errors  
  if (lowercaseError.includes('claude') || lowercaseError.includes('anthropic')) {
    return 'The AI service encountered an issue. Please try again in a moment.';
  }
  if (lowercaseError.includes('rate limit')) {
    return 'Too many requests. Please wait a moment before trying again.';
  }
  
  // Parse/validation errors
  if (lowercaseError.includes('parse') || lowercaseError.includes('invalid json')) {
    return 'There was an issue processing the response. Please try again.';
  }
  
  // Operation-specific messages
  if (operation) {
    const operationMessages: Record<OperationName, string> = {
      intake: 'Unable to process your message. Please try rephrasing.',
      planning: 'Planning failed. Please ensure the brief is complete.',
      build: 'Build failed. Please check the architecture and try again.',
      qa: 'Quality check failed. Please try running QA again.',
      review: 'Review failed. Please try again.',
      approve: 'Approval failed. Please try again.',
      deploy: 'Deployment failed. Please try again.',
    };
    return operationMessages[operation];
  }
  
  // Generic fallback - but cleaner than raw error
  if (error.length > 100) {
    return 'An unexpected error occurred. Please try again.';
  }
  
  return error;
}

// ============================================================================
// API CLIENT
// ============================================================================

class VibeAPIClient {
  private baseUrl: string;
  
  constructor() {
    this.baseUrl = `${API_URL}/vibe`;
  }
  
  private getHeaders(): HeadersInit {
    const token = getStoredToken();
    if (!token) {
      throw new Error('Not authenticated');
    }
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
  }
  
  async request<T>(
    endpoint: string,
    method: 'GET' | 'POST' | 'PATCH' | 'DELETE' = 'GET',
    body?: Record<string, unknown>,
    signal?: AbortSignal
  ): Promise<APIResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      method,
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      // Handle FastAPI validation errors (detail is array of {type, loc, msg, input})
      let errorMessage: string;
      if (Array.isArray(data.detail)) {
        // Extract messages from validation errors
        errorMessage = data.detail
          .map((e: { msg?: string }) => e.msg || 'Validation error')
          .join('; ');
      } else if (typeof data.detail === 'object' && data.detail !== null) {
        // Handle object-style errors
        errorMessage = data.detail.msg || data.detail.message || JSON.stringify(data.detail);
      } else if (typeof data.detail === 'string') {
        errorMessage = data.detail;
      } else if (typeof data.error === 'string') {
        errorMessage = data.error;
      } else if (typeof data.message === 'string') {
        errorMessage = data.message;
      } else {
        errorMessage = `Request failed with status ${response.status}`;
      }
      
      return {
        success: false,
        error: errorMessage,
      };
    }
    
    return data as APIResponse<T>;
  }
}

const apiClient = new VibeAPIClient();

const DEFAULT_API_BUDGET = 5; // dollars per project session

// ============================================================================
// HOOK: useVibeProjects (List)
// ============================================================================

export function useVibeProjects() {
  const [projects, setProjects] = useState<VibeProject[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pagination, setPagination] = useState({
    total: 0,
    limit: 50,
    offset: 0,
    hasMore: false,
  });

  const fetchProjects = useCallback(async (
    status?: ProjectStatus,
    limit = 50,
    offset = 0
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      let params = `?limit=${limit}&offset=${offset}`;
      if (status) params += `&status=${status}`;
      
      const response = await apiClient.request<{ projects: VibeProject[] }>(
        `/projects${params}`
      );
      
      if (!response.success) {
        setError(response.error || 'Failed to fetch projects');
        return;
      }
      
      setProjects(response.data?.projects || []);
      
      if (response.meta) {
        setPagination({
          total: response.meta.total || 0,
          limit: response.meta.limit || limit,
          offset: response.meta.offset || offset,
          hasMore: response.meta.has_more || false,
        });
      }
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : 'Failed to fetch projects';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage);
      setError(friendlyMessage);
      console.error('[useVibeProjects] Fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const createProject = useCallback(async (
    name: string,
    projectType: ProjectType,
    clientName?: string,
    clientEmail?: string
  ): Promise<VibeProject | null> => {
    setLoading(true);
    setError(null);
    
    try {
      // Build request body, omitting empty optional fields
      const body: Record<string, string> = {
        name: name.trim(),
        project_type: projectType,
      };
      if (clientName && clientName.trim()) {
        body.client_name = clientName.trim();
      }
      if (clientEmail && clientEmail.trim()) {
        body.client_email = clientEmail.trim();
      }
      
      const response = await apiClient.request<{ project: VibeProject }>(
        '/projects',
        'POST',
        body
      );
      
      if (!response.success || !response.data?.project) {
        setError(response.error || 'Failed to create project');
        return null;
      }
      
      const newProject = response.data.project;
      setProjects(prev => [newProject, ...prev]);
      
      return newProject;
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : 'Failed to create project';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage);
      setError(friendlyMessage);
      console.error('[useVibeProjects] Create error:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteProject = useCallback(async (projectId: number): Promise<boolean> => {
    try {
      const response = await apiClient.request(`/projects/${projectId}`, 'DELETE');
      
      if (!response.success) {
        setError(response.error || 'Failed to delete project');
        return false;
      }
      
      setProjects(prev => prev.filter(p => p.project_id !== projectId));
      return true;
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : 'Failed to delete project';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage);
      setError(friendlyMessage);
      console.error('[useVibeProjects] Delete error:', err);
      return false;
    }
  }, []);

  return {
    projects,
    loading,
    error,
    pagination,
    fetchProjects,
    createProject,
    deleteProject,
    clearError: useCallback(() => setError(null), []),
  };
}

// ============================================================================
// HOOK: useVibeProject (Single Project)
// ============================================================================

export function useVibeProject(projectId?: number) {
  // Core state
  const [project, setProject] = useState<VibeProject | null>(null);
  const [agents, setAgents] = useState<VibeAgent[]>([]);
  const [workflow, setWorkflow] = useState<VibeWorkflowStep[]>([]);
  const [files, setFiles] = useState<VibeFile[]>([]);
  const [fileTree, setFileTree] = useState<VibeFileTreeItem[]>([]);
  const [intakeHistory, setIntakeHistory] = useState<Array<{ role: string; content: string }>>([]);
  const [activities, setActivities] = useState<VibeActivity[]>([]);
  const [pipelineError, setPipelineError] = useState<PipelineError | null>(null);
  const [rawBuildPreview, setRawBuildPreview] = useState<string | null>(null);
  
  // Global loading/error
  const [loading, setLoading] = useState(false);
  const [filesLoading, setFilesLoading] = useState(false);
  const [filesError, setFilesError] = useState<string | null>(null);
  const [activitiesError, setActivitiesError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Operation-specific states
  const [operationStates, setOperationStates] = useState<Record<OperationName, OperationState>>({
    intake: { loading: false, error: null },
    planning: { loading: false, error: null },
    build: { loading: false, error: null },
    qa: { loading: false, error: null },
    review: { loading: false, error: null },
    approve: { loading: false, error: null },
    deploy: { loading: false, error: null },
  });
  
  // API cost tracking
  const [totalApiCost, setTotalApiCost] = useState(0);
  const [apiBudget] = useState(DEFAULT_API_BUDGET);
  
  // Refs for avoiding stale closures
  const projectRef = useRef<VibeProject | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  
  // Keep ref in sync
  useEffect(() => {
    projectRef.current = project;
  }, [project]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);
  
  // Helper: Set operation state
  const setOperationState = useCallback((
    operation: OperationName,
    state: Partial<OperationState>
  ) => {
    setOperationStates(prev => ({
      ...prev,
      [operation]: { ...prev[operation], ...state },
    }));
  }, []);
  
  // Helper: Track API cost
  const trackApiCost = useCallback((cost?: number) => {
    if (cost && cost > 0) {
      setTotalApiCost(prev => prev + cost);
    }
  }, []);

  // Fetch project details
  const fetchProject = useCallback(async (id: number): Promise<VibeProject | null> => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.request<{
        project: VibeProject;
        agents: VibeAgent[];
        workflow: VibeWorkflowStep[];
      }>(`/projects/${id}`);
      
      if (!response.success || !response.data) {
        setError(response.error || 'Failed to fetch project');
        return null;
      }
      
      const { project: proj, agents: agentData, workflow: workflowData } = response.data;
      
      setProject(proj);
      setAgents(agentData);
      setWorkflow(workflowData);
      
      return proj;
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : 'Failed to fetch project';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage);
      setError(friendlyMessage);
      console.error('[useVibeProject] Fetch error:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch project files
  const fetchFiles = useCallback(async (id: number): Promise<void> => {
    setFilesLoading(true);
    setFilesError(null);
    try {
      const response = await apiClient.request<{
        files: VibeFile[];
        file_tree: VibeFileTreeItem[];
      }>(`/projects/${id}/files`);
      
      if (!response.success || !response.data) {
        const errMsg = response.error || 'Failed to fetch files';
        const friendlyMsg = getFriendlyErrorMessage(errMsg);
        setFilesError(friendlyMsg);
        console.error('[useVibeProject] Fetch files error:', response.error);
        return;
      }
      
      setFiles(response.data.files);
      setFileTree(response.data.file_tree);
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : 'Failed to fetch files';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage);
      setFilesError(friendlyMessage);
      console.error('[useVibeProject] Fetch files error:', err);
    } finally {
      setFilesLoading(false);
    }
  }, []);

  // Fetch project activities (audit log)
  const fetchActivities = useCallback(async (id: number, limit = 50): Promise<void> => {
    setActivitiesError(null);
    try {
      const response = await apiClient.request<{
        activities: VibeActivity[];
        total_count: number;
      }>(`/projects/${id}/activities?limit=${limit}`);
      
      if (!response.success || !response.data) {
        const errMsg = response.error || 'Failed to fetch activities';
        const friendlyMsg = getFriendlyErrorMessage(errMsg);
        setActivitiesError(friendlyMsg);
        console.error('[useVibeProject] Fetch activities error:', response.error);
        return;
      }
      
      setActivities(response.data.activities);
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : 'Failed to fetch activities';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage);
      setActivitiesError(friendlyMessage);
      console.error('[useVibeProject] Fetch activities error:', err);
    }
  }, []);

  // Run intake conversation
  const runIntake = useCallback(async (
    id: number,
    message: string
  ): Promise<IntakeData | null> => {
    // Cancel any previous in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    setOperationState('intake', { loading: true, error: null });
    
    // Add user message to history IMMEDIATELY for responsiveness
    const currentHistory = [...intakeHistory];
    setIntakeHistory([
      ...currentHistory,
      { role: 'user', content: message },
      { role: 'assistant', content: '✨ Analyzing your message...' },
    ]);
    
    // Real-time activity polling for live tool status
    // Uses longer interval to stay within rate limits (30 req/60s)
    let lastActivityDesc = '✨ Analyzing your message...';
    let pollInterval = 3000; // Start at 3 seconds
    let activityIntervalId: ReturnType<typeof setTimeout> | null = null;
    let stopPolling = false;
    
    const pollActivities = async () => {
      if (stopPolling) return;
      
      try {
        // Fetch latest activities to show real tool usage
        const response = await apiClient.request<{
          activities: VibeActivity[];
        }>(`/projects/${id}/activities?limit=5`);
        
        if (response.success && response.data?.activities?.length) {
          // Find the most recent tool activity
          const latestActivity = response.data.activities[0];
          if (latestActivity && latestActivity.description) {
            const desc = latestActivity.description;
            // Only update if it's a tool activity (has emoji) and different from last
            if (desc.match(/^[🔍📸💾🔬🧠✅⚠️🔧]/) && desc !== lastActivityDesc) {
              lastActivityDesc = desc;
              setIntakeHistory(prev => {
                const lastMsg = prev[prev.length - 1];
                if (lastMsg?.role === 'assistant' && lastMsg.content.match(/^[✨🔍💭📝📸💾🔬🧠⚠️🔧]/)) {
                  return [...prev.slice(0, -1), { role: 'assistant', content: desc }];
                }
                return prev;
              });
            }
          }
          // Reset interval on success
          pollInterval = 3000;
        }
      } catch (err) {
        // On rate limit, back off exponentially
        if (err instanceof Error && err.message.includes('429')) {
          pollInterval = Math.min(pollInterval * 2, 15000); // Max 15s backoff
        }
      }
      
      // Schedule next poll if not stopped
      if (!stopPolling) {
        activityIntervalId = setTimeout(pollActivities, pollInterval);
      }
    };
    
    // Start polling
    activityIntervalId = setTimeout(pollActivities, pollInterval);
    
    // Fallback phases if no activities found
    const fallbackPhases = [
      '✨ Analyzing your message...',
      '💭 Thinking about the best approach...',
      '📝 Preparing response...',
    ];
    let fallbackIndex = 0;
    const fallbackInterval = setInterval(() => {
      fallbackIndex = (fallbackIndex + 1) % fallbackPhases.length;
      setIntakeHistory(prev => {
        const lastMsg = prev[prev.length - 1];
        // Only use fallback if still showing initial message
        if (lastMsg?.role === 'assistant' && lastMsg.content === '✨ Analyzing your message...') {
          return [...prev.slice(0, -1), { role: 'assistant', content: fallbackPhases[fallbackIndex] }];
        }
        return prev;
      });
    }, 4000);
    
    // Combined cleanup function
    const clearAllIntervals = () => {
      stopPolling = true;
      if (activityIntervalId) clearTimeout(activityIntervalId);
      clearInterval(fallbackInterval);
    };
    
    try {
      console.log('[runIntake] Sending to API:', { id, message: message.slice(0, 50) + '...' });
      
      const response = await apiClient.request<IntakeData>(
        `/projects/${id}/intake`,
        'POST',
        {
          message,
          conversation_history: currentHistory, // Send old history, not including the just-added message
        },
        abortControllerRef.current.signal
      );
      
      console.log('[runIntake] API Response:', response);
      
      if (!response.success || !response.data) {
        clearAllIntervals();
        const errMsg = response.error || 'Intake failed';
        console.error('[runIntake] API failed:', errMsg);
        setOperationState('intake', { loading: false, error: errMsg });
        setError(errMsg);
        // Replace thinking indicator with error
        setIntakeHistory(prev => {
          const filtered = prev.filter(m => m.role !== 'assistant' || !m.content.match(/^[✨🔍💭📝📸💾🔬🧠⚠️🔧]/));
          return [...filtered, { role: 'assistant', content: `⚠️ Error: ${errMsg}` }];
        });
        return null;
      }
      
      clearAllIntervals();
      const intakeData = response.data;
      console.log('[runIntake] Success, response:', intakeData.response?.slice(0, 100) + '...');
      
      // Track API cost (once only)
      if (response.meta?.api_cost) {
        trackApiCost(response.meta.api_cost);
      }
      
      // Replace thinking indicator with actual response
      setIntakeHistory(prev => {
        const filtered = prev.filter(m => m.role !== 'assistant' || !m.content.match(/^[✨🔍💭📝📸💾🔬🧠⚠️🔧]/));
        return [...filtered, { role: 'assistant', content: intakeData.response }];
      });
      
      // Refresh project if brief was extracted
      if (intakeData.brief_complete) {
        await fetchProject(id);
      }
      
      setOperationState('intake', { loading: false, error: null });
      return intakeData;
    } catch (err) {
      clearAllIntervals();
      const rawMessage = err instanceof Error ? err.message : 'Intake failed';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage, 'intake');
      setOperationState('intake', { loading: false, error: friendlyMessage });
      setError(friendlyMessage);
      // Replace thinking indicator with error
      setIntakeHistory(prev => {
        const filtered = prev.filter(m => m.role !== 'assistant' || !m.content.match(/^[✨🔍💭📝📸💾🔬🧠⚠️🔧]/));
        return [...filtered, { role: 'assistant', content: `⚠️ ${friendlyMessage}` }];
      });
      console.error('[useVibeProject] Intake error:', err);
      return null;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intakeHistory, fetchProject, setOperationState, trackApiCost]);

  // Helper to poll activities and update agent task
  const startActivityPolling = useCallback((id: number, agentId: string): (() => void) => {
    let stopPolling = false;
    let pollInterval = 2000;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;
    let lastDesc = '';
    
    const poll = async () => {
      if (stopPolling) return;
      try {
        const response = await apiClient.request<{ activities: VibeActivity[] }>(
          `/projects/${id}/activities?limit=3`
        );
        if (response.success && response.data?.activities?.length) {
          const latest = response.data.activities[0];
          if (latest?.description && latest.description !== lastDesc) {
            lastDesc = latest.description;
            // Update agent task with real activity
            setAgents(prev => prev.map(a => 
              a.id === agentId && a.status === 'working' 
                ? { ...a, task: latest.description.replace(/^[🔍📸💾🔬🧠✨📂📋⚠️✅🔧📝💭]\s*/, '') }
                : a
            ));
          }
          pollInterval = 2000; // Reset on success
        }
      } catch {
        pollInterval = Math.min(pollInterval * 1.5, 10000);
      }
      if (!stopPolling) {
        timeoutId = setTimeout(poll, pollInterval);
      }
    };
    
    timeoutId = setTimeout(poll, 500); // Start quickly
    
    return () => {
      stopPolling = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, []);

  // Run planning (architecture generation)
  const runPlanning = useCallback(async (id: number): Promise<BuildData | null> => {
    // Cancel any previous in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    setOperationState('planning', { loading: true, error: null });
    setAgents(prev => prev.map(a => 
      a.id === 'planning' ? { ...a, status: 'working' as const, progress: 25, task: 'Starting...' } : a
    ));
    
    // Start real-time activity polling
    const stopPolling = startActivityPolling(id, 'planning');
    
    try {
      const response = await apiClient.request<BuildData>(
        `/projects/${id}/plan`,
        'POST',
        undefined,
        abortControllerRef.current.signal
      );
      
      if (!response.success || !response.data) {
        stopPolling();
        const errMsg = response.error || 'Planning failed';
        setOperationState('planning', { loading: false, error: errMsg });
        setPipelineErrorState('planning', errMsg);
        setAgents(prev => prev.map(a => 
          a.id === 'planning' ? { ...a, status: 'error' as const, task: errMsg } : a
        ));
        setError(errMsg);
        return null;
      }
      
      stopPolling();
      trackApiCost(response.meta?.api_cost);
      
      setAgents(prev => prev.map(a => 
        a.id === 'planning' ? { ...a, status: 'complete' as const, progress: 100, task: 'Architecture complete' } : a
      ));
      
      await fetchProject(id);
      setOperationState('planning', { loading: false, error: null });
      
      return response.data;
    } catch (err) {
      stopPolling();
      const rawMessage = err instanceof Error ? err.message : 'Planning failed';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage, 'planning');
      setOperationState('planning', { loading: false, error: friendlyMessage });
      setPipelineErrorState('planning', friendlyMessage);
      setError(friendlyMessage);
      console.error('[useVibeProject] Planning error:', err);
      return null;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchProject, setOperationState, trackApiCost, startActivityPolling]);

  // Run build (code generation)
  const runBuild = useCallback(async (id: number): Promise<BuildData | null> => {
    // Cancel any previous in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    setOperationState('build', { loading: true, error: null });
    setAgents(prev => prev.map(a => 
      a.id === 'build' ? { ...a, status: 'working' as const, progress: 25, task: 'Starting...' } : a
    ));
    
    // Start real-time activity polling
    const stopPolling = startActivityPolling(id, 'build');
    
    try {
      const response = await apiClient.request<BuildData>(
        `/projects/${id}/build`,
        'POST',
        undefined,
        abortControllerRef.current.signal
      );
      
      if (!response.success || !response.data) {
        stopPolling();
        const errMsg = response.error || 'Build failed';
        setOperationState('build', { loading: false, error: errMsg });
        setPipelineErrorState('build', errMsg);
        const dataWithPreview = response.data as { raw_response_preview?: string } | undefined;
        if (dataWithPreview?.raw_response_preview) {
          setRawBuildPreview(dataWithPreview.raw_response_preview);
        }
        setAgents(prev => prev.map(a => 
          a.id === 'build' ? { ...a, status: 'error' as const, task: errMsg } : a
        ));
        setError(errMsg);
        return null;
      }
      
      stopPolling();
      trackApiCost(response.meta?.api_cost);
      
      const fileCount = response.data.file_count || 0;
      setAgents(prev => prev.map(a => 
        a.id === 'build' ? { ...a, status: 'complete' as const, progress: 100, task: `Generated ${fileCount} files` } : a
      ));
      
      await fetchProject(id);
      await fetchFiles(id);
      setOperationState('build', { loading: false, error: null });
      
      return response.data;
    } catch (err) {
      stopPolling();
      const rawMessage = err instanceof Error ? err.message : 'Build failed';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage, 'build');
      setOperationState('build', { loading: false, error: friendlyMessage });
      setPipelineErrorState('build', friendlyMessage);
      setError(friendlyMessage);
      console.error('[useVibeProject] Build error:', err);
      return null;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchProject, fetchFiles, setOperationState, trackApiCost, startActivityPolling]);

  // Run QA
  const runQA = useCallback(async (id: number): Promise<BuildData | null> => {
    // Cancel any previous in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    setOperationState('qa', { loading: true, error: null });
    setAgents(prev => prev.map(a => 
      a.id === 'qa' ? { ...a, status: 'working' as const, progress: 25, task: 'Starting...' } : a
    ));
    
    // Start real-time activity polling
    const stopPolling = startActivityPolling(id, 'qa');
    
    try {
      const response = await apiClient.request<BuildData>(
        `/projects/${id}/qa`,
        'POST',
        undefined,
        abortControllerRef.current.signal
      );
      
      if (!response.success || !response.data) {
        stopPolling();
        const errMsg = response.error || 'QA failed';
        setOperationState('qa', { loading: false, error: errMsg });
        setPipelineErrorState('qa', errMsg);
        setAgents(prev => prev.map(a => 
          a.id === 'qa' ? { ...a, status: 'error' as const, task: errMsg } : a
        ));
        setError(errMsg);
        return null;
      }
      
      stopPolling();
      trackApiCost(response.meta?.api_cost);
      
      const passed = response.data.passed;
      const issueCount = response.data.issues?.length || 0;
      
      setAgents(prev => prev.map(a => 
        a.id === 'qa' 
          ? { 
              ...a, 
              status: passed ? 'complete' as const : 'error' as const, 
              progress: 100, 
              task: passed ? 'All checks passed' : `${issueCount} issues found` 
            } 
          : a
      ));
      
      await fetchProject(id);
      setOperationState('qa', { loading: false, error: null });
      
      return response.data;
    } catch (err) {
      stopPolling();
      const rawMessage = err instanceof Error ? err.message : 'QA failed';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage, 'qa');
      setOperationState('qa', { loading: false, error: friendlyMessage });
      setPipelineErrorState('qa', friendlyMessage);
      setError(friendlyMessage);
      console.error('[useVibeProject] QA error:', err);
      return null;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchProject, setOperationState, trackApiCost, startActivityPolling]);

  // Run review
  const runReview = useCallback(async (id: number): Promise<BuildData | null> => {
    // Cancel any previous in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    setOperationState('review', { loading: true, error: null });
    setAgents(prev => prev.map(a => 
      a.id === 'review' ? { ...a, status: 'working' as const, progress: 25, task: 'Starting...' } : a
    ));
    
    // Start real-time activity polling
    const stopPolling = startActivityPolling(id, 'review');
    
    try {
      const response = await apiClient.request<BuildData>(
        `/projects/${id}/review`,
        'POST',
        undefined,
        abortControllerRef.current.signal
      );
      
      if (!response.success || !response.data) {
        stopPolling();
        const errMsg = response.error || 'Review failed';
        setOperationState('review', { loading: false, error: errMsg });
        setPipelineErrorState('review', errMsg);
        setAgents(prev => prev.map(a => 
          a.id === 'review' ? { ...a, status: 'error' as const, task: errMsg } : a
        ));
        setError(errMsg);
        return null;
      }
      
      stopPolling();
      trackApiCost(response.meta?.api_cost);
      
      const approved = response.data.approved;
      const score = response.data.score || 0;
      const recommendation = response.data.recommendation || 'Needs revision';
      
      setAgents(prev => prev.map(a => 
        a.id === 'review' 
          ? { 
              ...a, 
              status: approved ? 'complete' as const : 'error' as const, 
              progress: 100, 
              task: approved ? `Approved (${score}/10)` : recommendation
            } 
          : a
      ));
      
      await fetchProject(id);
      setOperationState('review', { loading: false, error: null });
      
      return response.data;
    } catch (err) {
      stopPolling();
      const rawMessage = err instanceof Error ? err.message : 'Review failed';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage, 'review');
      setOperationState('review', { loading: false, error: friendlyMessage });
      setPipelineErrorState('review', friendlyMessage);
      setError(friendlyMessage);
      console.error('[useVibeProject] Review error:', err);
      return null;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchProject, setOperationState, trackApiCost, startActivityPolling]);

  // Manual approval
  const approveProject = useCallback(async (id: number): Promise<boolean> => {
    // Cancel any previous in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    setOperationState('approve', { loading: true, error: null });
    
    try {
      const response = await apiClient.request(
        `/projects/${id}/approve`,
        'POST',
        undefined,
        abortControllerRef.current.signal
      );
      
      if (!response.success) {
        const errMsg = response.error || 'Approval failed';
        setOperationState('approve', { loading: false, error: errMsg });
        setError(errMsg);
        return false;
      }
      
      await fetchProject(id);
      setOperationState('approve', { loading: false, error: null });
      if (response.meta?.api_cost) trackApiCost(response.meta.api_cost);
      return true;
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : 'Approval failed';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage, 'approve');
      setOperationState('approve', { loading: false, error: friendlyMessage });
      setError(friendlyMessage);
      console.error('[useVibeProject] Approve error:', err);
      return false;
    }
  }, [fetchProject, setOperationState, trackApiCost]);

  // Deploy project
  const deployProject = useCallback(async (id: number): Promise<boolean> => {
    // Cancel any previous in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    
    setOperationState('deploy', { loading: true, error: null });
    setAgents(prev => prev.map(a => 
      a.id === 'deploy' ? { ...a, status: 'working' as const, progress: 50, task: 'Deploying...' } : a
    ));
    
    try {
      const response = await apiClient.request(
        `/projects/${id}/deploy`,
        'POST',
        undefined,
        abortControllerRef.current.signal
      );
      
      if (!response.success) {
        const errMsg = response.error || 'Deployment failed';
        setOperationState('deploy', { loading: false, error: errMsg });
        setAgents(prev => prev.map(a => 
          a.id === 'deploy' ? { ...a, status: 'error' as const, task: errMsg } : a
        ));
        setError(errMsg);
        return false;
      }
      
      setAgents(prev => prev.map(a => 
        a.id === 'deploy' ? { ...a, status: 'complete' as const, progress: 100, task: 'Deployed!' } : a
      ));
      
      await fetchProject(id);
      setOperationState('deploy', { loading: false, error: null });
      if (response.meta?.api_cost) trackApiCost(response.meta.api_cost);
      return true;
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : 'Deployment failed';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage, 'deploy');
      setOperationState('deploy', { loading: false, error: friendlyMessage });
      setError(friendlyMessage);
      console.error('[useVibeProject] Deploy error:', err);
      return false;
    }
  }, [fetchProject, setOperationState, trackApiCost]);

  // Run full pipeline
  const runPipeline = useCallback(async (id: number): Promise<boolean> => {
    setLoading(true);
    setError(null);
    clearPipelineError();
    
    // Always get fresh project state to avoid stale closure
    const freshProject = await fetchProject(id);
    
    if (!freshProject) {
      setLoading(false);
      setError('Failed to load project');
      return false;
    }
    
    // Cannot run pipeline from intake - must complete intake first
    if (freshProject.status === 'intake') {
      setLoading(false);
      setError('Complete intake conversation before running pipeline');
      return false;
    }
    
    try {
      // Planning (if needed)
      if (freshProject.status === 'planning') {
        const planResult = await runPlanning(id);
        if (!planResult || planResult.status !== 'building') {
          setLoading(false);
          return false;
        }
      }
      
      // Get updated project state
      const afterPlanning = await fetchProject(id);
      
      // Build (if needed)
      if (afterPlanning?.status === 'building') {
        const buildResult = await runBuild(id);
        if (!buildResult || buildResult.status !== 'qa') {
          setLoading(false);
          return false;
        }
      }
      
      // Get updated project state
      const afterBuild = await fetchProject(id);
      
      // QA (if needed)
      if (afterBuild?.status === 'qa') {
        const qaResult = await runQA(id);
        if (!qaResult || qaResult.status !== 'review') {
          setLoading(false);
          return false;
        }
      }
      
      // Get updated project state
      const afterQA = await fetchProject(id);
      
      // Review (if needed)
      if (afterQA?.status === 'review') {
        const reviewResult = await runReview(id);
        setLoading(false);
        return reviewResult?.approved || false;
      }
      
      setLoading(false);
      return true;
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : 'Pipeline failed';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage);
      setError(friendlyMessage);
      setLoading(false);
      console.error('[useVibeProject] Pipeline error:', err);
      return false;
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchProject, runPlanning, runBuild, runQA, runReview]);

  // Retry a stuck phase
  const retryPhase = useCallback(async (id: number, targetStatus?: string): Promise<boolean> => {
    try {
      const url = targetStatus 
        ? `/projects/${id}/retry?target_status=${targetStatus}`
        : `/projects/${id}/retry`;
      
      const response = await apiClient.request<{ status: string; message: string }>(
        url,
        'POST'
      );
      
      if (!response.success) {
        setError(response.error || 'Retry failed');
        return false;
      }
      
      // Refresh project after retry
      await fetchProject(id);
      setError(null);
      return true;
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : 'Retry failed';
      setError(getFriendlyErrorMessage(rawMessage));
      console.error('[useVibeProject] Retry error:', err);
      return false;
    }
  }, [fetchProject]);

  // Auto-fetch when projectId changes
  useEffect(() => {
    if (projectId) {
      fetchProject(projectId);
      fetchFiles(projectId);
      fetchActivities(projectId);
    } else {
      // Clear state when no project selected
      setProject(null);
      setAgents([]);
      setWorkflow([]);
      setFiles([]);
      setFileTree([]);
      setActivities([]);
      setIntakeHistory([]);
      setError(null);
    }
  }, [projectId, fetchProject, fetchFiles, fetchActivities]);

  // Track previous loading state to detect operation completion
  const wasLoadingRef = useRef(false);
  
  // Memoized computed values (must be before useEffects that use them)
  const isAnyOperationLoading = useMemo(() => 
    Object.values(operationStates).some(s => s.loading),
    [operationStates]
  );
  const setPipelineErrorState = useCallback((phase: PipelineError['phase'], message: string, raw_preview?: string) => {
    setPipelineError({ phase, message, raw_preview });
  }, []);
  const clearPipelineError = useCallback(() => {
    setPipelineError(null);
    setRawBuildPreview(null);
  }, []);
  
  // Polling for real-time updates during operations
  useEffect(() => {
    if (!projectId) return;
    
    // Detect when operation just completed (was loading, now not)
    if (wasLoadingRef.current && !isAnyOperationLoading) {
      // Final refresh after operation completes
      fetchActivities(projectId, 25);
      fetchProject(projectId);
    }
    wasLoadingRef.current = isAnyOperationLoading;
    
    if (!isAnyOperationLoading) return;
    
    // Initial refresh when operation starts
    fetchActivities(projectId, 25);
    
    // Periodic refresh during operations - faster for real-time feel
    const interval = window.setInterval(() => {
      fetchActivities(projectId, 25);
      fetchProject(projectId);
    }, 2000); // Reduced from 4s to 2s for faster updates
    
    return () => window.clearInterval(interval);
  }, [projectId, isAnyOperationLoading, fetchActivities, fetchProject]);

  // Additional memoized values
  const remainingApiBudget = useMemo(() =>
    Math.max(0, apiBudget - totalApiCost),
    [apiBudget, totalApiCost]
  );
  
  const canRunPipeline = useMemo(() => 
    project !== null && 
    project.status !== 'intake' && 
    project.status !== 'approved' && 
    project.status !== 'deployed' &&
    !isAnyOperationLoading,
    [project, isAnyOperationLoading]
  );
  
  const canApprove = useMemo(() =>
    project?.status === 'review' && !isAnyOperationLoading,
    [project, isAnyOperationLoading]
  );
  
  const canDeploy = useMemo(() =>
    project?.status === 'approved' && !isAnyOperationLoading,
    [project, isAnyOperationLoading]
  );

  return {
    // Data
    project,
    agents,
    workflow,
    files,
    fileTree,
    intakeHistory,
    activities,
    
    // Global state
    loading,
    filesLoading,
    filesError,
    activitiesError,
    error,
    
    // Operation-specific states
    operationStates,
    isAnyOperationLoading,
    
    // Computed flags
    canRunPipeline,
    canApprove,
    canDeploy,
    
    // Cost tracking
    totalApiCost,
    apiBudget,
    remainingApiBudget,
    pipelineError,
    rawBuildPreview,
    
    // Actions
    fetchProject,
    fetchFiles,
    fetchActivities,
    runIntake,
    runPlanning,
    runBuild,
    runQA,
    runReview,
    approveProject,
    deployProject,
    runPipeline,
    retryPhase,
    
    // Helpers
    clearIntakeHistory: useCallback(() => setIntakeHistory([]), []),
    clearError: useCallback(() => setError(null), []),
    clearPipelineError,
    resetOperationStates: useCallback(() => {
      setOperationStates({
        intake: { loading: false, error: null },
        planning: { loading: false, error: null },
        build: { loading: false, error: null },
        qa: { loading: false, error: null },
        review: { loading: false, error: null },
        approve: { loading: false, error: null },
        deploy: { loading: false, error: null },
      });
    }, []),
  };
}

// ============================================================================
// HOOK: useVibeFile (Single File)
// ============================================================================

export function useVibeFile(projectId: number, filePath?: string) {
  const [file, setFile] = useState<VibeFile | null>(null);
  const [language, setLanguage] = useState('text');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchFile = useCallback(async (path: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await apiClient.request<{
        file: VibeFile;
        language: string;
      }>(`/projects/${projectId}/files/${encodeURIComponent(path)}`);
      
      if (!response.success || !response.data) {
        setError(response.error || 'Failed to fetch file');
        return;
      }
      
      setFile(response.data.file);
      setLanguage(response.data.language);
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : 'Failed to fetch file';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage);
      setError(friendlyMessage);
      console.error('[useVibeFile] Fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (filePath) {
      fetchFile(filePath);
    }
  }, [filePath, fetchFile]);

  return {
    file,
    language,
    loading,
    error,
    fetchFile,
  };
}

// ============================================================================
// HOOK: useVibeLessons
// ============================================================================

export function useVibeLessons() {
  const [lessons, setLessons] = useState<VibeLesson[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLessons = useCallback(async (
    projectType: ProjectType,
    category?: string,
    limit = 10
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      let params = `?project_type=${projectType}&limit=${limit}`;
      if (category) params += `&category=${category}`;
      
      const response = await apiClient.request<{ lessons: VibeLesson[] }>(
        `/lessons${params}`
      );
      
      if (!response.success) {
        setError(response.error || 'Failed to fetch lessons');
        return;
      }
      
      setLessons(response.data?.lessons || []);
    } catch (err) {
      const rawMessage = err instanceof Error ? err.message : 'Failed to fetch lessons';
      const friendlyMessage = getFriendlyErrorMessage(rawMessage);
      setError(friendlyMessage);
      console.error('[useVibeLessons] Fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    lessons,
    loading,
    error,
    fetchLessons,
  };
}
