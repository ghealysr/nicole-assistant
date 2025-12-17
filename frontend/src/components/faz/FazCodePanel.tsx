'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  X, Plus, Folder, Play, Square, Loader2, Code2, ChevronRight,
  Send, Bot, Terminal, Eye, Rocket, RefreshCw, Sparkles,
  BrainCircuit, Search, PenTool, Bug, CheckCircle, Zap
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useFazStore } from '@/lib/faz/store';
import { fazApi } from '@/lib/faz/api';
import { fazWS } from '@/lib/faz/websocket';
import { FazProject, FazActivity } from '@/types/faz';
import { StatusBadge } from './StatusBadge';
import { FileTree } from './FileTree';
import { CodeViewer } from './CodeViewer';
import { format } from 'date-fns';

interface FazCodePanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const AGENT_ICONS: Record<string, React.ReactNode> = {
  nicole: <Bot size={14} className="text-purple-400" />,
  planning: <BrainCircuit size={14} className="text-indigo-400" />,
  research: <Search size={14} className="text-blue-400" />,
  design: <PenTool size={14} className="text-pink-400" />,
  coding: <Code2 size={14} className="text-yellow-400" />,
  qa: <Bug size={14} className="text-orange-400" />,
  review: <CheckCircle size={14} className="text-green-400" />,
  memory: <Sparkles size={14} className="text-cyan-400" />,
};

const AGENT_LABELS: Record<string, string> = {
  nicole: 'Nicole (Orchestrator)',
  planning: 'Planning Agent',
  research: 'Research Agent',
  design: 'Design Agent',
  coding: 'Coding Agent',
  qa: 'QA Agent',
  review: 'Review Agent',
  memory: 'Memory Agent',
};

/**
 * Faz Code Panel - Production-grade AI coding dashboard.
 * 
 * Features:
 * - Real-time WebSocket updates
 * - Activity polling fallback
 * - Agent status visualization
 * - Chat integration
 * - File tree with code preview
 */
