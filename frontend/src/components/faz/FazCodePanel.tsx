'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, Plus, Folder, Play, Pause, Loader2, Code2, ChevronRight } from 'lucide-react';
import { useFazStore } from '@/lib/faz/store';
import { fazApi } from '@/lib/faz/api';
import { FazProject } from '@/types/faz';
import { StatusBadge } from './StatusBadge';
import { FileTree } from './FileTree';
import { CodeViewer } from './CodeViewer';
import { AgentActivityFeed } from './AgentActivityFeed';

interface FazCodePanelProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Faz Code Panel - Slide-in AI coding dashboard.
 * 
 * Features:
 * - Resizable panel (600px - 1200px)
 * - Project list view
 * - Workspace view with code editor, preview, and activity feed
 * - Real-time WebSocket updates for agent activity
 */
export function FazCodePanel({ isOpen, onClose }: FazCodePanelProps) {
  const [panelWidth, setPanelWidth] = useState(900);
  const [isResizing, setIsResizing] = useState(false);
  const [view, setView] = useState<'projects' | 'workspace'>('projects');
  const [projects, setProjects] = useState<FazProject[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectPrompt, setNewProjectPrompt] = useState('');
  
  const resizeRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(900);

  const MIN_WIDTH = 600;
  const MAX_WIDTH = 1200;

  const { 
    currentProject, 
    setCurrentProject, 
    files,
    fileMetadata,
    activities, 
    selectedFile,
    selectFile,
  } = useFazStore();

  // Fetch projects on open
  useEffect(() => {
    if (isOpen) {
      fetchProjects();
    }
  }, [isOpen]);

  const fetchProjects = async () => {
    setLoading(true);
    try {
      const data = await fazApi.listProjects();
      setProjects(data);
    } catch (error) {
      console.error('Failed to fetch projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim() || !newProjectPrompt.trim()) return;
    
    setCreating(true);
    try {
      const project = await fazApi.createProject(newProjectName, newProjectPrompt);
      setProjects(prev => [project, ...prev]);
      setNewProjectName('');
      setNewProjectPrompt('');
      // Open the new project
      handleSelectProject(project);
    } catch (error) {
      console.error('Failed to create project:', error);
    } finally {
      setCreating(false);
    }
  };

  const handleSelectProject = async (project: FazProject) => {
    setCurrentProject(project);
    setView('workspace');
    
    // Fetch project files
    try {
      const projectFiles = await fazApi.getProjectFiles(project.project_id);
      useFazStore.getState().setFiles(projectFiles);
    } catch (error) {
      console.error('Failed to fetch project files:', error);
    }
  };

  const handleBackToProjects = () => {
    setView('projects');
    setCurrentProject(null);
  };

  const handleRunPipeline = async () => {
    if (!currentProject) return;
    try {
      await fazApi.runPipeline(currentProject.project_id);
    } catch (error) {
      console.error('Failed to run pipeline:', error);
    }
  };

  const handleStopPipeline = async () => {
    if (!currentProject) return;
    try {
      await fazApi.stopPipeline(currentProject.project_id);
    } catch (error) {
      console.error('Failed to stop pipeline:', error);
    }
  };

  // Resize handlers
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

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  // Get selected file content from the Map
  const selectedFileContent = selectedFile 
    ? files.get(selectedFile) || ''
    : '';

  // Convert files Map to array for FileTree
  const filesArray = Array.from(fileMetadata.values());

  const isPipelineRunning = currentProject?.status && 
    ['planning', 'researching', 'designing', 'building', 'qa'].includes(currentProject.status);

  return (
    <div
      className={`fixed top-0 right-0 h-full bg-[#0A0A0F] border-l border-[#1E1E2E] shadow-2xl z-50 
        transition-transform duration-300 ease-in-out flex flex-col
        ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
      style={{ width: panelWidth }}
    >
      {/* Resize handle */}
      <div
        ref={resizeRef}
        className="absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize hover:bg-purple-500/50 transition-colors z-10"
        onMouseDown={handleMouseDown}
      />

      {/* Header */}
      <div className="h-14 border-b border-[#1E1E2E] flex items-center justify-between px-4 bg-[#12121A] shrink-0">
        <div className="flex items-center gap-3">
          {view === 'workspace' && (
            <button
              onClick={handleBackToProjects}
              className="p-1.5 hover:bg-[#1E1E2E] rounded-md text-[#64748B] hover:text-white transition-colors"
            >
              <ChevronRight size={16} className="rotate-180" />
            </button>
          )}
          <Code2 size={20} className="text-purple-400" />
          <span className="font-semibold text-white tracking-tight">
            {view === 'projects' ? 'Faz Code' : currentProject?.name || 'Project'}
          </span>
          {currentProject && (
            <StatusBadge status={currentProject.status} />
          )}
        </div>
        <div className="flex items-center gap-2">
          {view === 'workspace' && currentProject && (
            <>
              {isPipelineRunning ? (
                <button
                  onClick={handleStopPipeline}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-red-500/20 text-red-400 rounded-md text-xs font-medium hover:bg-red-500/30 transition-colors"
                >
                  <Pause size={14} />
                  Stop
                </button>
              ) : (
                <button
                  onClick={handleRunPipeline}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-500/20 text-purple-400 rounded-md text-xs font-medium hover:bg-purple-500/30 transition-colors"
                >
                  <Play size={14} />
                  Run
                </button>
              )}
            </>
          )}
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-[#1E1E2E] rounded-md text-[#64748B] hover:text-white transition-colors"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {view === 'projects' ? (
          /* Projects List View */
          <div className="h-full flex flex-col">
            {/* New Project Form */}
            <div className="p-4 border-b border-[#1E1E2E] bg-[#0A0A0F]">
              <div className="space-y-3">
                <input
                  type="text"
                  placeholder="Project name..."
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3 py-2 bg-[#12121A] border border-[#1E1E2E] rounded-md text-white text-sm placeholder-[#64748B] focus:outline-none focus:border-purple-500/50"
                />
                <textarea
                  placeholder="Describe what you want to build..."
                  value={newProjectPrompt}
                  onChange={(e) => setNewProjectPrompt(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 bg-[#12121A] border border-[#1E1E2E] rounded-md text-white text-sm placeholder-[#64748B] focus:outline-none focus:border-purple-500/50 resize-none"
                />
                <button
                  onClick={handleCreateProject}
                  disabled={creating || !newProjectName.trim() || !newProjectPrompt.trim()}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-purple-600 text-white rounded-md text-sm font-medium hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {creating ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <Plus size={16} />
                  )}
                  Create Project
                </button>
              </div>
            </div>

            {/* Projects List */}
            <div className="flex-1 overflow-y-auto p-4">
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 size={24} className="animate-spin text-purple-400" />
                </div>
              ) : projects.length === 0 ? (
                <div className="text-center py-12 text-[#64748B]">
                  <Folder size={40} className="mx-auto mb-3 opacity-50" />
                  <p className="text-sm">No projects yet</p>
                  <p className="text-xs mt-1">Create your first AI-powered project above</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {projects.map((project) => (
                    <button
                      key={project.project_id}
                      onClick={() => handleSelectProject(project)}
                      className="w-full p-4 bg-[#12121A] border border-[#1E1E2E] rounded-lg text-left hover:border-purple-500/30 transition-colors group"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <span className="font-medium text-white group-hover:text-purple-300 transition-colors">
                          {project.name}
                        </span>
                        <StatusBadge status={project.status} />
                      </div>
                      <p className="text-xs text-[#64748B] line-clamp-2 mb-2">
                        {project.original_prompt}
                      </p>
                      <div className="flex items-center gap-4 text-xs text-[#475569]">
                        <span>{project.file_count} files</span>
                        <span>{project.total_tokens_used.toLocaleString()} tokens</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Workspace View */
          <div className="h-full flex">
            {/* File Tree */}
            <div className="w-[200px] border-r border-[#1E1E2E] overflow-y-auto bg-[#0A0A0F]">
              <div className="p-2 border-b border-[#1E1E2E]">
                <span className="text-xs font-medium text-[#64748B] uppercase tracking-wider">Files</span>
              </div>
              <FileTree 
                files={filesArray} 
                selectedFile={selectedFile}
                onSelectFile={selectFile}
              />
            </div>

            {/* Code / Preview Area */}
            <div className="flex-1 flex flex-col min-w-0">
              {selectedFile ? (
                <CodeViewer
                  code={selectedFileContent}
                  language={selectedFile.split('.').pop() || 'typescript'}
                  filename={selectedFile}
                />
              ) : (
                <div className="flex-1 flex items-center justify-center text-[#64748B]">
                  <div className="text-center">
                    <Code2 size={40} className="mx-auto mb-3 opacity-50" />
                    <p className="text-sm">Select a file to view code</p>
                    <p className="text-xs mt-1">or wait for the build to generate files</p>
                  </div>
                </div>
              )}
            </div>

            {/* Activity Feed */}
            <div className="w-[260px] border-l border-[#1E1E2E] overflow-hidden flex flex-col bg-[#0A0A0F]">
              <div className="p-3 border-b border-[#1E1E2E]">
                <span className="text-xs font-medium text-[#64748B] uppercase tracking-wider">Activity</span>
              </div>
              <div className="flex-1 overflow-y-auto">
                <AgentActivityFeed activities={activities} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

