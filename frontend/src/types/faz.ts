export type ProjectStatus = 
  | 'intake' 
  | 'planning' 
  | 'researching' 
  | 'designing' 
  | 'building' 
  | 'processing' 
  | 'qa' 
  | 'review' 
  | 'approved' 
  | 'deploying' 
  | 'deployed' 
  | 'failed' 
  | 'paused'
  | 'archived';

export interface FazProject {
  project_id: number;
  name: string;
  slug: string;
  status: ProjectStatus;
  original_prompt: string;
  current_agent?: string | null;
  file_count: number;
  total_tokens_used: number;
  total_cost_cents: number;
  created_at: string;
  updated_at: string;
  preview_url?: string;
  production_url?: string;
  github_repo?: string;
  vercel_project_id?: string;
  architecture?: Architecture;
  design_tokens?: DesignSystem;
}

export interface FazFile {
  file_id: number;
  path: string;
  filename: string;
  extension: string;
  content: string;
  file_type: 'component' | 'page' | 'config' | 'style' | 'asset' | 'unknown';
  line_count: number;
  generated_by?: string;
  version: number;
  status: 'generated' | 'modified' | 'approved' | 'error' | 'deleted';
  created_at: string;
}

export interface FazActivity {
  activity_id: number;
  agent_name: string;
  agent_model: string;
  activity_type: string; // 'route', 'analyze', 'generate', 'review', etc.
  message: string;
  content_type: 'status' | 'thinking' | 'response' | 'tool_call' | 'error';
  full_content?: string;
  details?: Record<string, unknown>;
  input_tokens: number;
  output_tokens: number;
  cost_cents: number;
  status: 'running' | 'complete' | 'error' | 'cancelled';
  started_at: string;
  completed_at?: string;
}

export interface ChatMessage {
  message_id?: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  agent_name?: string;
  model_used?: string;
  created_at: string;
}

export interface DesignSystem {
  colors: Record<string, string>;
  typography: {
    heading_font: string;
    body_font: string;
    base_size: string;
  };
  spacing: Record<string, string>;
}

export interface Architecture {
  project_summary: {
    name: string;
    description: string;
    target_audience: string;
  };
  tech_stack: {
    framework: string;
    styling: string;
  };
  pages: Array<{
    path: string;
    name: string;
    components: string[];
  }>;
  components: Array<{
    name: string;
    type: string;
    description: string;
  }>;
  design_tokens?: DesignSystem;
  file_structure: string[];
}

