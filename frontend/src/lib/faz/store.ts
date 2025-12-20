import { create } from 'zustand';
import { FazProject, FazFile, FazActivity, ChatMessage, PipelineMode } from '@/types/faz';

/**
 * Artifact for approval gate display
 */
export interface GateArtifact {
  artifact_type: string;
  title: string;
  content: string;
  is_approved?: boolean;
}

interface FazStore {
  // Projects
  projects: FazProject[];
  currentProject: FazProject | null;
  setCurrentProject: (project: FazProject | null) => void;
  updateCurrentProject: (updates: Partial<FazProject>) => void;
  setProjects: (projects: FazProject[]) => void;
  
  // Files
  files: FazFile[];
  fileMetadata: Map<string, FazFile>; // path -> metadata
  selectedFile: string | null;
  selectFile: (path: string | null) => void;
  setFiles: (files: FazFile[]) => void;
  updateFile: (path: string, content: string) => void;
  addFile: (file: FazFile) => void;
  
  // Activities
  activities: FazActivity[];
  addActivity: (activity: FazActivity) => void;
  updateActivity: (activityId: number, updates: Partial<FazActivity>) => void;
  setActivities: (activities: FazActivity[]) => void;
  
  // Chat
  messages: ChatMessage[];
  addMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  
  // Approval Gates (Interactive Pipeline)
  currentGate: string | null;
  gateArtifacts: GateArtifact[];
  setCurrentGate: (gate: string | null) => void;
  setGateArtifacts: (artifacts: GateArtifact[]) => void;
  addGateArtifact: (artifact: GateArtifact) => void;
  clearGate: () => void;
  
  // Pipeline Mode
  pipelineMode: PipelineMode;
  setPipelineMode: (mode: PipelineMode) => void;
  
  // UI State
  previewMode: 'mobile' | 'tablet' | 'desktop';
  setPreviewMode: (mode: 'mobile' | 'tablet' | 'desktop') => void;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  activeTab: 'code' | 'preview' | 'split';
  setActiveTab: (tab: 'code' | 'preview' | 'split') => void;
  
  // Loading & Error State
  isLoading: boolean;
  setLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
  clearError: () => void;
  
  // Deploy State
  isDeploying: boolean;
  deployProgress: string | null;
  setDeploying: (deploying: boolean) => void;
  setDeployProgress: (progress: string | null) => void;
  
  // Reset
  reset: () => void;
}

const initialState = {
  projects: [] as FazProject[],
  currentProject: null as FazProject | null,
  files: [] as FazFile[],
  fileMetadata: new Map<string, FazFile>(),
  selectedFile: null as string | null,
  activities: [] as FazActivity[],
  messages: [] as ChatMessage[],
  currentGate: null as string | null,
  gateArtifacts: [] as GateArtifact[],
  pipelineMode: 'interactive' as PipelineMode,
  previewMode: 'desktop' as 'mobile' | 'tablet' | 'desktop',
  isSidebarOpen: true,
  activeTab: 'split' as 'code' | 'preview' | 'split',
  isLoading: false,
  error: null as string | null,
  isDeploying: false,
  deployProgress: null as string | null,
};

export const useFazStore = create<FazStore>((set) => ({
  ...initialState,
  
  // Projects
  setCurrentProject: (project) => set({ currentProject: project }),
  updateCurrentProject: (updates) => set((state) => ({
    currentProject: state.currentProject 
      ? { ...state.currentProject, ...updates }
      : null
  })),
  setProjects: (projects) => set({ projects }),
  
  // Files
  selectFile: (path) => set({ selectedFile: path }),
  setFiles: (filesList) => set((state) => {
    const newMetadata = new Map(state.fileMetadata);
    
    filesList.forEach(f => {
      newMetadata.set(f.path, f);
    });
    
    // Select first file if none selected
    let selected = state.selectedFile;
    if (!selected && filesList.length > 0) {
      // Prefer page.tsx or layout.tsx
      const preferred = filesList.find(f => f.path.includes('page.tsx')) || filesList[0];
      selected = preferred.path;
    }
    
    return { 
      files: filesList, 
      fileMetadata: newMetadata,
      selectedFile: selected
    };
  }),
  updateFile: (path, content) => set((state) => {
    const newFiles = state.files.map(f => 
      f.path === path ? { ...f, content } : f
    );
    return { files: newFiles };
  }),
  addFile: (file) => set((state) => {
    // Check if file already exists
    const existing = state.files.find(f => f.path === file.path);
    const newMetadata = new Map(state.fileMetadata);
    newMetadata.set(file.path, file);
    
    if (existing) {
      return {
        files: state.files.map(f => f.path === file.path ? file : f),
        fileMetadata: newMetadata,
      };
    }
    
    return { 
      files: [...state.files, file],
      fileMetadata: newMetadata,
    };
  }),
  
  // Activities
  addActivity: (activity) => set((state) => {
    // Avoid duplicates
    if (state.activities.some(a => a.activity_id === activity.activity_id)) {
      // Update existing activity
      return {
        activities: state.activities.map(a => 
          a.activity_id === activity.activity_id ? { ...a, ...activity } : a
        )
      };
    }
    return { activities: [activity, ...state.activities] };
  }),
  updateActivity: (activityId, updates) => set((state) => ({
    activities: state.activities.map(a =>
      a.activity_id === activityId ? { ...a, ...updates } : a
    )
  })),
  setActivities: (activities) => set({ activities }),
  
  // Chat
  addMessage: (message) => set((state) => ({ 
    messages: [...state.messages, message] 
  })),
  setMessages: (messages) => set({ messages }),
  
  // Approval Gates
  setCurrentGate: (gate) => set({ currentGate: gate }),
  setGateArtifacts: (artifacts) => set({ gateArtifacts: artifacts }),
  addGateArtifact: (artifact) => set((state) => {
    // Replace if same type exists
    const existing = state.gateArtifacts.findIndex(a => a.artifact_type === artifact.artifact_type);
    if (existing >= 0) {
      const newArtifacts = [...state.gateArtifacts];
      newArtifacts[existing] = artifact;
      return { gateArtifacts: newArtifacts };
    }
    return { gateArtifacts: [...state.gateArtifacts, artifact] };
  }),
  clearGate: () => set({ currentGate: null, gateArtifacts: [] }),
  
  // Pipeline Mode
  setPipelineMode: (mode) => set({ pipelineMode: mode }),
  
  // UI State
  setPreviewMode: (mode) => set({ previewMode: mode }),
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setActiveTab: (tab) => set({ activeTab: tab }),
  
  // Loading & Error State
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),
  
  // Deploy State
  setDeploying: (deploying) => set({ isDeploying: deploying }),
  setDeployProgress: (progress) => set({ deployProgress: progress }),
  
  // Reset
  reset: () => set(initialState),
}));

