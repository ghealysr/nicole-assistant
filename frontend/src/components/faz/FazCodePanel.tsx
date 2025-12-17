'use client';

/**
 * FAZ CODE - AI-Powered Web Development Dashboard
 * 
 * A complete development environment with:
 * - Monaco-style code editor with line numbers and tabs
 * - Live preview with responsive viewport switching
 * - Real-time agent activity feed
 * - Status pipeline showing agent progress
 * - File tree with collapsible folders
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  X, Plus, Folder, Play, Square, Loader2, Code2, ChevronRight, ChevronDown,
  Send, Bot, Terminal, Rocket, RefreshCw, Sparkles, Monitor, Tablet, Smartphone,
  BrainCircuit, Search, PenTool, Bug, CheckCircle, Zap, Eye, FileCode,
  Copy, Check, AlertCircle, FolderOpen
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useFazStore } from '@/lib/faz/store';
import { fazApi } from '@/lib/faz/api';
import { fazWS } from '@/lib/faz/websocket';
import { FazProject, FazFile, FazActivity } from '@/types/faz';
import { format } from 'date-fns';

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
  
  // Editor
  const [openTabs, setOpenTabs] = useState<OpenTab[]>([]);
  const [activeTab, setActiveTab] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  
  // Preview
  const [previewMode, setPreviewMode] = useState<'desktop' | 'tablet' | 'mobile'>('desktop');
  const [showPreview, setShowPreview] = useState(true);
  
  // Activity
  const [activities, setActivities] = useState<FazActivity[]>([]);
  const activityScrollRef = useRef<HTMLDivElement>(null);
  const activityPollRef = useRef<NodeJS.Timeout | null>(null);
  
  // Chat
  const [chatMessage, setChatMessage] = useState('');
  const [sendingMessage, setSendingMessage] = useState(false);
  
  // Store
  const { 
    currentProject, setCurrentProject,
    files, fileMetadata, setFiles,
    setActivities: storeSetActivities,
  } = useFazStore();

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

  const fetchProjectData = useCallback(async (projectId: number) => {
    try {
      const [filesData, activitiesData] = await Promise.all([
        fazApi.getFiles(projectId),
        fazApi.getActivities(projectId),
      ]);
      
      setFiles(filesData || []);
      setActivities(activitiesData || []);
      storeSetActivities(activitiesData || []);
      
      // Open first file - use inline function to avoid dependency issue
      if (filesData && filesData.length > 0) {
        const preferred = filesData.find(f => f.path.includes('page.tsx')) || 
                         filesData.find(f => f.path.includes('layout.tsx')) ||
                         filesData[0];
        if (preferred) {
          const lang = preferred.path.split('.').pop()?.toLowerCase();
          const langMap: Record<string, string> = {
            tsx: 'typescript', ts: 'typescript', jsx: 'javascript', js: 'javascript',
            css: 'css', json: 'json', md: 'markdown', html: 'html',
          };
          setOpenTabs(tabs => {
            if (tabs.find(t => t.path === preferred.path)) return tabs;
            return [...tabs, { 
              path: preferred.path, 
              content: preferred.content, 
              language: langMap[lang || ''] || 'plaintext',
              isDirty: false 
            }];
          });
          setActiveTab(preferred.path);
        }
      }
    } catch (error) {
      console.error('Failed to fetch project data:', error);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setFiles, storeSetActivities]);

  const pollActivities = useCallback(async () => {
    if (!currentProject) return;
    
    try {
      const data = await fazApi.getActivities(currentProject.project_id);
      setActivities(data || []);
      
      // Refresh project to get status updates
      const project = await fazApi.getProject(currentProject.project_id);
      setCurrentProject(project);
      
      // Update running state
      const runningStatuses = ['planning', 'researching', 'designing', 'building', 'qa', 'review', 'deploying'];
      setPipelineRunning(runningStatuses.includes(project.status));
    } catch (error) {
      console.error('Activity poll failed:', error);
    }
  }, [currentProject, setCurrentProject]);

  // ===== EFFECTS =====
  
  useEffect(() => {
    if (isOpen && view === 'projects') {
      fetchProjects();
    }
  }, [isOpen, view, fetchProjects]);

  useEffect(() => {
    if (currentProject && view === 'workspace' && pipelineRunning) {
      activityPollRef.current = setInterval(pollActivities, 2000);
      return () => {
        if (activityPollRef.current) clearInterval(activityPollRef.current);
      };
    }
  }, [currentProject, view, pipelineRunning, pollActivities]);

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
    const runningStatuses = ['planning', 'researching', 'designing', 'building', 'qa', 'review', 'deploying'];
    setPipelineRunning(runningStatuses.includes(project.status));
    await fetchProjectData(project.project_id);
  };

  const handleBackToProjects = () => {
    setView('projects');
    setCurrentProject(null);
    setActivities([]);
    setOpenTabs([]);
    setActiveTab(null);
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
      pollActivities();
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
      pollActivities();
    } catch (error) {
      console.error('Deploy failed:', error);
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
    if (activeTab === path) {
      const remaining = openTabs.filter(t => t.path !== path);
      setActiveTab(remaining.length > 0 ? remaining[remaining.length - 1].path : null);
    }
  };

  const handleCopy = () => {
    const tab = openTabs.find(t => t.path === activeTab);
    if (tab) {
      navigator.clipboard.writeText(tab.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
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
    return PIPELINE_STAGES.indexOf(currentProject.status);
  };

  const generatePreviewHTML = (): string => {
    const fileArray = Array.from(files.entries());
    const pageFile = fileArray.find(([path]) => path.includes('page.tsx'));
    const globalsCss = fileArray.find(([path]) => path.includes('globals.css'));
    
    if (!pageFile) {
      return `<html><body style="background:#0a0a0f;color:#64748B;display:flex;align-items:center;justify-content:center;height:100vh;font-family:system-ui;"><div style="text-align:center"><h2>No Preview Available</h2><p>Run the pipeline to generate files</p></div></body></html>`;
    }

    // Extract CSS variables if available
    let cssContent = '';
    if (globalsCss) {
      cssContent = globalsCss[1].replace(/@tailwind[^;]+;/g, '');
    }

    // Simple preview that renders the component structure
    return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: system-ui, -apple-system, sans-serif; }
    ${cssContent}
  </style>
</head>
<body>
  <div id="preview-notice" style="position:fixed;top:0;left:0;right:0;background:linear-gradient(90deg,#8B5CF6,#6366F1);color:white;padding:8px 16px;font-size:12px;text-align:center;z-index:9999;">
    📋 Preview Mode - Full render requires deployment
  </div>
  <div style="padding-top:40px;">
    <div style="padding:2rem;background:#0a0a0f;min-height:100vh;color:white;">
      <h1 style="font-size:2rem;font-weight:bold;margin-bottom:1rem;">
        ${currentProject?.name || 'Project Preview'}
      </h1>
      <div style="background:#12121a;border:1px solid #1e1e2e;border-radius:8px;padding:1rem;margin-bottom:1rem;">
        <p style="color:#94a3b8;font-size:14px;margin-bottom:0.5rem;">Generated ${files.size} files:</p>
        <ul style="list-style:none;font-family:monospace;font-size:12px;color:#64748b;">
          ${fileArray.slice(0, 10).map(([path]) => `<li style="padding:4px 0;">📄 ${path}</li>`).join('')}
          ${fileArray.length > 10 ? `<li style="padding:4px 0;color:#8B5CF6;">... and ${fileArray.length - 10} more</li>` : ''}
        </ul>
      </div>
      <p style="color:#64748b;font-size:13px;">Click "Deploy" to see the full rendered site</p>
    </div>
  </div>
</body>
</html>`;
  };

  // ===== RENDER HELPERS =====
  
  const activeTabContent = openTabs.find(t => t.path === activeTab);

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
    const fileArray = Array.from(fileMetadata.values());
    const folders: Record<string, FazFile[]> = {};
    const rootFiles: FazFile[] = [];

    fileArray.forEach(file => {
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
              <button onClick={pollActivities} className="p-1.5 text-[#64748B] hover:text-white hover:bg-[#1a1a2e] rounded-lg transition-all" title="Refresh">
                <RefreshCw size={14} />
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
              
              {files.size > 0 && !pipelineRunning && currentProject.status === 'approved' && (
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
          <WorkspaceView
            files={files}
            openTabs={openTabs}
            activeTab={activeTab}
            activeTabContent={activeTabContent}
            activities={activities}
            currentProject={currentProject}
            previewMode={previewMode}
            showPreview={showPreview}
            pipelineRunning={pipelineRunning}
            chatMessage={chatMessage}
            sendingMessage={sendingMessage}
            copied={copied}
            onSetActiveTab={setActiveTab}
            onCloseTab={closeTab}
            onCopy={handleCopy}
            onSetPreviewMode={setPreviewMode}
            onTogglePreview={() => setShowPreview(!showPreview)}
            onSetChatMessage={setChatMessage}
            onSendMessage={handleSendMessage}
            renderFileTree={renderFileTree}
            generatePreviewHTML={generatePreviewHTML}
            activityScrollRef={activityScrollRef}
          />
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
                  <span>{project.total_tokens_used.toLocaleString()} tokens</span>
                  <span>${(project.total_cost_cents / 100).toFixed(3)}</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function WorkspaceView({
  files, openTabs, activeTab, activeTabContent, activities, currentProject,
  previewMode, showPreview, pipelineRunning, chatMessage, sendingMessage, copied,
  onSetActiveTab, onCloseTab, onCopy, onSetPreviewMode, onTogglePreview,
  onSetChatMessage, onSendMessage, renderFileTree, generatePreviewHTML, activityScrollRef
}: {
  files: Map<string, string>;
  openTabs: OpenTab[];
  activeTab: string | null;
  activeTabContent: OpenTab | undefined;
  activities: FazActivity[];
  currentProject: FazProject | null;
  previewMode: 'desktop' | 'tablet' | 'mobile';
  showPreview: boolean;
  pipelineRunning: boolean;
  chatMessage: string;
  sendingMessage: boolean;
  copied: boolean;
  onSetActiveTab: (p: string) => void;
  onCloseTab: (p: string) => void;
  onCopy: () => void;
  onSetPreviewMode: (m: 'desktop' | 'tablet' | 'mobile') => void;
  onTogglePreview: () => void;
  onSetChatMessage: (m: string) => void;
  onSendMessage: () => void;
  renderFileTree: () => React.ReactNode;
  generatePreviewHTML: () => string;
  activityScrollRef: React.RefObject<HTMLDivElement>;
}) {
  return (
    <div className="h-full flex">
      {/* Left: File Tree */}
      <div className="w-[200px] border-r border-[#1a1a2e] flex flex-col bg-[#0a0a10]">
        <div className="p-3 border-b border-[#1a1a2e] flex items-center justify-between">
          <span className="text-[10px] font-semibold text-[#64748B] uppercase tracking-wider">Explorer</span>
          <span className="text-[10px] text-purple-400 font-mono">{files.size}</span>
        </div>
        
        <div className="flex-1 overflow-y-auto p-2">
          {files.size === 0 ? (
            <div className="flex items-center justify-center h-full text-[#4a4a5a] text-center px-2">
              <div>
                <Terminal size={24} className="mx-auto mb-2 opacity-40" />
                <p className="text-[10px]">No files yet</p>
              </div>
            </div>
          ) : (
            renderFileTree()
          )}
        </div>
        
        {currentProject && (
          <div className="p-3 border-t border-[#1a1a2e] bg-[#08080c] text-[10px] space-y-1">
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
                onClick={() => onSetActiveTab(tab.path)}
                className={`flex items-center gap-2 px-3 h-9 border-r border-[#1a1a2e] cursor-pointer group ${
                  activeTab === tab.path ? 'bg-[#12121a] text-white' : 'text-[#64748B] hover:text-[#94a3b8]'
                }`}
              >
                <FileCode size={12} />
                <span className="text-xs font-mono truncate max-w-[120px]">{tab.path.split('/').pop()}</span>
                <button 
                  onClick={(e) => { e.stopPropagation(); onCloseTab(tab.path); }}
                  className="opacity-0 group-hover:opacity-100 hover:text-red-400 transition-opacity"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
          
          <div className="flex items-center gap-1 px-2">
            <button onClick={onTogglePreview} className={`p-1.5 rounded ${showPreview ? 'bg-purple-500/20 text-purple-400' : 'text-[#64748B] hover:text-white'}`} title="Toggle Preview">
              <Eye size={14} />
            </button>
            <button onClick={onCopy} className="p-1.5 text-[#64748B] hover:text-white rounded" title="Copy Code">
              {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
            </button>
          </div>
        </div>

        {/* Editor + Preview Split */}
        <div className="flex-1 flex overflow-hidden">
          {/* Code Editor */}
          <div className={`flex flex-col bg-[#0a0a0f] ${showPreview ? 'w-1/2' : 'flex-1'}`}>
            {activeTabContent ? (
              <div className="flex-1 overflow-auto font-mono text-sm">
                <div className="flex min-h-full">
                  {/* Line Numbers */}
                  <div className="w-12 flex-shrink-0 bg-[#08080c] text-[#3a3a4a] text-right pr-3 pt-4 select-none border-r border-[#1a1a2e]">
                    {activeTabContent.content.split('\n').map((_, i) => (
                      <div key={i} className="leading-6 text-xs">{i + 1}</div>
                    ))}
                  </div>
                  {/* Code Content */}
                  <pre className="flex-1 p-4 text-[#e4e4e7] overflow-x-auto leading-6 text-xs">
                    <code>{activeTabContent.content}</code>
                  </pre>
                </div>
              </div>
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
                      onClick={() => onSetPreviewMode(mode)}
                      className={`p-1 rounded transition-colors ${previewMode === mode ? 'bg-[#1e1e2e] text-white' : 'text-[#64748B] hover:text-[#94A3B8]'}`}
                      title={`${mode} view`}
                    >
                      {mode === 'mobile' ? <Smartphone size={12} /> : mode === 'tablet' ? <Tablet size={12} /> : <Monitor size={12} />}
                    </button>
                  ))}
                </div>
                <span className="text-[10px] text-[#4a4a5a]">Preview</span>
              </div>

              {/* Preview iframe */}
              <div className="flex-1 p-4 bg-[radial-gradient(#1e1e2e_1px,transparent_1px)] [background-size:12px_12px] flex items-start justify-center overflow-auto">
                <div className={`bg-white shadow-2xl transition-all duration-300 h-full ${
                  previewMode === 'mobile' ? 'w-[375px] rounded-2xl border-4 border-[#1e1e2e]' :
                  previewMode === 'tablet' ? 'w-[768px] rounded-xl border-2 border-[#1e1e2e]' :
                  'w-full'
                }`}>
                  <iframe
                    srcDoc={generatePreviewHTML()}
                    className="w-full h-full border-0"
                    title="Preview"
                    sandbox="allow-scripts"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right: Activity + Chat */}
      <div className="w-[280px] border-l border-[#1a1a2e] flex flex-col bg-[#0a0a10]">
        <div className="p-3 border-b border-[#1a1a2e] flex justify-between items-center">
          <span className="text-[10px] font-semibold text-[#F1F5F9] uppercase tracking-wider">Agent Activity</span>
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
                <p className="text-[10px] mt-1 opacity-60">Run to start</p>
              </div>
            ) : (
              [...activities].reverse().slice(0, 50).map((activity, idx) => {
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
                    
                    <p className={`text-[10px] leading-relaxed ${activity.content_type === 'error' ? 'text-red-400' : 'text-[#94A3B8]'}`}>
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

        {/* Chat Input */}
        <div className="p-3 border-t border-[#1a1a2e]">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Message Nicole..."
              value={chatMessage}
              onChange={(e) => onSetChatMessage(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && onSendMessage()}
              className="flex-1 px-2.5 py-1.5 bg-[#12121A] border border-[#1E1E2E] rounded text-xs text-white placeholder-[#4a4a5a] focus:outline-none focus:border-purple-500/50"
              disabled={sendingMessage}
            />
            <button
              onClick={onSendMessage}
              disabled={sendingMessage || !chatMessage.trim()}
              className="p-1.5 bg-purple-600/20 text-purple-400 rounded hover:bg-purple-600/30 disabled:opacity-50 transition-all"
            >
              {sendingMessage ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
            </button>
          </div>
        </div>
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
      <span className="truncate">{filename}</span>
    </button>
  );
}
