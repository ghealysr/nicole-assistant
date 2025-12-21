/**
 * Enjineer Type Definitions
 * Shared types for the AI-powered development environment
 */

// ============================================================================
// Core Entities
// ============================================================================

export interface EnjineerProject {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  tech_stack: Record<string, unknown>;
  status: 'active' | 'paused' | 'completed' | 'abandoned';
  conversation_id: string | null;
  intake_data: Record<string, unknown>;
  settings: ProjectSettings;
  created_at: string;
  updated_at: string;
}

export interface ProjectSettings {
  vercel_token?: string;
  github_repo?: string;
  budget_limit?: number;
  total_spent?: number;
  theme?: 'dark' | 'light';
}

export interface EnjineerPlan {
  id: string;
  project_id: string;
  version: string;
  content: string;
  status: 'draft' | 'awaiting_approval' | 'approved' | 'in_progress' | 'completed' | 'abandoned';
  current_phase_number: number;
  created_at: string;
  approved_at: string | null;
  completed_at: string | null;
  phases?: EnjineerPlanPhase[];
}

export interface EnjineerPlanPhase {
  id: string;
  plan_id: string;
  phase_number: number;
  name: string;
  status: 'pending' | 'in_progress' | 'complete' | 'blocked' | 'skipped';
  estimated_minutes: number | null;
  actual_minutes: number | null;
  agents_required: string[];
  qa_depth: 'light' | 'standard' | 'thorough';
  qa_focus: string[];
  requires_approval: boolean;
  approval_status: 'pending' | 'approved' | 'changes_requested' | null;
  started_at: string | null;
  completed_at: string | null;
  approved_at: string | null;
  notes: string | null;
}

export interface EnjineerFile {
  id: string;
  project_id: string;
  path: string;
  content: string;
  language: string;
  version: number;
  modified_by: string | null;
  locked_by: string | null;
  lock_expires_at: string | null;
  checksum: string | null;
  created_at: string;
  updated_at: string;
}

export interface EnjineerFileVersion {
  id: string;
  file_id: string;
  version: number;
  content: string;
  modified_by: string;
  diff_from_previous: string | null;
  commit_message: string | null;
  created_at: string;
}

// ============================================================================
// Plan Steps (for UI display)
// ============================================================================

export interface EnjineerPlanStep {
  id: string;
  phase_number: number;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  agents?: string[];
  estimated_minutes?: number;
}

// ============================================================================
// Messages & Chat
// ============================================================================

export interface EnjineerMessage {
  id: string;
  project_id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  attachments?: MessageAttachment[];
  metadata?: MessageMetadata;
  timestamp: string;
  isStreaming?: boolean;
}

export interface MessageAttachment {
  type: 'file' | 'image' | 'url';
  path?: string;
  url?: string;
  name?: string;
}

export interface MessageMetadata {
  tool_use?: ToolUseInfo[];
  thinking?: string;
  agent_status?: AgentStatus;
  approval_id?: string;
  qa_report_id?: string;
}

export interface ToolUseInfo {
  tool_name: string;
  input: Record<string, unknown>;
  output?: unknown;
  status: 'pending' | 'running' | 'complete' | 'error';
}

// ============================================================================
// Agents
// ============================================================================

export type AgentType = 'nicole' | 'qa' | 'engineer' | 'sr_qa';

export interface AgentStatus {
  agent_type: AgentType;
  status: 'idle' | 'pending' | 'running' | 'success' | 'failed';
  progress?: number;
  current_task?: string;
  execution_id?: string;
}

