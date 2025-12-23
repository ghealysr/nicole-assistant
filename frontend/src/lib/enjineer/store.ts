/**
 * Enjineer Store - Zustand state management for the Enjineer IDE
 * 
 * This is the central state for the entire Enjineer dashboard:
 * - Project state (files, current project)
 * - Chat messages with Nicole
 * - UI state (active panels, tabs, preview mode)
 * - Agent activity tracking
 * - Terminal output
 */

import { create } from 'zustand';

// Types
export interface EnjineerFile {
  path: string;
  content: string;
  language: string;
  isModified: boolean;
  lastSaved?: Date;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
}

export interface ToolCall {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'complete' | 'error';
  result?: string;
}

export interface AgentTask {
  id: string;
  agent: 'engineer' | 'qa' | 'sr_qa';
  task: string;
  status: 'queued' | 'running' | 'complete' | 'error';
  startedAt?: Date;
  completedAt?: Date;
  result?: string;
}

export interface PlanStep {
  id: string;
  phaseNumber: number;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'complete' | 'skipped' | 'awaiting_approval';
  files?: string[];
  // Enhanced fields from backend
  estimatedMinutes?: number;
  actualMinutes?: number;
  agentsRequired?: ('engineer' | 'qa' | 'sr_qa')[];
  requiresApproval?: boolean;
  approvalStatus?: 'pending' | 'approved' | 'rejected' | null;
  qaDepth?: 'basic' | 'standard' | 'thorough';
  qaFocus?: string[];
  startedAt?: Date;
  completedAt?: Date;
  approvedAt?: Date;
  notes?: string;
}

export interface PlanOverview {
  id: string;
  version: number;
  status: 'planning' | 'awaiting_approval' | 'active' | 'paused' | 'completed' | 'abandoned';
  currentPhaseNumber: number;
  totalPhases: number;
  completedPhases: number;
  createdAt: Date;
  approvedAt?: Date;
  completedAt?: Date;
}

export interface Project {
  id: number;
  name: string;
  description?: string;
  status: string;
  createdAt: Date;
  updatedAt: Date;
}

export type MainTab = 'code' | 'preview' | 'terminal';
export type SidebarTab = 'files' | 'plan';
export type PreviewMode = 'mobile' | 'tablet' | 'desktop';

interface EnjineerStore {
  // Project
  currentProject: Project | null;
  setCurrentProject: (project: Project | null) => void;
  
  // Files
  files: Map<string, EnjineerFile>;
  selectedFile: string | null;
  openFiles: string[]; // Tabs
  setFiles: (files: EnjineerFile[]) => void;
  addFile: (file: EnjineerFile) => void;
  updateFile: (path: string, content: string) => void;
  selectFile: (path: string | null) => void;
  openFile: (path: string) => void;
  closeFile: (path: string) => void;
  deleteFile: (path: string) => void;
  renameFile: (oldPath: string, newPath: string) => void;
  
  // Chat with Nicole
  messages: ChatMessage[];
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  clearMessages: () => void;
  isNicoleThinking: boolean;
  setNicoleThinking: (thinking: boolean) => void;
  
  // Plan
  plan: PlanStep[];
  planOverview: PlanOverview | null;
  currentPhaseId: string | null;
  setPlan: (plan: PlanStep[]) => void;
  setPlanOverview: (overview: PlanOverview | null) => void;
  updatePlanStep: (id: string, updates: Partial<PlanStep>) => void;
  setCurrentPhase: (phaseId: string | null) => void;
  markPhaseComplete: (phaseId: string) => void;
  requestPhaseApproval: (phaseId: string) => void;
  
  // Agent Tasks
  agentTasks: AgentTask[];
  addAgentTask: (task: AgentTask) => void;
  updateAgentTask: (id: string, updates: Partial<AgentTask>) => void;
  
  // Terminal
  terminalOutput: string[];
  addTerminalLine: (line: string) => void;
  clearTerminal: () => void;
  
  // UI State
  mainTab: MainTab;
  setMainTab: (tab: MainTab) => void;
  sidebarTab: SidebarTab;
  setSidebarTab: (tab: SidebarTab) => void;
  previewMode: PreviewMode;
  setPreviewMode: (mode: PreviewMode) => void;
  isSidebarCollapsed: boolean;
  toggleSidebar: () => void;
  isChatCollapsed: boolean;
  toggleChat: () => void;
  
  // Loading & Error
  isLoading: boolean;
  setLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
  
  // Preview refresh trigger - increment to force preview refresh
  previewRefreshTrigger: number;
  triggerPreviewRefresh: () => void;
}

