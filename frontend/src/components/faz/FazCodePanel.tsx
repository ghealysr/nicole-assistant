'use client';

/**
 * FAZ CODE V2 - AI-Powered Web Development Dashboard
 * 
 * Major improvements:
 * - Monaco editor with full editing
 * - Live preview that renders generated code
 * - File polling during pipeline (files appear as generated)
 * - Nicole chat integration
 * - QA issue visibility
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  X, Plus, Folder, Play, Square, Loader2, Code2, ChevronRight, ChevronDown,
  Send, Bot, Terminal, Rocket, RefreshCw, Sparkles, Monitor, Tablet, Smartphone,
  BrainCircuit, Search, PenTool, Bug, CheckCircle, Zap, Eye, FileCode,
  AlertCircle, FolderOpen, MessageSquare, Save
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import dynamic from 'next/dynamic';
import { useFazStore } from '@/lib/faz/store';
import { fazApi } from '@/lib/faz/api';
import { fazWS } from '@/lib/faz/websocket';
import { FazLivePreview } from './FazLivePreview';
import { FazProject, FazFile, FazActivity } from '@/types/faz';
import { format } from 'date-fns';

// Dynamic import Monaco to avoid SSR issues
const MonacoEditor = dynamic(
  () => import('@monaco-editor/react').then(mod => mod.default),
  { ssr: false, loading: () => <div className="flex items-center justify-center h-full"><Loader2 className="animate-spin" /></div> }
);

// =============================================================================
// CONSTANTS
// =============================================================================

const AGENT_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  nicole: { icon: <Sparkles size={14} />, color: '#8B5CF6', label: 'Nicole' },
  planning: { icon: <BrainCircuit size={14} />, color: '#3B82F6', label: 'Planning' },
  research: { icon: <Search size={14} />, color: '#10B981', label: 'Research' },
  design: { icon: <PenTool size={14} />, color: '#EC4899', label: 'Design' },
  coding: { icon: <Code2 size={14} />, color: '#F59E0B', label: 'Coding' },
  qa: { icon: <Bug size={14} />, color: '#EF4444', label: 'QA' },
  review: { icon: <CheckCircle size={14} />, color: '#6366F1', label: 'Review' },
  memory: { icon: <Zap size={14} />, color: '#64748B', label: 'Memory' },
};

const PIPELINE_STAGES = ['planning', 'researching', 'designing', 'building', 'qa', 'review', 'approved'];

// =============================================================================
// TYPES
// =============================================================================

interface FazCodePanelProps {
  isOpen: boolean;
  onClose: () => void;
  isFullWidth?: boolean;
}

interface OpenTab {
  path: string;
  content: string;
  language: string;
  isDirty: boolean;
}

// =============================================================================
// COMPONENT
// =============================================================================

export function FazCodePanel({ isOpen, onClose, isFullWidth = false }: FazCodePanelProps) {
  // ===== STATE =====
  const [view, setView] = useState<'projects' | 'workspace'>('projects');
  const [projects, setProjects] = useState<FazProject[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  
  // Project creation
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectPrompt, setNewProjectPrompt] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  
  // Pipeline
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [lastPolledStatus, setLastPolledStatus] = useState<string>('');
  
  // Editor
  const [openTabs, setOpenTabs] = useState<OpenTab[]>([]);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [editedContent, setEditedContent] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  
  // Files
  const [projectFiles, setProjectFiles] = useState<FazFile[]>([]);
  
  // Preview
  const [previewMode, setPreviewMode] = useState<'desktop' | 'tablet' | 'mobile'>('desktop');
  const [showPreview, setShowPreview] = useState(true);
  const [previewKey, setPreviewKey] = useState(0);
  
  // Activity & Chat
  const [activities, setActivities] = useState<FazActivity[]>([]);
  const [activeRightTab, setActiveRightTab] = useState<'activity' | 'chat'>('activity');
  const activityScrollRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);
  
  // Chat
  const [chatMessage, setChatMessage] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  
  // Store
  const { 
    currentProject, setCurrentProject,
    setFiles,
    setActivities: storeSetActivities,
    messages: storeMessages,
    setMessages: storeSetMessages,
  } = useFazStore();

  // ===== HELPER: Get current tab content =====
  const getTabContent = (path: string): string => {
    return editedContent[path] ?? projectFiles.find(f => f.path === path)?.content ?? '';
  };

  // ===== DATA FETCHING =====
  
  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setLoadingError(null);
    try {
      const data = await fazApi.listProjects();
      setProjects(data.projects || []);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
      setLoadingError(error instanceof Error ? error.message : 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAllProjectData = useCallback(async (projectId: number, forceRefresh = false) => {
    try {
      console.log(`[Faz] Fetching all data for project ${projectId}...`);
      
      const [filesData, activitiesData, projectData] = await Promise.all([
        fazApi.getFiles(projectId),
        fazApi.getActivities(projectId),
        fazApi.getProject(projectId),
      ]);
      
      console.log(`[Faz] Received ${filesData?.length || 0} files, ${activitiesData?.length || 0} activities`);
      
      // Update local state
      setProjectFiles(filesData || []);
      setActivities(activitiesData || []);
      storeSetActivities(activitiesData || []);
      
      // Update store with files
      setFiles(filesData || []);
      
      // Update project status
      if (projectData) {
        setCurrentProject(projectData);
        const runningStatuses = ['planning', 'researching', 'designing', 'building', 'qa', 'review', 'deploying'];
        const isRunning = runningStatuses.includes(projectData.status);
        setPipelineRunning(isRunning);
        
        // If status changed from running to not running, force refresh files
        if (lastPolledStatus && runningStatuses.includes(lastPolledStatus) && !isRunning) {
          console.log('[Faz] Pipeline completed, refreshing files...');
          const freshFiles = await fazApi.getFiles(projectId);
          setProjectFiles(freshFiles || []);
          setFiles(freshFiles || []);
        }
        setLastPolledStatus(projectData.status);
      }
      
      // Auto-open first file if none open
      if ((filesData && filesData.length > 0) && (forceRefresh || openTabs.length === 0)) {
        const preferred = filesData.find(f => f.path.includes('page.tsx')) || 
                         filesData.find(f => f.path.includes('layout.tsx')) ||
                         filesData[0];
        if (preferred) {
          // Inline openFile logic to avoid dependency issue
          const ext = preferred.path.split('.').pop()?.toLowerCase();
          const langMap: Record<string, string> = {
            tsx: 'typescript', ts: 'typescript', jsx: 'javascript', js: 'javascript',
            css: 'css', json: 'json', md: 'markdown', html: 'html',
          };
          setOpenTabs(prev => {
            if (prev.find(t => t.path === preferred.path)) return prev;
            return [...prev, { path: preferred.path, content: preferred.content, language: langMap[ext || ''] || 'plaintext', isDirty: false }];
          });
          setActiveTab(preferred.path);
        }
      }
      
      // Refresh preview when files change
      setPreviewKey(k => k + 1);
      
    } catch (error) {
      console.error('Failed to fetch project data:', error);
    }
  }, [setFiles, storeSetActivities, lastPolledStatus, openTabs.length, setCurrentProject]);

  // ===== EFFECTS =====
  
  useEffect(() => {
    if (isOpen && view === 'projects') {
      fetchProjects();
    }
  }, [isOpen, view, fetchProjects]);

  // Poll for updates while pipeline is running OR just completed
  useEffect(() => {
    if (!currentProject || view !== 'workspace') return;
    
    // Always poll while running
    if (pipelineRunning) {
      pollRef.current = setInterval(() => {
        fetchAllProjectData(currentProject.project_id);
      }, 2500);
      
      return () => {
        if (pollRef.current) clearInterval(pollRef.current);
      };
    }
    
    // One final poll after pipeline stops (to get final state)
    fetchAllProjectData(currentProject.project_id, true);
    
  }, [currentProject, view, pipelineRunning, fetchAllProjectData]);

  useEffect(() => {
    if (activityScrollRef.current && activities.length > 0) {
      activityScrollRef.current.scrollTop = 0;
    }
  }, [activities]);

  // WebSocket connection
  useEffect(() => {
    if (currentProject && view === 'workspace') {
      fazWS.connect(currentProject.project_id);
      return () => fazWS.disconnect();
    }
  }, [currentProject, view]);

  // ===== HANDLERS =====
  
  const handleCreateProject = async () => {
    if (!newProjectName.trim() || !newProjectPrompt.trim()) return;
    
    setCreating(true);
    setCreateError(null);
    try {
      const project = await fazApi.createProject(newProjectName, newProjectPrompt);
      setProjects(prev => [project, ...prev]);
      setNewProjectName('');
      setNewProjectPrompt('');
      handleSelectProject(project);
    } catch (error) {
      console.error('Failed to create project:', error);
      setCreateError(error instanceof Error ? error.message : 'Could not create project');
    } finally {
      setCreating(false);
    }
  };

  const handleSelectProject = async (project: FazProject) => {
    setCurrentProject(project);
    setView('workspace');
    setActivities([]);
    setOpenTabs([]);
    setActiveTab(null);
    setProjectFiles([]);
    storeSetMessages([]); // Clear previous messages
    
    // Connect WebSocket for real-time updates
    fazWS.connect(project.project_id);
    
    // Load chat history
    try {
      const chatHistory = await fazApi.getChatHistory(project.project_id);
      storeSetMessages(chatHistory);
    } catch (err) {
      console.error('[Faz] Failed to load chat history:', err);
    }
    setEditedContent({});
    
    const runningStatuses = ['planning', 'researching', 'designing', 'building', 'qa', 'review', 'deploying'];
    setPipelineRunning(runningStatuses.includes(project.status));
    setLastPolledStatus(project.status);
    
    // Fetch all data
    await fetchAllProjectData(project.project_id, true);
  };

  const handleBackToProjects = () => {
    setView('projects');
    setCurrentProject(null);
    setActivities([]);
    setOpenTabs([]);
    setActiveTab(null);
    setProjectFiles([]);
    setEditedContent({});
    storeSetMessages([]);
    
    // Disconnect WebSocket
    fazWS.disconnect();
    fazWS.disconnect();
    if (pollRef.current) {
      clearInterval(pollRef.current);
    }
  };

  const handleRunPipeline = async () => {
    if (!currentProject) return;
    
    setPipelineRunning(true);
    setPipelineError(null);
    
    try {
      await fazApi.runPipeline(currentProject.project_id);
      // Polling will pick up changes
    } catch (error) {
      console.error('Failed to run pipeline:', error);
      setPipelineError(error instanceof Error ? error.message : 'Failed to start pipeline');
      setPipelineRunning(false);
    }
  };

  const handleStopPipeline = async () => {
    if (!currentProject) return;
    
    try {
      await fazApi.stopPipeline(currentProject.project_id);
      setPipelineRunning(false);
      await fetchAllProjectData(currentProject.project_id, true);
    } catch (error) {
      console.error('Failed to stop pipeline:', error);
    }
  };

  const handleRefresh = async () => {
    if (!currentProject) return;
    await fetchAllProjectData(currentProject.project_id, true);
  };

  const handleSendMessage = async () => {
    if (!currentProject || !chatMessage.trim()) return;
    
    setSendingMessage(true);
    try {
      // Use WebSocket for real-time chat if connected, fallback to API
      if (fazWS.isConnected() && fazWS.isAuthenticated()) {
        fazWS.sendChat(chatMessage);
        setChatMessage('');
      } else {
        // Fallback to HTTP API
        await fazApi.sendChatMessage(currentProject.project_id, chatMessage);
        setChatMessage('');
        await fetchAllProjectData(currentProject.project_id);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setSendingMessage(false);
    }
  };

  const handleDeploy = async () => {
    if (!currentProject) return;
    
    try {
      const result = await fazApi.deployProject(currentProject.project_id);
      if (result.preview_url) {
        window.open(result.preview_url, '_blank');
      }
      await fetchAllProjectData(currentProject.project_id);
    } catch (error) {
      console.error('Deploy failed:', error);
      setPipelineError(error instanceof Error ? error.message : 'Deploy failed');
    }
  };

  const openFile = (file: FazFile) => {
    const existing = openTabs.find(t => t.path === file.path);
    if (!existing) {
      const lang = getLanguage(file.path);
      setOpenTabs(prev => [...prev, { path: file.path, content: file.content, language: lang, isDirty: false }]);
    }
    setActiveTab(file.path);
  };

  const closeTab = (path: string) => {
    setOpenTabs(prev => prev.filter(t => t.path !== path));
    setEditedContent(prev => {
      const next = { ...prev };
      delete next[path];
      return next;
    });
    if (activeTab === path) {
      const remaining = openTabs.filter(t => t.path !== path);
      setActiveTab(remaining.length > 0 ? remaining[remaining.length - 1].path : null);
    }
  };

  const handleEditorChange = (path: string, value: string | undefined) => {
    if (value === undefined) return;
    const originalFile = projectFiles.find(f => f.path === path);
    const isDirty = originalFile?.content !== value;
    
    setEditedContent(prev => ({ ...prev, [path]: value }));
    setOpenTabs(prev => prev.map(t => t.path === path ? { ...t, isDirty } : t));
  };

  const handleSaveFile = async (path: string) => {
    if (!currentProject) return;
    
    setSaving(true);
    try {
      const content = editedContent[path];
      if (content === undefined) return;
      
      // Find file ID from project files
      const file = projectFiles.find(f => f.path === path);
      if (file?.file_id) {
        // Use file ID update endpoint
        await fazApi.updateFile(currentProject.project_id, file.file_id, content);
      } else {
        // Fallback to path-based update
        await fazApi.updateFileByPath(currentProject.project_id, path, content);
      }
      
      // Update local state
      setOpenTabs(prev => prev.map(t => t.path === path ? { ...t, isDirty: false, content } : t));
      setEditedContent(prev => {
        const next = { ...prev };
        delete next[path];
        return next;
      });
      
      // Update project files array
      setProjectFiles(prev => prev.map(f => 
        f.path === path ? { ...f, content, version: (f.version || 1) + 1 } : f
      ));
    } catch (error) {
      console.error('Failed to save file:', error);
      // Show error to user
      alert(`Failed to save file: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setSaving(false);
    }
  };

  // ===== HELPERS =====
  
  const getLanguage = (path: string): string => {
    const ext = path.split('.').pop()?.toLowerCase();
    const langMap: Record<string, string> = {
      tsx: 'typescript', ts: 'typescript', jsx: 'javascript', js: 'javascript',
      css: 'css', json: 'json', md: 'markdown', html: 'html',
    };
    return langMap[ext || ''] || 'plaintext';
  };

  const getCurrentStageIndex = (): number => {
    if (!currentProject) return -1;
    const statusMap: Record<string, string> = {
      'building': 'building',
      'coding': 'building',
    };
    const normalizedStatus = statusMap[currentProject.status] || currentProject.status;
    return PIPELINE_STAGES.indexOf(normalizedStatus);
  };

  // ===== RENDER HELPERS =====

  const renderStatusPipeline = () => {
    const currentIndex = getCurrentStageIndex();
    
    return (
      <div className="flex items-center gap-1 px-4 py-2 bg-[#0a0a0f] border-b border-[#1e1e2e] overflow-x-auto">
        {PIPELINE_STAGES.map((stage, index) => {
          const isPast = index < currentIndex;
          const isCurrent = index === currentIndex;
          const config = AGENT_CONFIG[stage] || AGENT_CONFIG.coding;
          
          return (
            <React.Fragment key={stage}>
              <div 
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  isCurrent ? 'bg-purple-500/20 text-purple-300 ring-1 ring-purple-500/40' :
                  isPast ? 'bg-emerald-500/10 text-emerald-400' :
                  'bg-[#12121a] text-[#4a4a5a]'
                }`}
              >
                {isCurrent && pipelineRunning ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : isPast ? (
                  <CheckCircle size={12} />
                ) : (
                  config.icon
                )}
                <span className="capitalize">{stage}</span>
              </div>
              {index < PIPELINE_STAGES.length - 1 && (
                <ChevronRight size={14} className={isPast ? 'text-emerald-500' : 'text-[#2a2a3a]'} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    );
  };

  const renderFileTree = () => {
    const folders: Record<string, FazFile[]> = {};
    const rootFiles: FazFile[] = [];

    projectFiles.forEach(file => {
      const parts = file.path.split('/');
      if (parts.length > 1) {
        const folder = parts[0];
        if (!folders[folder]) folders[folder] = [];
        folders[folder].push(file);
      } else {
        rootFiles.push(file);
      }
    });

    return (
      <div className="text-xs">
        {Object.entries(folders).map(([folder, folderFiles]) => (
          <FileTreeFolder key={folder} name={folder} files={folderFiles} onFileClick={openFile} activeFile={activeTab} />
        ))}
        {rootFiles.map(file => (
          <FileTreeItem key={file.path} file={file} onClick={() => openFile(file)} isActive={activeTab === file.path} />
        ))}
      </div>
    );
  };

  const activeTabData = openTabs.find(t => t.path === activeTab);

  // ===== MAIN RENDER =====
  
  const renderContent = () => (
    <div className="h-full flex flex-col bg-[#08080C]">
      {/* Header */}
      <div className="h-12 border-b border-[#1a1a2e] flex items-center justify-between px-4 bg-[#0d0d14] shrink-0">
        <div className="flex items-center gap-3">
          {view === 'workspace' && (
            <button onClick={handleBackToProjects} className="p-1.5 hover:bg-[#1a1a2e] rounded-lg text-[#64748B] hover:text-white transition-all">
              <ChevronRight size={16} className="rotate-180" />
            </button>
          )}
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-purple-500/20 to-indigo-600/20 flex items-center justify-center border border-purple-500/30">
              <Zap size={14} className="text-purple-400" />
            </div>
            <span className="font-semibold text-white text-sm">
              {view === 'projects' ? 'Faz Code' : currentProject?.name || 'Project'}
            </span>
            {currentProject && (
              <span className={`px-2 py-0.5 text-[10px] font-medium rounded-full uppercase tracking-wide ${
                pipelineRunning ? 'bg-purple-500/20 text-purple-300 animate-pulse' :
                currentProject.status === 'approved' ? 'bg-emerald-500/20 text-emerald-300' :
                currentProject.status === 'deployed' ? 'bg-blue-500/20 text-blue-300' :
                currentProject.status === 'failed' ? 'bg-red-500/20 text-red-300' :
                'bg-[#1e1e2e] text-[#64748b]'
              }`}>
                {currentProject.status}
              </span>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {view === 'workspace' && currentProject && (
            <>
              <button onClick={handleRefresh} className="p-1.5 text-[#64748B] hover:text-white hover:bg-[#1a1a2e] rounded-lg transition-all" title="Refresh">
                <RefreshCw size={14} className={pipelineRunning ? 'animate-spin' : ''} />
              </button>
              
              {pipelineRunning ? (
                <button onClick={handleStopPipeline} className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-xs font-medium hover:bg-red-500/30 border border-red-500/30">
                  <Square size={12} /> Stop
                </button>
              ) : (
                <button onClick={handleRunPipeline} className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg text-xs font-medium hover:from-purple-500 hover:to-indigo-500 shadow-lg shadow-purple-500/20">
                  <Play size={12} /> Run
                </button>
              )}
              
              {projectFiles.length > 0 && !pipelineRunning && ['approved', 'review'].includes(currentProject.status) && (
                <button onClick={handleDeploy} className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-xs font-medium hover:bg-emerald-500/30 border border-emerald-500/30">
                  <Rocket size={12} /> Deploy
                </button>
              )}
            </>
          )}
          
          <button onClick={onClose} className="p-1.5 hover:bg-[#1a1a2e] rounded-lg text-[#64748B] hover:text-white transition-all">
            <X size={16} />
          </button>
        </div>
      </div>

      {/* Status Pipeline */}
      {view === 'workspace' && currentProject && renderStatusPipeline()}

      {/* Error Banner */}
      {pipelineError && (
        <div className="px-4 py-2 bg-red-500/10 border-b border-red-500/30 flex items-center gap-2">
          <AlertCircle size={14} className="text-red-400" />
          <span className="text-xs text-red-400 flex-1">{pipelineError}</span>
          <button onClick={() => setPipelineError(null)} className="text-red-400 hover:text-red-300">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {view === 'projects' ? (
          <ProjectsView
            projects={projects}
            loading={loading}
            loadingError={loadingError}
            createError={createError}
            creating={creating}
            newProjectName={newProjectName}
            newProjectPrompt={newProjectPrompt}
            setNewProjectName={setNewProjectName}
            setNewProjectPrompt={setNewProjectPrompt}
            onCreateProject={handleCreateProject}
            onSelectProject={handleSelectProject}
            onRefresh={fetchProjects}
          />
        ) : (
          <div className="h-full flex">
            {/* Left: File Tree */}
            <div className="w-[200px] border-r border-[#1a1a2e] flex flex-col bg-[#0a0a10]">
              <div className="p-3 border-b border-[#1a1a2e] flex items-center justify-between">
                <span className="text-[10px] font-semibold text-[#64748B] uppercase tracking-wider">Explorer</span>
                <span className="text-[10px] text-purple-400 font-mono">{projectFiles.length}</span>
              </div>
              
              <div className="flex-1 overflow-y-auto p-2">
                {projectFiles.length === 0 ? (
                  <div className="flex items-center justify-center h-full text-[#4a4a5a] text-center px-2">
                    <div>
                      <Terminal size={24} className="mx-auto mb-2 opacity-40" />
                      <p className="text-[10px]">{pipelineRunning ? 'Generating...' : 'No files yet'}</p>
                    </div>
                  </div>
                ) : (
                  renderFileTree()
                )}
              </div>
              
              {currentProject && (
                <div className="p-3 border-t border-[#1a1a2e] bg-[#08080c] text-[10px] space-y-1">
                  <div className="flex justify-between text-[#64748B]">
                    <span>Files</span>
                    <span className="text-[#94A3B8] font-mono">{projectFiles.length}</span>
                  </div>
                  <div className="flex justify-between text-[#64748B]">
                    <span>Tokens</span>
                    <span className="text-[#94A3B8] font-mono">{currentProject.total_tokens_used?.toLocaleString() || 0}</span>
                  </div>
                  <div className="flex justify-between text-[#64748B]">
                    <span>Cost</span>
                    <span className="text-[#94A3B8] font-mono">${((currentProject.total_cost_cents || 0) / 100).toFixed(3)}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Center: Editor + Preview */}
            <div className="flex-1 flex flex-col min-w-0">
              {/* Tabs */}
              <div className="h-9 bg-[#0a0a0f] border-b border-[#1a1a2e] flex items-center">
                <div className="flex-1 flex items-center overflow-x-auto">
                  {openTabs.map(tab => (
                    <div
                      key={tab.path}
                      onClick={() => setActiveTab(tab.path)}
                      className={`flex items-center gap-2 px-3 h-9 border-r border-[#1a1a2e] cursor-pointer group ${
                        activeTab === tab.path ? 'bg-[#12121a] text-white' : 'text-[#64748B] hover:text-[#94a3b8]'
                      }`}
                    >
                      <FileCode size={12} />
                      <span className="text-xs font-mono truncate max-w-[120px]">
                        {tab.isDirty && <span className="text-amber-400 mr-1">•</span>}
                        {tab.path.split('/').pop()}
                      </span>
                      <button 
                        onClick={(e) => { e.stopPropagation(); closeTab(tab.path); }}
                        className="opacity-0 group-hover:opacity-100 hover:text-red-400 transition-opacity"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                </div>
                
                <div className="flex items-center gap-1 px-2">
                  <button onClick={() => setShowPreview(!showPreview)} className={`p-1.5 rounded ${showPreview ? 'bg-purple-500/20 text-purple-400' : 'text-[#64748B] hover:text-white'}`} title="Toggle Preview">
                    <Eye size={14} />
                  </button>
                  {activeTab && editedContent[activeTab] !== undefined && (
                    <button 
                      onClick={() => handleSaveFile(activeTab)}
                      disabled={saving}
                      className="p-1.5 text-amber-400 hover:bg-amber-500/20 rounded"
                      title="Save (⌘S)"
                    >
                      {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                    </button>
                  )}
                </div>
              </div>

              {/* Editor + Preview Split */}
              <div className="flex-1 flex overflow-hidden">
                {/* Monaco Editor */}
                <div className={`flex flex-col bg-[#0a0a0f] ${showPreview ? 'w-1/2' : 'flex-1'}`}>
                  {activeTabData ? (
                    <MonacoEditor
                      height="100%"
                      language={activeTabData.language}
                      value={getTabContent(activeTabData.path)}
                      onChange={(value) => handleEditorChange(activeTabData.path, value)}
                      theme="vs-dark"
                      options={{
                        minimap: { enabled: false },
                        fontSize: 13,
                        lineNumbers: 'on',
                        scrollBeyondLastLine: false,
                        automaticLayout: true,
                        tabSize: 2,
                        wordWrap: 'on',
                        padding: { top: 12 },
                      }}
                    />
                  ) : (
                    <div className="flex-1 flex items-center justify-center text-[#4a4a5a]">
                      <div className="text-center">
                        <Code2 size={40} className="mx-auto mb-3 opacity-30" />
                        <p className="text-sm mb-1">Select a file to view</p>
                        <p className="text-xs opacity-60">or run the pipeline to generate code</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Preview */}
                {showPreview && (
                  <div className="w-1/2 border-l border-[#1a1a2e] flex flex-col bg-[#0a0a0f]">
                    {/* Preview Toolbar */}
                    <div className="h-9 border-b border-[#1a1a2e] flex items-center justify-between px-3">
                      <div className="flex items-center gap-1 bg-[#08080c] p-0.5 rounded border border-[#1a1a2e]">
                        {(['mobile', 'tablet', 'desktop'] as const).map(mode => (
                          <button
                            key={mode}
                            onClick={() => setPreviewMode(mode)}
                            className={`p-1 rounded transition-colors ${previewMode === mode ? 'bg-[#1e1e2e] text-white' : 'text-[#64748B] hover:text-[#94A3B8]'}`}
                            title={`${mode} view`}
                          >
                            {mode === 'mobile' ? <Smartphone size={12} /> : mode === 'tablet' ? <Tablet size={12} /> : <Monitor size={12} />}
                          </button>
                        ))}
                      </div>
                      <button onClick={() => setPreviewKey(k => k + 1)} className="p-1 text-[#64748B] hover:text-white" title="Refresh preview">
                        <RefreshCw size={12} />
                      </button>
                    </div>

                    {/* Live Preview */}
                    <div className="flex-1 p-4 bg-[radial-gradient(#1e1e2e_1px,transparent_1px)] [background-size:12px_12px] flex items-start justify-center overflow-auto">
                      <div className={`bg-white shadow-2xl transition-all duration-300 h-full overflow-hidden ${
                        previewMode === 'mobile' ? 'w-[375px] rounded-2xl border-4 border-[#1e1e2e]' :
                        previewMode === 'tablet' ? 'w-[768px] rounded-xl border-2 border-[#1e1e2e]' :
                        'w-full'
                      }`}>
                        <FazLivePreview
                          key={previewKey}
                          files={projectFiles}
                          projectName={currentProject?.name || 'Project'}
                          previewMode={previewMode}
                          className="w-full h-full"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right: Activity + Chat */}
            <div className="w-[300px] border-l border-[#1a1a2e] flex flex-col bg-[#0a0a10]">
              {/* Tab Switcher */}
              <div className="flex border-b border-[#1a1a2e]">
                <button 
                  onClick={() => setActiveRightTab('activity')}
                  className={`flex-1 py-2 text-xs font-medium ${activeRightTab === 'activity' ? 'text-white border-b-2 border-purple-500' : 'text-[#64748B]'}`}
                >
                  <Bot size={12} className="inline mr-1" /> Activity
                </button>
                <button 
                  onClick={() => setActiveRightTab('chat')}
                  className={`flex-1 py-2 text-xs font-medium ${activeRightTab === 'chat' ? 'text-white border-b-2 border-purple-500' : 'text-[#64748B]'}`}
                >
                  <MessageSquare size={12} className="inline mr-1" /> Chat
                </button>
              </div>
              
              {activeRightTab === 'activity' ? (
                <>
                  <div className="p-3 border-b border-[#1a1a2e] flex justify-between items-center">
                    <span className="text-[10px] font-semibold text-[#94A3B8] uppercase tracking-wider">Agent Activity</span>
                    {pipelineRunning && (
                      <div className="flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                        <span className="text-[9px] text-green-400 font-medium">LIVE</span>
                      </div>
                    )}
                  </div>
                  
                  <div ref={activityScrollRef} className="flex-1 overflow-y-auto p-3 space-y-2">
                    <AnimatePresence mode="popLayout">
                      {activities.length === 0 ? (
                        <div className="text-center text-[#4a4a5a] py-8">
                          <Bot size={24} className="mx-auto mb-2 opacity-40" />
                          <p className="text-xs">No activity yet</p>
                          <p className="text-[10px] mt-1 opacity-60">Run pipeline to start</p>
                        </div>
                      ) : (
                        [...activities].slice(0, 50).map((activity, idx) => {
                          const agentConfig = AGENT_CONFIG[activity.agent_name.toLowerCase()] || AGENT_CONFIG.coding;
                          
                          return (
                            <motion.div
                              key={`${activity.activity_id}-${idx}`}
                              initial={{ opacity: 0, y: -5 }}
                              animate={{ opacity: 1, y: 0 }}
                              className="relative pl-6 pb-2"
                            >
                              <div 
                                className="absolute left-0 top-0 w-4 h-4 rounded flex items-center justify-center"
                                style={{ backgroundColor: `${agentConfig.color}20`, color: agentConfig.color }}
                              >
                                {agentConfig.icon}
                              </div>
                              
                              <div className="flex justify-between items-start mb-0.5">
                                <span className="text-[9px] font-medium uppercase tracking-wide" style={{ color: agentConfig.color }}>
                                  {agentConfig.label}
                                </span>
                                <span className="text-[8px] text-[#4a4a5a]">
                                  {format(new Date(activity.started_at), 'HH:mm:ss')}
                                </span>
                              </div>
                              
                              <p className={`text-[11px] leading-relaxed ${activity.content_type === 'error' ? 'text-red-400' : 'text-[#94A3B8]'}`}>
                                {activity.message}
                              </p>
                              
                              {activity.cost_cents > 0 && (
                                <span className="inline-block mt-1 text-[8px] text-[#4a4a5a] bg-[#12121a] px-1 py-0.5 rounded">
                                  ${(activity.cost_cents / 100).toFixed(4)}
                                </span>
                              )}
                            </motion.div>
                          );
                        })
                      )}
                    </AnimatePresence>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex-1 overflow-y-auto p-3 space-y-3">
                    {storeMessages.length === 0 ? (
                      <div className="text-center text-[#4a4a5a] py-8">
                        <MessageSquare size={24} className="mx-auto mb-2 opacity-40" />
                        <p className="text-xs">Chat with Nicole</p>
                        <p className="text-[10px] mt-1 opacity-60">Start a conversation about your project</p>
                      </div>
                    ) : (
                      storeMessages.map((msg) => (
                        <motion.div
                          key={msg.message_id}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className={`rounded-lg p-2.5 text-xs ${
                            msg.role === 'user'
                              ? 'bg-purple-600/20 ml-6 text-white'
                              : 'bg-[#12121a] mr-6 text-[#94A3B8]'
                          }`}
                        >
                          {msg.role === 'assistant' && msg.agent_name && (
                            <div className="flex items-center gap-1 mb-1">
                              <Sparkles size={10} className="text-purple-400" />
                              <span className="text-[9px] text-purple-400 font-medium">
                                {msg.agent_name === 'nicole' ? 'Nicole' : msg.agent_name}
                              </span>
                            </div>
                          )}
                          <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                          {msg.created_at && (
                            <span className="text-[8px] text-[#4a4a5a] mt-1 block">
                              {format(new Date(msg.created_at), 'HH:mm')}
                            </span>
                          )}
                        </motion.div>
                      ))
                    )}
                  </div>
                </>
              )}

              {/* Chat Input */}
              <div className="p-3 border-t border-[#1a1a2e]">
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Message Nicole..."
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                    className="flex-1 px-2.5 py-1.5 bg-[#12121A] border border-[#1E1E2E] rounded text-xs text-white placeholder-[#4a4a5a] focus:outline-none focus:border-purple-500/50"
                    disabled={sendingMessage}
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={sendingMessage || !chatMessage.trim()}
                    className="p-1.5 bg-purple-600/20 text-purple-400 rounded hover:bg-purple-600/30 disabled:opacity-50 transition-all"
                  >
                    {sendingMessage ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  if (!isOpen && !isFullWidth) return null;

  if (isFullWidth) {
    return <div className="h-full w-full">{renderContent()}</div>;
  }

  return (
    <div className="fixed inset-0 z-50 bg-[#08080C]">
      {renderContent()}
    </div>
  );
}

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

function ProjectsView({
  projects, loading, loadingError, createError, creating,
  newProjectName, newProjectPrompt, setNewProjectName, setNewProjectPrompt,
  onCreateProject, onSelectProject, onRefresh
}: {
  projects: FazProject[];
  loading: boolean;
  loadingError: string | null;
  createError: string | null;
  creating: boolean;
  newProjectName: string;
  newProjectPrompt: string;
  setNewProjectName: (v: string) => void;
  setNewProjectPrompt: (v: string) => void;
  onCreateProject: () => void;
  onSelectProject: (p: FazProject) => void;
  onRefresh: () => void;
}) {
  return (
    <div className="h-full flex">
      {/* Create Section */}
      <div className="w-[400px] border-r border-[#1a1a2e] p-6 bg-[#0a0a10]">
        <h3 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
          <Plus size={16} className="text-purple-400" /> New Project
        </h3>
        
        {createError && (
          <div className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-2 text-xs text-red-300">
            {createError}
          </div>
        )}
        
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-[#94A3B8] mb-1.5">Project Name</label>
            <input
              type="text"
              placeholder="My Awesome Website"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              className="w-full px-3 py-2.5 bg-[#12121A] border border-[#1E1E2E] rounded-lg text-white text-sm placeholder-[#4a4a5a] focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20"
            />
          </div>
          
          <div>
            <label className="block text-xs font-medium text-[#94A3B8] mb-1.5">Describe what you want to build</label>
            <textarea
              placeholder="A modern landing page for my AI startup with a hero section, features grid, pricing table, testimonials, and contact form. Dark theme with purple accents..."
              value={newProjectPrompt}
              onChange={(e) => setNewProjectPrompt(e.target.value)}
              rows={6}
              className="w-full px-3 py-2.5 bg-[#12121A] border border-[#1E1E2E] rounded-lg text-white text-sm placeholder-[#4a4a5a] focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 resize-none"
            />
          </div>
          
          <button
            onClick={onCreateProject}
            disabled={creating || !newProjectName.trim() || !newProjectPrompt.trim()}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg font-medium text-sm hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-purple-500/20"
          >
            {creating ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            Start Building
          </button>
        </div>
      </div>

      {/* Projects List */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-white flex items-center gap-2">
            <Folder size={16} className="text-[#64748B]" /> Your Projects
          </h3>
          <button onClick={onRefresh} className="p-1.5 text-[#64748B] hover:text-white transition-colors">
            <RefreshCw size={14} />
          </button>
        </div>
        
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={24} className="animate-spin text-purple-400" />
          </div>
        ) : loadingError ? (
          <div className="text-center py-10">
            <AlertCircle size={32} className="mx-auto mb-3 text-red-400 opacity-60" />
            <p className="text-red-400 text-sm mb-2">{loadingError}</p>
            <button onClick={onRefresh} className="text-purple-400 hover:text-purple-300 text-xs">Try again</button>
          </div>
        ) : projects.length === 0 ? (
          <div className="text-center py-16 text-[#64748B]">
            <FolderOpen size={48} className="mx-auto mb-4 opacity-30" />
            <p className="text-sm mb-1">No projects yet</p>
            <p className="text-xs opacity-60">Create your first AI-powered website</p>
          </div>
        ) : (
          <div className="grid gap-3">
            {projects.map((project) => (
              <button
                key={project.project_id}
                onClick={() => onSelectProject(project)}
                className="w-full p-4 bg-[#12121A] border border-[#1E1E2E] rounded-xl text-left hover:border-purple-500/40 hover:bg-[#14141f] transition-all group"
              >
                <div className="flex items-start justify-between mb-2">
                  <span className="font-medium text-white text-sm group-hover:text-purple-300 transition-colors">
                    {project.name}
                  </span>
                  <span className={`px-2 py-0.5 text-[9px] font-medium rounded uppercase ${
                    project.status === 'deployed' ? 'bg-emerald-500/20 text-emerald-300' :
                    project.status === 'approved' ? 'bg-blue-500/20 text-blue-300' :
                    project.status === 'failed' ? 'bg-red-500/20 text-red-300' :
                    'bg-[#1e1e2e] text-[#64748b]'
                  }`}>
                    {project.status}
                  </span>
                </div>
                <p className="text-xs text-[#64748B] line-clamp-2 mb-3">{project.original_prompt}</p>
                <div className="flex items-center gap-4 text-[10px] text-[#4a4a5a]">
                  <span className="flex items-center gap-1"><FileCode size={10} /> {project.file_count} files</span>
                  <span>{project.total_tokens_used?.toLocaleString() || 0} tokens</span>
                  <span>${((project.total_cost_cents || 0) / 100).toFixed(3)}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// File Tree Components
function FileTreeFolder({ name, files, onFileClick, activeFile }: {
  name: string;
  files: FazFile[];
  onFileClick: (f: FazFile) => void;
  activeFile: string | null;
}) {
  const [isOpen, setIsOpen] = useState(true);
  
  return (
    <div>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 w-full px-2 py-1 text-[#94A3B8] hover:bg-[#1e1e2e] rounded text-left"
      >
        {isOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <Folder size={12} className="text-purple-400" />
        <span className="truncate">{name}</span>
        <span className="text-[9px] text-[#4a4a5a] ml-auto">{files.length}</span>
      </button>
      
      {isOpen && (
        <div className="ml-4">
          {files.map(file => (
            <FileTreeItem key={file.path} file={file} onClick={() => onFileClick(file)} isActive={activeFile === file.path} />
          ))}
        </div>
      )}
    </div>
  );
}

function FileTreeItem({ file, onClick, isActive }: {
  file: FazFile;
  onClick: () => void;
  isActive: boolean;
}) {
  const filename = file.path.split('/').pop() || file.filename;
  
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 w-full px-2 py-1 text-left rounded ${
        isActive ? 'bg-purple-500/20 text-purple-300' : 'text-[#94A3B8] hover:bg-[#1e1e2e]'
      }`}
    >
      <FileCode size={12} className={isActive ? 'text-purple-400' : 'text-[#64748B]'} />
      <span className="truncate text-xs">{filename}</span>
    </button>
  );
}
