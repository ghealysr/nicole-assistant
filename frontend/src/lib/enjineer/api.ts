/**
 * Enjineer API Client
 * 
 * Handles all communication with the backend for the Enjineer IDE.
 * Nicole's tool calls flow through this API.
 */

import { EnjineerFile, PlanStep, Project } from './store';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://alphawave-api.online';

function getAuthHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
}

export const enjineerApi = {
  // Project Management
  async createProject(name: string, description: string): Promise<Project> {
    const res = await fetch(`${API_BASE}/enjineer/projects`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ name, description }),
    });
    if (!res.ok) throw new Error('Failed to create project');
    return res.json();
  },

  async getProject(id: number): Promise<Project> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${id}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get project');
    return res.json();
  },

  async listProjects(): Promise<Project[]> {
    const res = await fetch(`${API_BASE}/enjineer/projects`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to list projects');
    const data = await res.json();
    return data.projects || [];
  },

  // File Operations
  async getFiles(projectId: number): Promise<EnjineerFile[]> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/files`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get files');
    const data = await res.json();
    return (data.files || []).map((f: { path: string; content: string }) => ({
      path: f.path,
      content: f.content,
      language: getLanguageFromPath(f.path),
      isModified: false,
    }));
  },

  async saveFile(projectId: number, path: string, content: string): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/files`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({ path, content }),
    });
    if (!res.ok) throw new Error('Failed to save file');
  },

  async createFile(projectId: number, path: string, content: string): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/files`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ path, content }),
    });
    if (!res.ok) throw new Error('Failed to create file');
  },

  async deleteFile(projectId: number, path: string): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/files/${encodeURIComponent(path)}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete file');
  },

  // Chat with Nicole - SSE stream
  async chat(projectId: number, message: string, onChunk: (chunk: string) => void): Promise<void> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/chat`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ message }),
    });

    if (!res.ok) throw new Error('Failed to send message');
    if (!res.body) throw new Error('No response body');

    const reader = res.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') break;
          try {
            const parsed = JSON.parse(data);
            if (parsed.type === 'text' && parsed.content) {
              onChunk(parsed.content);
            }
          } catch {
            // Skip non-JSON lines
          }
        }
      }
    }
  },

  // Plan Management
  async getPlan(projectId: number): Promise<PlanStep[]> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/plan`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.steps || [];
  },

  // Agent Dispatch
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

  // Deploy
  async deploy(projectId: number): Promise<{ url: string }> {
    const res = await fetch(`${API_BASE}/enjineer/projects/${projectId}/deploy`, {
      method: 'POST',
      headers: getAuthHeaders(),
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
    json: 'json',
    md: 'markdown',
    html: 'html',
  };
  return langMap[ext || ''] || 'plaintext';
}

