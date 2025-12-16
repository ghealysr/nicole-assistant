import { create } from 'zustand';
import { FazProject, FazFile, FazActivity, ChatMessage } from '@/types/faz';

interface FazStore {
  // Projects
  projects: FazProject[];
  currentProject: FazProject | null;
  setCurrentProject: (project: FazProject | null) => void;
  setProjects: (projects: FazProject[]) => void;
  
  // Files
  files: Map<string, string>; // path -> content
  fileMetadata: Map<string, FazFile>; // path -> metadata
  selectedFile: string | null;
  selectFile: (path: string | null) => void;
  setFiles: (files: FazFile[]) => void;
  updateFile: (path: string, content: string) => void;
  addFile: (file: FazFile) => void;
  
  // Activities
  activities: FazActivity[];
  addActivity: (activity: FazActivity) => void;
  setActivities: (activities: FazActivity[]) => void;
  
  // Chat
  messages: ChatMessage[];
  addMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  
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
}

export const useFazStore = create<FazStore>((set) => ({
  // Projects
  projects: [],
  currentProject: null,
  setCurrentProject: (project) => set({ currentProject: project }),
  setProjects: (projects) => set({ projects }),
  
  // Files
  files: new Map(),
  fileMetadata: new Map(),
  selectedFile: null,
  selectFile: (path) => set({ selectedFile: path }),
  setFiles: (filesList) => set((state) => {
    const newFiles = new Map(state.files);
    const newMetadata = new Map(state.fileMetadata);
    
    filesList.forEach(f => {
      newFiles.set(f.path, f.content);
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
      files: newFiles, 
      fileMetadata: newMetadata,
      selectedFile: selected
    };
  }),
  updateFile: (path, content) => set((state) => {
    const newFiles = new Map(state.files);
    newFiles.set(path, content);
    return { files: newFiles };
  }),
  addFile: (file) => set((state) => {
    const newFiles = new Map(state.files);
    const newMetadata = new Map(state.fileMetadata);
    newFiles.set(file.path, file.content);
    newMetadata.set(file.path, file);
    return { files: newFiles, fileMetadata: newMetadata };
  }),
  
  // Activities
  activities: [],
  addActivity: (activity) => set((state) => {
    // Avoid duplicates
    if (state.activities.some(a => a.activity_id === activity.activity_id)) {
      return {};
    }
    return { activities: [activity, ...state.activities] };
  }),
  setActivities: (activities) => set({ activities }),
  
  // Chat
  messages: [],
  addMessage: (message) => set((state) => ({ 
    messages: [...state.messages, message] 
  })),
  setMessages: (messages) => set({ messages }),
  
  // UI State
  previewMode: 'desktop',
  setPreviewMode: (mode) => set({ previewMode: mode }),
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  activeTab: 'split',
  setActiveTab: (tab) => set({ activeTab: tab }),
  
  // Loading & Error State
  isLoading: false,
  setLoading: (loading) => set({ isLoading: loading }),
  error: null,
  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),
  
  // Deploy State
  isDeploying: false,
  deployProgress: null,
  setDeploying: (deploying) => set({ isDeploying: deploying }),
  setDeployProgress: (progress) => set({ deployProgress: progress }),
}));

