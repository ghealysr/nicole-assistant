/**
 * Enjineer API Client
 * 
 * Handles all communication with the backend for the Enjineer IDE.
 * Nicole's tool calls flow through this API.
 */

import { EnjineerFile, PlanStep, PlanOverview, Project } from './store';

/**
 * API Base URL - Hardcoded for reliability
 * Environment variables are baked at build time and can cause stale cache issues.
 */
const API_BASE = 'https://api.nicole.alphawavetech.com';

/**
 * Get authentication headers with token.
 * Checks all possible token storage keys used by the auth system.
 * Order matters: nicole_google_token is the primary key used by Google OAuth.
 */
function getAuthHeaders(): HeadersInit {
  if (typeof window === 'undefined') {
    return { 'Content-Type': 'application/json' };
  }
  
  // Check token keys in priority order (Google OAuth token first, then legacy)
  const token = 
    localStorage.getItem('nicole_google_token') ||  // Primary: Google OAuth ID token
    localStorage.getItem('nicole_token') ||          // Legacy Nicole token
    localStorage.getItem('auth_token');              // Generic fallback
  
  if (!token) {
    console.warn('[Enjineer API] No auth token found in localStorage');
  }
  
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
}

/**
 * Map backend phase status + approval_status to frontend display status
 */
function mapPhaseStatus(
  status: string | undefined, 
  approvalStatus: string | undefined
): 'pending' | 'in_progress' | 'complete' | 'skipped' | 'awaiting_approval' {
  // If waiting for approval, show that status
  if (approvalStatus === 'pending' && status === 'in_progress') {
    return 'awaiting_approval';
  }
  
  switch (status) {
    case 'complete':
    case 'completed':
      return 'complete';
    case 'in_progress':
    case 'active':
      return 'in_progress';
    case 'skipped':
      return 'skipped';
    default:
      return 'pending';
  }
}

// SSE Event Types from backend
export interface ChatEvent {
  type: 'text' | 'thinking' | 'tool_use' | 'tool_result' | 'code' | 'approval_required' | 'error' | 'done';
  content?: string;
  tool?: string;
  input?: Record<string, unknown>;
  result?: Record<string, unknown>;
  status?: 'starting' | 'running' | 'complete' | 'error';
  path?: string;
  action?: 'created' | 'updated' | 'deleted';
  approval_id?: string;
  title?: string;
}