export interface AgentExecution {
  id: string;
  project_id: string;
  plan_id: string | null;
  phase_number: number | null;
  agent_type: AgentType;
  instruction: string;
  context: Record<string, unknown>;
  focus_areas: string[];
  status: 'pending' | 'running' | 'success' | 'partial' | 'failed' | 'cancelled';
  result: Record<string, unknown> | null;
  error_message: string | null;
  tokens_input: number;
  tokens_output: number;
  cost_usd: number;
  duration_seconds: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface AgentRequest {
  agent_type: AgentType;
  instruction: string;
  context?: Record<string, unknown>;
  focus_areas?: string[];
  files_to_include?: string[];
  return_format?: 'report' | 'code' | 'analysis';
  timeout_seconds?: number;
}

// ============================================================================
// Approvals
// ============================================================================

export type ApprovalType = 'plan' | 'phase' | 'agent' | 'deploy' | 'destructive' | 'qa_override';

export interface EnjineerApproval {
  id: string;
  project_id: string;
  approval_type: ApprovalType;
  reference_type: string | null;
  reference_id: string | null;
  title: string;
  description: string | null;
  context: Record<string, unknown>;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  requested_at: string;
  expires_at: string | null;
  responded_at: string | null;
  response_note: string | null;
}

// ============================================================================
// QA
// ============================================================================

export interface QACheck {
  category: string;
  status: 'pass' | 'fail' | 'warn' | 'skip';
  message: string;
  file: string | null;
  line: number | null;
  column: number | null;
  severity: 'critical' | 'warning' | 'info';
  suggestion: string | null;
  code_snippet: string | null;
  screenshot_url: string | null;
}

export interface QAReport {
  id: string;
  project_id: string;
  execution_id: string | null;
  plan_id: string | null;
  phase_number: number | null;
  trigger_type: 'phase_complete' | 'manual' | 'pre_deploy' | 'scheduled';
  qa_depth: 'light' | 'standard' | 'thorough';
  overall_status: 'pass' | 'fail' | 'partial';
  checks: QACheck[];
  summary: string | null;
  blocking_issues_count: number;
  warnings_count: number;
  passed_count: number;
  screenshots: string[];
  duration_seconds: number | null;
  created_at: string;
}

// ============================================================================
// Deployments
// ============================================================================

export interface EnjineerDeployment {
  id: string;
  project_id: string;
  platform: 'vercel' | 'digitalocean' | 'other';
  platform_deployment_id: string | null;
  environment: 'preview' | 'staging' | 'production';
  url: string | null;
  status: 'pending' | 'building' | 'deploying' | 'success' | 'failed' | 'cancelled';
  build_log: string | null;
  error_message: string | null;
  commit_sha: string | null;
  duration_seconds: number | null;
  deployed_at: string | null;
  created_at: string;
}

// ============================================================================
// Assets
// ============================================================================

export interface EnjineerAsset {
  id: string;
  project_id: string;
  asset_type: 'inspiration' | 'generated' | 'screenshot' | 'reference';
  url: string;
  thumbnail_url: string | null;
  description: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

export interface CreateProjectRequest {
  name: string;
  description?: string;
  tech_stack?: Record<string, unknown>;
  intake_data?: Record<string, unknown>;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  status?: 'active' | 'paused' | 'completed' | 'abandoned';
  settings?: Partial<ProjectSettings>;
}

export interface CreateFileRequest {
  path: string;
  content: string;
  language?: string;
}

export interface UpdateFileRequest {
  content: string;
  commit_message?: string;
}

export interface SendMessageRequest {
  message: string;
  attachments?: MessageAttachment[];
}

export interface GeneratePlanRequest {
  intent: string;
  inspiration_urls?: string[];
  requirements?: string[];
  tech_preferences?: Record<string, unknown>;
}

export interface RunQARequest {
  phase_number?: number;
  depth?: 'light' | 'standard' | 'thorough';
  focus_areas?: string[];
  files?: string[];
}

export interface DeployRequest {
  platform: 'vercel' | 'digitalocean';
  environment?: 'preview' | 'staging' | 'production';
}

// ============================================================================
// SSE Event Types
// ============================================================================

export type SSEEventType = 
  | 'thinking'
  | 'text'
  | 'code'
  | 'tool_use'
  | 'tool_result'
  | 'approval_required'
  | 'agent_status'
  | 'file_created'
  | 'file_updated'
  | 'error'
  | 'done';

export interface SSEEvent {
  type: SSEEventType;
  data: unknown;
}

// ============================================================================
// WebSocket Event Types
// ============================================================================

export type WSEventType =
  | 'file_created'
  | 'file_updated'
  | 'file_deleted'
  | 'file_locked'
  | 'file_unlocked'
  | 'agent_status_update'
  | 'agent_output'
  | 'agent_complete'
  | 'approval_new'
  | 'approval_resolved'
  | 'preview_refresh'
  | 'preview_error'
  | 'console_log';

export interface WSEvent {
  type: WSEventType;
  data: unknown;
  timestamp: string;
}