export const useEnjineerStore = create<EnjineerStore>((set) => ({
  // Project
  currentProject: null,
  setCurrentProject: (project) => set({ currentProject: project }),
  
  // Files
  files: new Map(),
  selectedFile: null,
  openFiles: [],
  setFiles: (filesList) => {
    const filesMap = new Map<string, EnjineerFile>();
    filesList.forEach(f => filesMap.set(f.path, f));
    set({ files: filesMap });
  },
  addFile: (file) => set((state) => {
    const newFiles = new Map(state.files);
    newFiles.set(file.path, file);
    return { files: newFiles };
  }),
  updateFile: (path, content) => set((state) => {
    const newFiles = new Map(state.files);
    const existing = newFiles.get(path);
    if (existing) {
      newFiles.set(path, { ...existing, content, isModified: true });
    }
    return { files: newFiles };
  }),
  selectFile: (path) => set({ selectedFile: path }),
  openFile: (path) => set((state) => {
    if (!state.openFiles.includes(path)) {
      return { openFiles: [...state.openFiles, path], selectedFile: path };
    }
    return { selectedFile: path };
  }),
  closeFile: (path) => set((state) => {
    const newOpenFiles = state.openFiles.filter(f => f !== path);
    const newSelected = state.selectedFile === path 
      ? (newOpenFiles[newOpenFiles.length - 1] || null)
      : state.selectedFile;
    return { openFiles: newOpenFiles, selectedFile: newSelected };
  }),
  deleteFile: (path) => set((state) => {
    const newFiles = new Map(state.files);
    newFiles.delete(path);
    const newOpenFiles = state.openFiles.filter(f => f !== path);
    const newSelected = state.selectedFile === path 
      ? (newOpenFiles[newOpenFiles.length - 1] || null)
      : state.selectedFile;
    return { files: newFiles, openFiles: newOpenFiles, selectedFile: newSelected };
  }),
  renameFile: (oldPath, newPath) => set((state) => {
    const newFiles = new Map(state.files);
    const file = newFiles.get(oldPath);
    if (file) {
      newFiles.delete(oldPath);
      newFiles.set(newPath, { ...file, path: newPath });
    }
    const newOpenFiles = state.openFiles.map(f => f === oldPath ? newPath : f);
    const newSelected = state.selectedFile === oldPath ? newPath : state.selectedFile;
    return { files: newFiles, openFiles: newOpenFiles, selectedFile: newSelected };
  }),
  
  // Chat
  messages: [],
  addMessage: (message) => set((state) => ({ 
    messages: [...state.messages, message] 
  })),
  updateMessage: (id, updates) => set((state) => ({
    messages: state.messages.map(m => 
      m.id === id ? { ...m, ...updates } : m
    )
  })),
  clearMessages: () => set({ messages: [] }),
  isNicoleThinking: false,
  setNicoleThinking: (thinking) => set({ isNicoleThinking: thinking }),
  
  // Plan
  plan: [],
  planOverview: null,
  currentPhaseId: null,
  setPlan: (plan) => set({ plan }),
  setPlanOverview: (overview) => set({ planOverview: overview }),
  updatePlanStep: (id, updates) => set((state) => ({
    plan: state.plan.map(s => 
      s.id === id ? { ...s, ...updates } : s
    )
  })),
  setCurrentPhase: (phaseId) => set((state) => {
    // Update the current phase and set status to in_progress
    const updatedPlan = state.plan.map(s => {
      if (s.id === phaseId) {
        return { ...s, status: 'in_progress' as const, startedAt: new Date() };
      }
      return s;
    });
    return { currentPhaseId: phaseId, plan: updatedPlan };
  }),
  markPhaseComplete: (phaseId) => set((state) => {
    const updatedPlan = state.plan.map(s => {
      if (s.id === phaseId) {
        return { ...s, status: 'complete' as const, completedAt: new Date() };
      }
      return s;
    });
    // Update overview
    const completedCount = updatedPlan.filter(s => s.status === 'complete').length;
    const updatedOverview = state.planOverview 
      ? { ...state.planOverview, completedPhases: completedCount }
      : null;
    return { plan: updatedPlan, planOverview: updatedOverview };
  }),
  requestPhaseApproval: (phaseId) => set((state) => ({
    plan: state.plan.map(s => 
      s.id === phaseId 
        ? { ...s, status: 'awaiting_approval' as const, approvalStatus: 'pending' as const }
        : s
    )
  })),
  
  // Agent Tasks
  agentTasks: [],
  addAgentTask: (task) => set((state) => ({
    agentTasks: [...state.agentTasks, task]
  })),
  updateAgentTask: (id, updates) => set((state) => ({
    agentTasks: state.agentTasks.map(t =>
      t.id === id ? { ...t, ...updates } : t
    )
  })),
  
  // Terminal
  terminalOutput: [],
  addTerminalLine: (line) => set((state) => ({
    terminalOutput: [...state.terminalOutput, line]
  })),
  clearTerminal: () => set({ terminalOutput: [] }),
  
  // UI State
  mainTab: 'code',
  setMainTab: (tab) => set({ mainTab: tab }),
  sidebarTab: 'files',
  setSidebarTab: (tab) => set({ sidebarTab: tab }),
  previewMode: 'desktop',
  setPreviewMode: (mode) => set({ previewMode: mode }),
  isSidebarCollapsed: false,
  toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
  isChatCollapsed: false,
  toggleChat: () => set((state) => ({ isChatCollapsed: !state.isChatCollapsed })),
  
  // Loading & Error
  isLoading: false,
  setLoading: (loading) => set({ isLoading: loading }),
  error: null,
  setError: (error) => set({ error }),
  
  // Preview refresh
  previewRefreshTrigger: 0,
  triggerPreviewRefresh: () => set((state) => ({ 
    previewRefreshTrigger: state.previewRefreshTrigger + 1 
  })),
}));