export const enjineerApi = {
  // ========================================================================
  // Project Management
  // ========================================================================
  
  /**
   * Create a new project with optional inspiration images.
   * Images are sent as base64 data URLs for Claude Vision analysis.
   */
  async createProject(
    name: string, 
    description: string,
    inspirationImages?: string[]  // Array of base64 data URLs
  ): Promise<Project> {
    const res = await fetch(`${API_BASE}/enjineer/projects`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ 
        name, 
        description,
        inspiration_images: inspirationImages || []
      }),
    });
    if (!res.ok) {
      const error = await res.text();
      throw new Error(`Failed to create project: ${error}`);
    }
    const data = await res.json();
    return {
      id: data.id,
      name: data.name,
      description: data.description,
      status: data.status,
      createdAt: new Date(data.created_at),
      updatedAt: new Date(data.updated_at),
    };
  },

  async getProject(id: number): Promise<Project> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${id}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get project');
    const data = await res.json();
    
    // Backend returns {project: {...}, files: [...], plan: {...}, pending_approvals: [...]}
    // ProjectResponse fields use snake_case
    const project = data.project;
    if (!project) {
      throw new Error('Invalid project response: missing project data');
    }
    
    return {
      id: project.id,
      name: project.name,
      description: project.description,
      status: project.status,
      createdAt: new Date(project.created_at),
      updatedAt: new Date(project.updated_at),
    };
  },

  async listProjects(): Promise<Project[]> {
    const res = await fetch(`${API_BASE}/enjineer/projects`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const error = await res.text();
      throw new Error(`Failed to list projects: ${error}`);
    }
    const data = await res.json();
    // Backend returns array directly, not {projects: [...]}
    const projects = Array.isArray(data) ? data : (data.projects || []);
    return projects.map((p: Record<string, unknown>) => ({
      id: p.id as number,
      name: p.name as string,
      description: p.description as string | undefined,
      status: p.status as string,
      createdAt: new Date(p.created_at as string),
      updatedAt: new Date(p.updated_at as string),
    }));
  },

  // ========================================================================
  // File Operations
  // ========================================================================
  
  async getFiles(projectId: number): Promise<EnjineerFile[]> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/files`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get files');
    const data = await res.json();
    // Backend returns array directly, not {files: [...]}
    const files = Array.isArray(data) ? data : (data.files || []);
    return files.map((f: Record<string, unknown>) => ({
      path: f.path as string,
      content: f.content as string,
      language: f.language as string || getLanguageFromPath(f.path as string),
      isModified: false,
    }));
  },

  async saveFile(projectId: number, path: string, content: string): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/files/${encodeURIComponent(path.replace(/^\//, ''))}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({ content }),
    });
    if (!res.ok) throw new Error('Failed to save file');
  },

  async createFile(projectId: number, path: string, content: string, language?: string): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/files`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ path, content, language }),
    });
    if (!res.ok) throw new Error('Failed to create file');
  },

  async deleteFile(projectId: number, path: string): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/files/${encodeURIComponent(path.replace(/^\//, ''))}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete file');
  },

  // ========================================================================
  // Chat with Nicole - SSE Streaming
  // ========================================================================
  
  async chat(
    projectId: number, 
    message: string, 
    onEvent: (event: ChatEvent) => void
  ): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/chat`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ message }),
    });

    if (!res.ok) {
      const error = await res.text();
      throw new Error(`Failed to send message: ${error}`);
    }
    if (!res.body) throw new Error('No response body');

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    /**
     * Parse SSE event data.
     * Backend now sends proper JSON, but we maintain backwards compatibility
     * with Python-style format just in case.
     */
    const parseEventData = (dataStr: string): ChatEvent | null => {
      if (!dataStr || dataStr === '[DONE]') return null;
      
      // First, try parsing as-is (proper JSON from updated backend)
      try {
        return JSON.parse(dataStr) as ChatEvent;
      } catch {
        // Fallback: handle legacy Python-style format
        try {
          const jsonStr = dataStr
            .replace(/'/g, '"')
            .replace(/True/g, 'true')
            .replace(/False/g, 'false')
            .replace(/None/g, 'null');
          return JSON.parse(jsonStr) as ChatEvent;
        } catch (e) {
          console.warn('[Enjineer API] Failed to parse SSE event:', dataStr, e);
          return null;
        }
      }
    };

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      
      // Keep the last incomplete line in the buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim();
          const event = parseEventData(dataStr);
          if (event) onEvent(event);
        }
      }
    }
    
    // Process any remaining buffer
    if (buffer.trim() && buffer.startsWith('data: ')) {
      const dataStr = buffer.slice(6).trim();
      const event = parseEventData(dataStr);
      if (event) onEvent(event);
    }
  },

  // ========================================================================
  // Chat History
  // ========================================================================
  
  async getChatHistory(projectId: number, limit = 50): Promise<Array<{
    id: string;
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp: Date;
  }>> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/chat/history?limit=${limit}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.map((m: Record<string, unknown>) => ({
      id: m.id as string,
      role: m.role as 'user' | 'assistant' | 'system',
      content: m.content as string,
      timestamp: new Date(m.created_at as string),
    }));
  },

  // ========================================================================
  // Plan Management
  // ========================================================================
  
  async getPlan(projectId: number): Promise<{ overview: PlanOverview | null; phases: PlanStep[] }> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/plan`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) return { overview: null, phases: [] };
    const data = await res.json();
    
    // Parse plan overview (backend returns camelCase)
    const planData = data.plan;
    let overview: PlanOverview | null = null;
    if (planData) {
      const phases = data.phases || [];
      overview = {
        id: String(planData.id),
        version: planData.version || 1,
        status: planData.status || 'planning',
        currentPhaseNumber: planData.currentPhase || 1,
        totalPhases: phases.length,
        completedPhases: phases.filter((p: Record<string, unknown>) => p.status === 'complete').length,
        createdAt: new Date(planData.createdAt),
        approvedAt: planData.approvedAt ? new Date(planData.approvedAt) : undefined,
        completedAt: planData.completedAt ? new Date(planData.completedAt) : undefined,
      };
    }
    
    // Parse phases with full data (backend returns camelCase)
    const phases = (data.phases || []).map((p: Record<string, unknown>) => ({
      id: String(p.id) || crypto.randomUUID(),
      phaseNumber: (p.phaseNumber as number) || 1,
      title: (p.name as string) || `Phase ${p.phaseNumber}`,
      description: (p.notes as string) || '',
      status: mapPhaseStatus(p.status as string, p.approvalStatus as string),
      estimatedMinutes: p.estimatedMinutes as number | undefined,
      actualMinutes: p.actualMinutes as number | undefined,
      agentsRequired: p.agentsRequired as ('engineer' | 'qa' | 'sr_qa')[] | undefined,
      requiresApproval: p.requiresApproval as boolean | undefined,
      approvalStatus: p.approvalStatus as 'pending' | 'approved' | 'rejected' | null,
      qaDepth: p.qaDepth as 'basic' | 'standard' | 'thorough' | undefined,
      qaFocus: p.qaFocus as string[] | undefined,
      startedAt: p.startedAt ? new Date(p.startedAt as string) : undefined,
      completedAt: p.completedAt ? new Date(p.completedAt as string) : undefined,
      approvedAt: p.approvedAt ? new Date(p.approvedAt as string) : undefined,
      notes: p.notes as string | undefined,
      files: [],
    }));
    
    return { overview, phases };
  },
  
  async approvePlan(projectId: number, planId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/plan/${planId}/approve`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to approve plan');
    }
  },
  
  async approvePhase(projectId: number, phaseId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/plan/phases/${phaseId}/approve`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to approve phase');
    }
  },
  
  async rejectPhase(projectId: number, phaseId: string, reason?: string): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/plan/phases/${phaseId}/reject`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ reason }),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new Error(error.detail || 'Failed to reject phase');
    }
  },

  // ========================================================================
  // Approvals
  // ========================================================================
  
  async approveAction(projectId: number, approvalId: string, note?: string): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/approvals/${approvalId}/approve`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ note }),
    });
    if (!res.ok) throw new Error('Failed to approve');
  },

  async rejectAction(projectId: number, approvalId: string, reason?: string): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/approvals/${approvalId}/reject`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ reason }),
    });
    if (!res.ok) throw new Error('Failed to reject');
  },

  // ========================================================================
  // Agent Dispatch
  // ========================================================================
  
  async dispatchAgent(
    projectId: number, 
    agent: 'engineer' | 'qa' | 'sr_qa', 
    task: string
  ): Promise<{ taskId: string }> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/agents/${agent}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ task }),
    });
    if (!res.ok) throw new Error(`Failed to dispatch ${agent}`);
    return res.json();
  },

  // ========================================================================
  // Deploy
  // ========================================================================
  
  async deploy(projectId: number, environment: 'preview' | 'production' = 'preview'): Promise<{ url: string }> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/deploy`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ environment }),
    });
    if (!res.ok) throw new Error('Failed to deploy');
    return res.json();
  },

  // ========================================================================
  // Preview - Local sandbox preview without deployment
  // ========================================================================
  
  /**
   * Get preview bundle with all project files for Sandpack/iframe rendering.
   */
  async getPreviewBundle(projectId: number): Promise<PreviewBundle> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/preview/bundle`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get preview bundle');
    return res.json();
  },

  /**
   * Get static HTML preview (for simple HTML/CSS/JS projects).
   */
  async getPreviewHtml(projectId: number): Promise<string> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/preview/html`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get preview HTML');
    return res.text();
  },

  /**
   * Get URL for preview HTML endpoint (for iframe src).
   */
  getPreviewHtmlUrl(projectId: number): string {
    // Note: For iframe src, we use srcdoc approach since we can't add auth headers to iframe src
    // The frontend fetches the HTML content via getPreviewHtml() and sets it as srcdoc
    return `${API_BASE}/enjineer/projects/${projectId}/preview/html`;
  },

  // ========================================================================
  // Vercel Preview & Production Deployments
  // ========================================================================

  /**
   * Deploy project to Vercel for live preview.
   * Uses persistent Vercel project per Enjineer project.
   * Domain: project-{id}.enjineer.alphawavetech.com
   */
  async deployPreview(projectId: number, framework?: string): Promise<{
    deployment_id: string;
    url: string;
    preview_domain: string | null;
    status: string;
    message: string;
  }> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/preview/deploy`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ framework }),
    });
    if (!res.ok) {
      const error = await res.text();
      throw new Error(`Failed to deploy preview: ${error}`);
    }
    return res.json();
  },

  /**
   * Get current preview info for a project.
   * Returns persistent preview domain and latest deployment info.
   */
  async getPreviewInfo(projectId: number): Promise<{
    preview: {
      domain: string | null;
      last_deployment_id: string | null;
      last_url: string | null;
      last_deployed_at: string | null;
    };
    production: {
      domain: string | null;
      last_url: string | null;
      last_deployed_at: string | null;
    };
  }> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/preview`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get preview info');
    return res.json();
  },

  /**
   * Get status of a preview deployment.
   */
  async getPreviewStatus(projectId: number, deploymentId: string): Promise<{
    deployment_id: string;
    url: string;
    status: string;
    ready: boolean;
  }> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/preview/status/${deploymentId}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get preview status');
    return res.json();
  },

  /**
   * Delete a preview deployment to clean up resources.
   */
  async deletePreview(projectId: number, deploymentId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/preview/${deploymentId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete preview');
  },

  /**
   * Clean up old preview deployments, keeping only the most recent.
   */
  async cleanupPreviews(projectId: number, keepCount: number = 1): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/preview/cleanup?keep_count=${keepCount}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to cleanup previews');
    return res.json();
  },

  /**
   * Deploy project to production with optional custom domain.
   */
  async deployProduction(projectId: number, domain?: string): Promise<{
    deployment_id: string;
    url: string;
    custom_domain: string | null;
    status: string;
    message: string;
  }> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/production/deploy`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ domain }),
    });
    if (!res.ok) {
      const error = await res.text();
      throw new Error(`Failed to deploy to production: ${error}`);
    }
    return res.json();
  },
};

// Preview Bundle type
export interface PreviewBundle {
  project_id: number;
  project_type: 'static' | 'react' | 'nextjs' | 'html';
  entry_file: string;
  files: Record<string, string>;
  dependencies: Record<string, string>;
}

// Helper function
function getLanguageFromPath(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase();
  const langMap: Record<string, string> = {
    ts: 'typescript',
    tsx: 'tsx',
    js: 'javascript',
    jsx: 'jsx',
    css: 'css',
    scss: 'scss',
    json: 'json',
    md: 'markdown',
    html: 'html',
    py: 'python',
    sql: 'sql',
  };
  return langMap[ext || ''] || 'plaintext';
}
