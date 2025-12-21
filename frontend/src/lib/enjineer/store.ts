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
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'complete' | 'skipped';
  files?: string[];
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
  
  // Chat with Nicole
  messages: ChatMessage[];
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  clearMessages: () => void;
  isNicoleThinking: boolean;
  setNicoleThinking: (thinking: boolean) => void;
  
  // Plan
  plan: PlanStep[];
  setPlan: (plan: PlanStep[]) => void;
  updatePlanStep: (id: string, updates: Partial<PlanStep>) => void;
  
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
  setPlan: (plan) => set({ plan }),
  updatePlanStep: (id, updates) => set((state) => ({
    plan: state.plan.map(s => 
      s.id === id ? { ...s, ...updates } : s
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
}));

