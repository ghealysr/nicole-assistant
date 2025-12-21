import { API_URL } from '@/lib/alphawave_config';
import { getAuthHeaders } from '@/lib/alphawave_utils';
import { FazProject, FazFile, FazActivity, ChatMessage, Architecture } from '@/types/faz';

const FAZ_API_URL = `${API_URL}/faz`;

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.ok) return res.json();
  let detail = '';
  try {
    const body = await res.json();
    detail = body.detail || body.message || JSON.stringify(body);
  } catch {
    detail = await res.text();
  }
  const prefix = `Request failed (${res.status})`;
  throw new Error(detail ? `${prefix}: ${detail}` : prefix);
}

export const fazApi = {
  // Projects
  async listProjects(limit = 20, offset = 0): Promise<{ projects: FazProject[], total: number }> {
    const res = await fetch(`${FAZ_API_URL}/projects?limit=${limit}&offset=${offset}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async getProject(id: number): Promise<FazProject> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async createProject(name: string, prompt: string, preferences?: Record<string, unknown>): Promise<FazProject> {
    const res = await fetch(`${FAZ_API_URL}/projects`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ name, prompt, design_preferences: preferences }),
    });
    return handleResponse(res);
  },

  async deleteProject(id: number): Promise<void> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      let detail = '';
      try {
        const body = await res.json();
        detail = body.detail || body.message || JSON.stringify(body);
      } catch {
        detail = await res.text();
      }
      const prefix = `Failed to delete project (${res.status})`;
      throw new Error(detail ? `${prefix}: ${detail}` : prefix);
    }
  },

  // Pipeline
  async runPipeline(id: number, prompt?: string, startAgent: string = 'nicole', force: boolean = false): Promise<void> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/run`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ prompt, start_agent: startAgent, force }),
    });
    if (!res.ok) {
      let detail = '';
      try {
        const body = await res.json();
        detail = body.detail || body.message || JSON.stringify(body);
      } catch {
        detail = await res.text();
      }
      const prefix = `Failed to run pipeline (${res.status})`;
      throw new Error(detail ? `${prefix}: ${detail}` : prefix);
    }
  },

  async stopPipeline(id: number): Promise<void> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/stop`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      let detail = '';
      try {
        const body = await res.json();
        detail = body.detail || body.message || JSON.stringify(body);
      } catch {
        detail = await res.text();
      }
      const prefix = `Failed to stop pipeline (${res.status})`;
      throw new Error(detail ? `${prefix}: ${detail}` : prefix);
    }
  },

  // Files
  async getFiles(id: number): Promise<FazFile[]> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/files`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async getFile(projectId: number, fileId: number): Promise<FazFile> {
    const res = await fetch(`${FAZ_API_URL}/projects/${projectId}/files/${fileId}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async updateFile(projectId: number, fileId: number, content: string): Promise<FazFile> {
    const res = await fetch(`${FAZ_API_URL}/projects/${projectId}/files/${fileId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({ content }),
    });
    return handleResponse(res);
  },

  async updateFileByPath(projectId: number, path: string, content: string): Promise<{ success: boolean; file_id: number; path: string; version: number }> {
    const res = await fetch(`${FAZ_API_URL}/projects/${projectId}/files/by-path?path=${encodeURIComponent(path)}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify({ content }),
    });
    return handleResponse(res);
  },

  // Activities
  async getActivities(id: number, limit = 50, afterId?: number): Promise<FazActivity[]> {
    let url = `${FAZ_API_URL}/projects/${id}/activities?limit=${limit}`;
    if (afterId) url += `&after_id=${afterId}`;
    
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // Chat
  async getChatHistory(id: number, limit = 50): Promise<ChatMessage[]> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/chat?limit=${limit}`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  async sendChatMessage(id: number, message: string): Promise<ChatMessage> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/chat`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ project_id: id, message }),
    });
    return handleResponse(res);
  },

  // Architecture
  async getArchitecture(id: number): Promise<Architecture> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/architecture`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },

  // Deploy
  async deployProject(id: number): Promise<{ 
    success: boolean; 
    message?: string;
    preview_url?: string;
    production_url?: string;
    github_repo?: string;
  }> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/deploy`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({ message: 'Deployment failed' }));
      throw new Error(error.detail || error.message || 'Failed to deploy project');
    }
    return res.json();
  },

  // Image Upload
  async uploadReferenceImages(projectId: number, files: File[]): Promise<{
    success: boolean;
    images: Array<{
      image_id: number;
      filename: string;
      url: string;
      width?: number;
      height?: number;
    }>;
    message: string;
  }> {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    // Get auth headers but remove Content-Type (let browser set for multipart)
    const headers = getAuthHeaders();
    delete (headers as Record<string, string>)['Content-Type'];
    
    const res = await fetch(`${FAZ_API_URL}/projects/${projectId}/upload-images`, {
      method: 'POST',
      headers,
      body: formData,
    });
    return handleResponse(res);
  },

  async getReferenceImages(projectId: number): Promise<{
    images: Array<{
      image_id: number;
      filename: string;
      url: string;
      width?: number;
      height?: number;
      created_at?: string;
    }>;
  }> {
    const res = await fetch(`${FAZ_API_URL}/projects/${projectId}/reference-images`, {
      headers: getAuthHeaders(),
    });
    return handleResponse(res);
  },
};

