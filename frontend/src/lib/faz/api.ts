import { API_URL } from '@/lib/alphawave_config';
import { getAuthHeaders } from '@/lib/alphawave_utils';
import { FazProject, FazFile, FazActivity, ChatMessage, Architecture } from '@/types/faz';

const FAZ_API_URL = `${API_URL}/faz`;

export const fazApi = {
  // Projects
  async listProjects(limit = 20, offset = 0): Promise<{ projects: FazProject[], total: number }> {
    const res = await fetch(`${FAZ_API_URL}/projects?limit=${limit}&offset=${offset}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to list projects');
    return res.json();
  },

  async getProject(id: number): Promise<FazProject> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get project');
    return res.json();
  },

  async createProject(name: string, prompt: string, preferences?: any): Promise<FazProject> {
    const res = await fetch(`${FAZ_API_URL}/projects`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ name, prompt, design_preferences: preferences }),
    });
    if (!res.ok) throw new Error('Failed to create project');
    return res.json();
  },

  async deleteProject(id: number): Promise<void> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete project');
  },

  // Pipeline
  async runPipeline(id: number, prompt?: string, startAgent: string = 'nicole'): Promise<void> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/run`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ prompt, start_agent: startAgent }),
    });
    if (!res.ok) throw new Error('Failed to run pipeline');
  },

  async stopPipeline(id: number): Promise<void> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/stop`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to stop pipeline');
  },

  // Files
  async getFiles(id: number): Promise<FazFile[]> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/files`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get files');
    return res.json();
  },

  async getFile(projectId: number, fileId: number): Promise<FazFile> {
    const res = await fetch(`${FAZ_API_URL}/projects/${projectId}/files/${fileId}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get file');
    return res.json();
  },

  // Activities
  async getActivities(id: number, limit = 50, afterId?: number): Promise<FazActivity[]> {
    let url = `${FAZ_API_URL}/projects/${id}/activities?limit=${limit}`;
    if (afterId) url += `&after_id=${afterId}`;
    
    const res = await fetch(url, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get activities');
    return res.json();
  },

  // Chat
  async getChatHistory(id: number, limit = 50): Promise<ChatMessage[]> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/chat?limit=${limit}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get chat history');
    return res.json();
  },

  async sendChatMessage(id: number, message: string): Promise<ChatMessage> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/chat`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ project_id: id, message }),
    });
    if (!res.ok) throw new Error('Failed to send message');
    return res.json();
  },

  // Architecture
  async getArchitecture(id: number): Promise<Architecture> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/architecture`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to get architecture');
    return res.json();
  },

  // Deploy
  async deployProject(id: number): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${FAZ_API_URL}/projects/${id}/deploy`, {
      method: 'POST',
      headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error('Failed to deploy project');
    return res.json();
  },
};

