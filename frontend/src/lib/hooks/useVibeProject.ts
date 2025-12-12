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
import { API_BASE_URL } from '@/lib/alphawave_config';

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

// ============================================================================
// API CLIENT
// ============================================================================

class VibeAPIClient {
  private baseUrl: string;
  
  constructor() {
    this.baseUrl = `${API_BASE_URL}/vibe`;
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
    body?: Record<string, unknown>
  ): Promise<APIResponse<T>> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method,
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      return {
        success: false,
        error: data.detail || data.error || `Request failed with status ${response.status}`,
      };
    }
    
    return data as APIResponse<T>;
  }
}

const apiClient = new VibeAPIClient();

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
      const message = err instanceof Error ? err.message : 'Failed to fetch projects';
      setError(message);
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
      const response = await apiClient.request<{ project: VibeProject }>(
        '/projects',
        'POST',
        {
          name,
          project_type: projectType,
          client_name: clientName,
          client_email: clientEmail,
        }
      );
      
      if (!response.success || !response.data?.project) {
        setError(response.error || 'Failed to create project');
        return null;
      }
      
      const newProject = response.data.project;
      setProjects(prev => [newProject, ...prev]);
      
      return newProject;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create project';
      setError(message);
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
      const message = err instanceof Error ? err.message : 'Failed to delete project';
      setError(message);
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
  
  // Global loading/error
  const [loading, setLoading] = useState(false);
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
      const message = err instanceof Error ? err.message : 'Failed to fetch project';
      setError(message);
      console.error('[useVibeProject] Fetch error:', err);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch project files
  const fetchFiles = useCallback(async (id: number): Promise<void> => {
    try {
      const response = await apiClient.request<{
        files: VibeFile[];
        file_tree: VibeFileTreeItem[];
      }>(`/projects/${id}/files`);
      
      if (!response.success || !response.data) {
        console.error('[useVibeProject] Fetch files error:', response.error);
        return;
      }
      
      setFiles(response.data.files);
      setFileTree(response.data.file_tree);
    } catch (err) {
      console.error('[useVibeProject] Fetch files error:', err);
    }
  }, []);

  // Run intake conversation
  const runIntake = useCallback(async (
    id: number,
    message: string
  ): Promise<IntakeData | null> => {
    setOperationState('intake', { loading: true, error: null });
    
    // Add user message to history immediately for responsiveness
    const updatedHistory = [
      ...intakeHistory,
      { role: 'user', content: message },
    ];
    
    try {
      const response = await apiClient.request<IntakeData>(
        `/projects/${id}/intake`,
        'POST',
        {
          message,
          conversation_history: intakeHistory,
        }
      );
      
      if (!response.success || !response.data) {
        const errMsg = response.error || 'Intake failed';
        setOperationState('intake', { loading: false, error: errMsg });
        setError(errMsg);
        return null;
      }
      
      // Update history with assistant response
      setIntakeHistory([
        ...updatedHistory,
        { role: 'assistant', content: response.data.response },
      ]);
      
      // Track cost
      trackApiCost(response.meta?.api_cost);
      
      // Refresh project if brief was extracted
      if (response.data.brief_complete) {
        await fetchProject(id);
      }
      
      setOperationState('intake', { loading: false, error: null });
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Intake failed';
      setOperationState('intake', { loading: false, error: message });
      setError(message);
      console.error('[useVibeProject] Intake error:', err);
      return null;
    }
  }, [intakeHistory, fetchProject, setOperationState, trackApiCost]);

  // Run planning (architecture generation)
  const runPlanning = useCallback(async (id: number): Promise<BuildData | null> => {
    setOperationState('planning', { loading: true, error: null });
    setAgents(prev => prev.map(a => 
      a.id === 'planning' ? { ...a, status: 'working' as const, progress: 25, task: 'Generating architecture...' } : a
    ));
    
    try {
      const response = await apiClient.request<BuildData>(
        `/projects/${id}/plan`,
        'POST'
      );
      
      if (!response.success || !response.data) {
        const errMsg = response.error || 'Planning failed';
        setOperationState('planning', { loading: false, error: errMsg });
        setAgents(prev => prev.map(a => 
          a.id === 'planning' ? { ...a, status: 'error' as const, task: errMsg } : a
        ));
        setError(errMsg);
        return null;
      }
      
      trackApiCost(response.meta?.api_cost);
      
      setAgents(prev => prev.map(a => 
        a.id === 'planning' ? { ...a, status: 'complete' as const, progress: 100, task: 'Architecture complete' } : a
      ));
      
      await fetchProject(id);
      setOperationState('planning', { loading: false, error: null });
      
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Planning failed';
      setOperationState('planning', { loading: false, error: message });
      setError(message);
      console.error('[useVibeProject] Planning error:', err);
      return null;
    }
  }, [fetchProject, setOperationState, trackApiCost]);

  // Run build (code generation)
  const runBuild = useCallback(async (id: number): Promise<BuildData | null> => {
    setOperationState('build', { loading: true, error: null });
    setAgents(prev => prev.map(a => 
      a.id === 'build' ? { ...a, status: 'working' as const, progress: 25, task: 'Generating code...' } : a
    ));
    
    try {
      const response = await apiClient.request<BuildData>(
        `/projects/${id}/build`,
        'POST'
      );
      
      if (!response.success || !response.data) {
        const errMsg = response.error || 'Build failed';
        setOperationState('build', { loading: false, error: errMsg });
        setAgents(prev => prev.map(a => 
          a.id === 'build' ? { ...a, status: 'error' as const, task: errMsg } : a
        ));
        setError(errMsg);
        return null;
      }
      
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
      const message = err instanceof Error ? err.message : 'Build failed';
      setOperationState('build', { loading: false, error: message });
      setError(message);
      console.error('[useVibeProject] Build error:', err);
      return null;
    }
  }, [fetchProject, fetchFiles, setOperationState, trackApiCost]);

  // Run QA
  const runQA = useCallback(async (id: number): Promise<BuildData | null> => {
    setOperationState('qa', { loading: true, error: null });
    setAgents(prev => prev.map(a => 
      a.id === 'qa' ? { ...a, status: 'working' as const, progress: 25, task: 'Running QA checks...' } : a
    ));
    
    try {
      const response = await apiClient.request<BuildData>(
        `/projects/${id}/qa`,
        'POST'
      );
      
      if (!response.success || !response.data) {
        const errMsg = response.error || 'QA failed';
        setOperationState('qa', { loading: false, error: errMsg });
        setAgents(prev => prev.map(a => 
          a.id === 'qa' ? { ...a, status: 'error' as const, task: errMsg } : a
        ));
        setError(errMsg);
        return null;
      }
      
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
      const message = err instanceof Error ? err.message : 'QA failed';
      setOperationState('qa', { loading: false, error: message });
      setError(message);
      console.error('[useVibeProject] QA error:', err);
      return null;
    }
  }, [fetchProject, setOperationState, trackApiCost]);

  // Run review
  const runReview = useCallback(async (id: number): Promise<BuildData | null> => {
    setOperationState('review', { loading: true, error: null });
    setAgents(prev => prev.map(a => 
      a.id === 'review' ? { ...a, status: 'working' as const, progress: 25, task: 'Final review...' } : a
    ));
    
    try {
      const response = await apiClient.request<BuildData>(
        `/projects/${id}/review`,
        'POST'
      );
      
      if (!response.success || !response.data) {
        const errMsg = response.error || 'Review failed';
        setOperationState('review', { loading: false, error: errMsg });
        setAgents(prev => prev.map(a => 
          a.id === 'review' ? { ...a, status: 'error' as const, task: errMsg } : a
        ));
        setError(errMsg);
        return null;
      }
      
      trackApiCost(response.meta?.api_cost);
      
      const approved = response.data.approved;
      const score = response.data.score || 0;
      
      setAgents(prev => prev.map(a => 
        a.id === 'review' 
          ? { 
              ...a, 
              status: approved ? 'complete' as const : 'error' as const, 
              progress: 100, 
              task: approved ? `Approved (${score}/10)` : response.data.recommendation || 'Needs revision'
            } 
          : a
      ));
      
      await fetchProject(id);
      setOperationState('review', { loading: false, error: null });
      
      return response.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Review failed';
      setOperationState('review', { loading: false, error: message });
      setError(message);
      console.error('[useVibeProject] Review error:', err);
      return null;
    }
  }, [fetchProject, setOperationState, trackApiCost]);

  // Manual approval
  const approveProject = useCallback(async (id: number): Promise<boolean> => {
    setOperationState('approve', { loading: true, error: null });
    
    try {
      const response = await apiClient.request(
        `/projects/${id}/approve`,
        'POST'
      );
      
      if (!response.success) {
        const errMsg = response.error || 'Approval failed';
        setOperationState('approve', { loading: false, error: errMsg });
        setError(errMsg);
        return false;
      }
      
      await fetchProject(id);
      setOperationState('approve', { loading: false, error: null });
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Approval failed';
      setOperationState('approve', { loading: false, error: message });
      setError(message);
      console.error('[useVibeProject] Approve error:', err);
      return false;
    }
  }, [fetchProject, setOperationState]);

  // Deploy project
  const deployProject = useCallback(async (id: number): Promise<boolean> => {
    setOperationState('deploy', { loading: true, error: null });
    setAgents(prev => prev.map(a => 
      a.id === 'deploy' ? { ...a, status: 'working' as const, progress: 50, task: 'Deploying...' } : a
    ));
    
    try {
      const response = await apiClient.request(
        `/projects/${id}/deploy`,
        'POST'
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
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Deployment failed';
      setOperationState('deploy', { loading: false, error: message });
      setError(message);
      console.error('[useVibeProject] Deploy error:', err);
      return false;
    }
  }, [fetchProject, setOperationState]);

  // Run full pipeline
  const runPipeline = useCallback(async (id: number): Promise<boolean> => {
    setLoading(true);
    setError(null);
    
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
      const message = err instanceof Error ? err.message : 'Pipeline failed';
      setError(message);
      setLoading(false);
      console.error('[useVibeProject] Pipeline error:', err);
      return false;
    }
  }, [fetchProject, runPlanning, runBuild, runQA, runReview]);

  // Auto-fetch when projectId changes
  useEffect(() => {
    if (projectId) {
      fetchProject(projectId);
      fetchFiles(projectId);
    } else {
      // Clear state when no project selected
      setProject(null);
      setAgents([]);
      setWorkflow([]);
      setFiles([]);
      setFileTree([]);
      setIntakeHistory([]);
      setError(null);
    }
  }, [projectId, fetchProject, fetchFiles]);

  // Memoized computed values
  const isAnyOperationLoading = useMemo(() => 
    Object.values(operationStates).some(s => s.loading),
    [operationStates]
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
    
    // Global state
    loading,
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
    
    // Actions
    fetchProject,
    fetchFiles,
    runIntake,
    runPlanning,
    runBuild,
    runQA,
    runReview,
    approveProject,
    deployProject,
    runPipeline,
    
    // Helpers
    clearIntakeHistory: useCallback(() => setIntakeHistory([]), []),
    clearError: useCallback(() => setError(null), []),
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
      const message = err instanceof Error ? err.message : 'Failed to fetch file';
      setError(message);
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
      const message = err instanceof Error ? err.message : 'Failed to fetch lessons';
      setError(message);
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
