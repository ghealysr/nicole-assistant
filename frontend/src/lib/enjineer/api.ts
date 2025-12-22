/**
 * Enjineer API Client
 * 
 * Handles all communication with the backend for the Enjineer IDE.
 * Nicole's tool calls flow through this API.
 */

import { EnjineerFile, PlanStep, Project } from './store';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.nicole.alphawavetech.com';

function getAuthHeaders(): HeadersInit {
  // Check multiple token keys for compatibility
  const token = typeof window !== 'undefined' 
    ? (localStorage.getItem('nicole_token') || 
       localStorage.getItem('auth_token') || 
       localStorage.getItem('nicole_google_token') ||
       localStorage.getItem('token'))
    : null;
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
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
  
  async createProject(name: string, description: string): Promise<Project> {
    const res = await fetch(`${API_BASE}/enjineer/projects`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ name, description }),
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
    return {
      id: data.project.id,
      name: data.project.name,
      description: data.project.description,
      status: data.project.status,
      createdAt: new Date(data.project.created_at),
      updatedAt: new Date(data.project.updated_at),
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
          if (!dataStr || dataStr === '[DONE]') continue;
          
          try {
            // Parse the SSE data - handle both single quotes and double quotes
            const jsonStr = dataStr
              .replace(/'/g, '"')
              .replace(/True/g, 'true')
              .replace(/False/g, 'false')
              .replace(/None/g, 'null');
            
            const event = JSON.parse(jsonStr) as ChatEvent;
            onEvent(event);
          } catch (e) {
            // Try direct parse if replacement fails
            try {
              const event = JSON.parse(dataStr) as ChatEvent;
              onEvent(event);
            } catch {
              console.warn('[Enjineer API] Failed to parse SSE event:', dataStr, e);
            }
          }
        }
      }
    }
    
    // Process any remaining buffer
    if (buffer.trim() && buffer.startsWith('data: ')) {
      const dataStr = buffer.slice(6).trim();
      if (dataStr && dataStr !== '[DONE]') {
        try {
          const jsonStr = dataStr.replace(/'/g, '"');
          const event = JSON.parse(jsonStr) as ChatEvent;
          onEvent(event);
        } catch {
          // Ignore
        }
      }
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
  
  async getPlan(projectId: number): Promise<PlanStep[]> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/plan`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) return [];
    const data = await res.json();
    
    // Backend returns {plan: {...}, phases: [...]}
    const phases = data.phases || [];
    if (phases.length === 0) return [];
    
    return phases.map((p: Record<string, unknown>) => ({
      id: p.id as string || crypto.randomUUID(),
      title: p.name as string,
      description: p.notes as string || '',
      status: p.status as string || 'pending',
      files: [],
    }));
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
};

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