export function FazCodePanel({ isOpen, onClose }: FazCodePanelProps) {
  // Panel state
  const [panelWidth, setPanelWidth] = useState(1000);
  const [isResizing, setIsResizing] = useState(false);
  const [view, setView] = useState<'projects' | 'workspace'>('projects');
  
  // Data state
  const [projects, setProjects] = useState<FazProject[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  
  // Create project state
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectPrompt, setNewProjectPrompt] = useState('');
  
  // Pipeline state
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  
  // Chat state
  const [chatMessage, setChatMessage] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);

  // Refs
  const resizeRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(1000);
  const activityPollRef = useRef<NodeJS.Timeout | null>(null);
  const activityScrollRef = useRef<HTMLDivElement>(null);

  const MIN_WIDTH = 700;
  const MAX_WIDTH = 1400;

  // Store
  const { 
    currentProject, setCurrentProject,
    files, fileMetadata, selectedFile, selectFile, setFiles,
    activities, setActivities, addActivity,
    messages, addMessage, setMessages
  } = useFazStore();

  // ===== FETCH DATA =====
  
  const fetchProjects = useCallback(async () => {
    setLoading(true);
    setLoadingError(null);
    try {
      const data = await fazApi.listProjects();
      setProjects(data.projects);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
      setLoadingError(error instanceof Error ? error.message : 'Failed to load projects');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchProjectData = useCallback(async (projectId: number) => {
    try {
      // Fetch files
      const projectFiles = await fazApi.getFiles(projectId);
      setFiles(projectFiles);
      
      // Fetch activities
      const activityList = await fazApi.getActivities(projectId);
      setActivities(activityList);
      
      // Fetch chat history
      try {
        const chatHistory = await fazApi.getChatHistory(projectId);
        setMessages(chatHistory);
      } catch {
        // Chat might not be implemented
      }
    } catch (error) {
      console.error('Failed to fetch project data:', error);
    }
  }, [setFiles, setActivities, setMessages]);

  const pollActivities = useCallback(async () => {
    if (!currentProject) return;
    
    try {
      const activityList = await fazApi.getActivities(currentProject.project_id);
      setActivities(activityList);
      
      // Also refresh project to get updated status
      const project = await fazApi.getProject(currentProject.project_id);
      setCurrentProject(project);
      
      // Check if pipeline is still running
      const isRunning = ['processing', 'planning', 'researching', 'designing', 'building', 'qa', 'review']
        .includes(project.status);
      setPipelineRunning(isRunning);
      
      // If running, also fetch files for real-time updates
      if (isRunning) {
        const projectFiles = await fazApi.getFiles(currentProject.project_id);
        setFiles(projectFiles);
      }
    } catch (error) {
      console.error('Activity poll failed:', error);
    }
  }, [currentProject, setActivities, setCurrentProject, setFiles]);

  // ===== EFFECTS =====
  
  // Fetch projects on open
  useEffect(() => {
    if (isOpen) {
      fetchProjects();
    }
  }, [isOpen, fetchProjects]);

  // Setup WebSocket and polling when viewing workspace
  useEffect(() => {
    if (!isOpen || view !== 'workspace' || !currentProject) return;

    // Connect WebSocket
    fazWS.connect(currentProject.project_id);
    
    // Start polling (backup for WebSocket)
    activityPollRef.current = setInterval(pollActivities, 2000);

    return () => {
      fazWS.disconnect();
      if (activityPollRef.current) {
        clearInterval(activityPollRef.current);
      }
    };
  }, [isOpen, view, currentProject, pollActivities]);

  // Auto-scroll activities
  useEffect(() => {
    if (activityScrollRef.current) {
      activityScrollRef.current.scrollTop = 0;
    }
  }, [activities]);

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
    setPipelineRunning(['processing', 'planning', 'researching', 'designing', 'building', 'qa', 'review'].includes(project.status));
    await fetchProjectData(project.project_id);
  };

  const handleBackToProjects = () => {
    setView('projects');
    setCurrentProject(null);
    setActivities([]);
    fazWS.disconnect();
    if (activityPollRef.current) {
      clearInterval(activityPollRef.current);
    }
  };

  const handleRunPipeline = async () => {
    if (!currentProject) return;
    
    setPipelineRunning(true);
    setPipelineError(null);
    
    try {
      await fazApi.runPipeline(currentProject.project_id);
      
      // Update project status
      const project = await fazApi.getProject(currentProject.project_id);
      setCurrentProject(project);
      
      // Start immediate poll
      pollActivities();
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
      
      // Update project status
      const project = await fazApi.getProject(currentProject.project_id);
      setCurrentProject(project);
    } catch (error) {
      console.error('Failed to stop pipeline:', error);
    }
  };

  const handleSendMessage = async () => {
    if (!currentProject || !chatMessage.trim()) return;
    
    setSendingMessage(true);
    try {
      await fazApi.sendChatMessage(currentProject.project_id, chatMessage);
      setChatMessage('');
      
      // Refresh chat
      const chatHistory = await fazApi.getChatHistory(currentProject.project_id);
      setMessages(chatHistory);
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
    } catch (error) {
      console.error('Deploy failed:', error);
    }
  };

  // ===== RESIZE =====
  
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    startXRef.current = e.clientX;
    startWidthRef.current = panelWidth;
  }, [panelWidth]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const delta = startXRef.current - e.clientX;
      const newWidth = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, startWidthRef.current + delta));
      setPanelWidth(newWidth);
    };

    const handleMouseUp = () => setIsResizing(false);

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  // ===== DERIVED STATE =====
  
  const selectedFileContent = selectedFile ? files.get(selectedFile) || '' : '';
  const filePaths = Array.from(fileMetadata.keys());
  const currentAgent = currentProject?.current_agent?.toLowerCase() || null;

  // ===== RENDER =====
  
  return (
    <div
      className={`fixed top-0 right-0 h-full bg-[#08080C] border-l border-[#1a1a2e] shadow-2xl z-50 
        transition-transform duration-300 ease-out flex flex-col
        ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
      style={{ width: panelWidth }}
    >
      {/* Resize handle */}
      <div
        ref={resizeRef}
        className="absolute left-0 top-0 bottom-0 w-1.5 cursor-ew-resize 
          hover:bg-gradient-to-b hover:from-purple-500/50 hover:via-indigo-500/50 hover:to-purple-500/50 
          transition-colors z-20"
        onMouseDown={handleMouseDown}
      />

      {/* Header */}
      <div className="h-14 border-b border-[#1a1a2e] flex items-center justify-between px-5 bg-[#0d0d14] shrink-0">
        <div className="flex items-center gap-3">
          {view === 'workspace' && (
            <button
              onClick={handleBackToProjects}
              className="p-1.5 hover:bg-[#1a1a2e] rounded-lg text-[#64748B] hover:text-white transition-all"
            >
              <ChevronRight size={18} className="rotate-180" />
            </button>
          )}
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/20 to-indigo-600/20 flex items-center justify-center border border-purple-500/30">
              <Zap size={16} className="text-purple-400" />
            </div>
            <span className="font-semibold text-white tracking-tight text-lg">
              {view === 'projects' ? 'Faz Code' : currentProject?.name || 'Project'}
            </span>
          </div>
          {currentProject && <StatusBadge status={currentProject.status} />}
        </div>
        
        <div className="flex items-center gap-2">
          {view === 'workspace' && currentProject && (
            <>
              {/* Current Agent Indicator */}
              {pipelineRunning && currentAgent && (
                <div className="flex items-center gap-2 px-3 py-1.5 bg-[#12121a] border border-[#1e1e2e] rounded-lg mr-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                  <span className="flex items-center gap-1.5 text-xs text-[#94A3B8]">
                    {AGENT_ICONS[currentAgent] || <Bot size={14} />}
                    {AGENT_LABELS[currentAgent] || currentAgent}
                  </span>
                </div>
              )}
              
              <button
                onClick={() => pollActivities()}
                className="p-2 text-[#64748B] hover:text-white hover:bg-[#1a1a2e] rounded-lg transition-all"
                title="Refresh"
              >
                <RefreshCw size={16} />
              </button>
              
              {pipelineRunning ? (
                <button
                  onClick={handleStopPipeline}
                  className="flex items-center gap-2 px-4 py-2 bg-red-500/20 text-red-400 rounded-lg text-sm font-medium hover:bg-red-500/30 transition-all border border-red-500/30"
                >
                  <Square size={14} />
                  Stop
                </button>
              ) : (
                <button
                  onClick={handleRunPipeline}
                  className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg text-sm font-medium hover:from-purple-500 hover:to-indigo-500 transition-all shadow-lg shadow-purple-500/20"
                >
                  <Play size={14} />
                  Run Pipeline
                </button>
              )}
              
              {files.size > 0 && !pipelineRunning && (
                <button
                  onClick={handleDeploy}
                  className="flex items-center gap-2 px-4 py-2 bg-emerald-500/20 text-emerald-400 rounded-lg text-sm font-medium hover:bg-emerald-500/30 transition-all border border-emerald-500/30"
                >
                  <Rocket size={14} />
                  Deploy
                </button>
              )}
            </>
          )}
          
          <button
            onClick={onClose}
            className="p-2 hover:bg-[#1a1a2e] rounded-lg text-[#64748B] hover:text-white transition-all ml-2"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {pipelineError && (
        <div className="px-4 py-3 bg-red-500/10 border-b border-red-500/30 flex items-center justify-between">
          <span className="text-sm text-red-400">{pipelineError}</span>
          <button onClick={() => setPipelineError(null)} className="text-red-400 hover:text-red-300">
            <X size={16} />
          </button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {view === 'projects' ? (
          /* ===== PROJECTS VIEW ===== */
          <div className="h-full flex flex-col">
            {/* Create Project */}
            <div className="p-5 border-b border-[#1a1a2e] bg-[#0a0a10]">
              <h3 className="text-sm font-medium text-[#94A3B8] mb-4">Create New Project</h3>
              <div className="space-y-3">
                {createError && (
                  <div className="rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                    {createError}
                  </div>
                )}
                <input
                  type="text"
                  placeholder="Project name..."
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-4 py-3 bg-[#12121A] border border-[#1E1E2E] rounded-lg text-white text-sm placeholder-[#64748B] focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20"
                />
                <textarea
                  placeholder="Describe what you want to build... (e.g., 'A landing page for my AI startup with dark theme, pricing section, testimonials, and contact form')"
                  value={newProjectPrompt}
                  onChange={(e) => setNewProjectPrompt(e.target.value)}
                  rows={4}
                  className="w-full px-4 py-3 bg-[#12121A] border border-[#1E1E2E] rounded-lg text-white text-sm placeholder-[#64748B] focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/20 resize-none"
                />
                <button
                  onClick={handleCreateProject}
                  disabled={creating || !newProjectName.trim() || !newProjectPrompt.trim()}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-lg font-medium hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-purple-500/20"
                >
                  {creating ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <Plus size={18} />
                  )}
                  Create & Start Building
                </button>
              </div>
            </div>

            {/* Projects List */}
            <div className="flex-1 overflow-y-auto p-5">
              <h3 className="text-sm font-medium text-[#94A3B8] mb-4">Your Projects</h3>
              
              {loading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 size={28} className="animate-spin text-purple-400" />
                </div>
              ) : loadingError ? (
                <div className="text-center py-10">
                  <p className="text-red-400 mb-3">{loadingError}</p>
                  <button onClick={fetchProjects} className="text-purple-400 hover:text-purple-300 text-sm">
                    Try again
                  </button>
                </div>
              ) : projects.length === 0 ? (
                <div className="text-center py-16 text-[#64748B]">
                  <Folder size={48} className="mx-auto mb-4 opacity-40" />
                  <p className="text-base mb-2">No projects yet</p>
                  <p className="text-sm">Create your first AI-powered project above</p>
                </div>
              ) : (
                <div className="grid gap-3">
                  {projects.map((project) => (
                    <button
                      key={project.project_id}
                      onClick={() => handleSelectProject(project)}
                      className="w-full p-5 bg-[#12121A] border border-[#1E1E2E] rounded-xl text-left hover:border-purple-500/40 hover:bg-[#14141f] transition-all group"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <span className="font-medium text-white group-hover:text-purple-300 transition-colors">
                          {project.name}
                        </span>
                        <StatusBadge status={project.status} />
                      </div>
                      <p className="text-sm text-[#64748B] line-clamp-2 mb-3">
                        {project.original_prompt}
                      </p>
                      <div className="flex items-center gap-4 text-xs text-[#475569]">
                        <span className="flex items-center gap-1">
                          <Code2 size={12} />
                          {project.file_count} files
                        </span>
                        <span>{project.total_tokens_used.toLocaleString()} tokens</span>
                        <span>${(project.total_cost_cents / 100).toFixed(2)}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          /* ===== WORKSPACE VIEW ===== */
          <div className="h-full flex">
            {/* Left: File Tree */}
            <div className="w-[220px] border-r border-[#1a1a2e] flex flex-col bg-[#0a0a10]">
              <div className="p-3 border-b border-[#1a1a2e] flex items-center justify-between">
                <span className="text-xs font-semibold text-[#64748B] uppercase tracking-wider">Files</span>
                <span className="text-xs text-purple-400 font-mono">{files.size}</span>
              </div>
              
              {files.size === 0 ? (
                <div className="flex-1 flex items-center justify-center text-[#4a4a5a] text-center px-4">
                  <div>
                    <Terminal size={32} className="mx-auto mb-3 opacity-40" />
                    <p className="text-xs">No files yet</p>
                    <p className="text-[10px] mt-1 text-[#3a3a4a]">Run pipeline to generate</p>
                  </div>
                </div>
              ) : (
                <div className="flex-1 overflow-y-auto">
                  <FileTree files={filePaths} />
                </div>
              )}
              
              {/* Project Stats */}
              {currentProject && (
                <div className="p-4 border-t border-[#1a1a2e] bg-[#08080c] text-xs space-y-2">
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

            {/* Center: Code Viewer */}
            <div className="flex-1 flex flex-col min-w-0 bg-[#0a0a10]">
              {selectedFile ? (
                <CodeViewer
                  code={selectedFileContent}
                  language={selectedFile.split('.').pop() || 'typescript'}
                  path={selectedFile}
                />
              ) : (
                <div className="flex-1 flex items-center justify-center text-[#4a4a5a]">
                  <div className="text-center">
                    <Code2 size={48} className="mx-auto mb-4 opacity-30" />
                    <p className="text-base mb-2">Select a file to view code</p>
                    <p className="text-sm opacity-60">or run the pipeline to generate files</p>
                  </div>
                </div>
              )}
            </div>

            {/* Right: Activity & Chat */}
            <div className="w-[320px] border-l border-[#1a1a2e] flex flex-col bg-[#0a0a10]">
              {/* Activity Feed */}
              <div className="flex-1 flex flex-col min-h-0">
                <div className="p-4 border-b border-[#1a1a2e] flex justify-between items-center bg-[#0d0d14]">
                  <span className="text-xs font-semibold text-[#F1F5F9] uppercase tracking-wider">Agent Activity</span>
                  {pipelineRunning && (
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                      <span className="text-[10px] text-green-400 font-medium">LIVE</span>
                    </div>
                  )}
                </div>
                
                <div ref={activityScrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
                  <AnimatePresence mode="popLayout">
                    {activities.length === 0 ? (
                      <div className="text-center text-[#4a4a5a] py-12">
                        <Bot size={32} className="mx-auto mb-3 opacity-40" />
                        <p className="text-sm">No activity yet</p>
                        <p className="text-xs mt-1 opacity-60">Click &quot;Run Pipeline&quot; to start</p>
                      </div>
                    ) : (
                      [...activities].reverse().slice(0, 50).map((activity, idx) => (
                        <motion.div
                          key={`${activity.activity_id}-${idx}`}
                          initial={{ opacity: 0, y: -10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: 10 }}
                          className="relative pl-7 pb-3"
                        >
                          <div className="absolute left-0 top-0 p-1.5 bg-[#12121a] border border-[#1e1e2e] rounded-lg">
                            {AGENT_ICONS[activity.agent_name.toLowerCase()] || <Bot size={14} />}
                          </div>
                          
                          <div className="flex justify-between items-start mb-1">
                            <span className="text-[10px] font-medium text-[#64748B] uppercase tracking-wide">
                              {activity.agent_name}
                            </span>
                            <span className="text-[9px] text-[#4a4a5a]">
                              {format(new Date(activity.started_at), 'HH:mm:ss')}
                            </span>
                          </div>
                          
                          <p className={`text-xs leading-relaxed ${
                            activity.content_type === 'error' ? 'text-red-400' : 'text-[#94A3B8]'
                          }`}>
                            {activity.message}
                          </p>
                          
                          {activity.cost_cents > 0 && (
                            <span className="inline-block mt-1.5 text-[9px] text-[#4a4a5a] bg-[#12121a] px-1.5 py-0.5 rounded">
                              ${(activity.cost_cents / 100).toFixed(4)}
                            </span>
                          )}
                        </motion.div>
                      ))
                    )}
                  </AnimatePresence>
                </div>
              </div>

              {/* Chat Input */}
              <div className="p-4 border-t border-[#1a1a2e] bg-[#0d0d14]">
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Message Nicole..."
                    value={chatMessage}
                    onChange={(e) => setChatMessage(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                    className="flex-1 px-3 py-2 bg-[#12121A] border border-[#1E1E2E] rounded-lg text-sm text-white placeholder-[#4a4a5a] focus:outline-none focus:border-purple-500/50"
                    disabled={sendingMessage}
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={sendingMessage || !chatMessage.trim()}
                    className="p-2 bg-purple-600/20 text-purple-400 rounded-lg hover:bg-purple-600/30 disabled:opacity-50 transition-all"
                  >
                    {sendingMessage ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
