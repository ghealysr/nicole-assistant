'use client';

/**
 * Enjineer Dashboard Page
 * 
 * The main entry point for the Enjineer IDE.
 * Layout: Sidebar (Files/Plan) | Main Area (Code/Preview/Terminal) | Chat (Nicole)
 * 
 * This is a Cursor-like coding environment where Nicole is the
 * conversational coding partner.
 * 
 * View States:
 * - loading: Initial load
 * - projects: Show all projects (can switch or create new)
 * - intake: Create new project form
 * - workspace: Main IDE view
 */

import React from 'react';
import { useRouter } from 'next/navigation';
import { 
  ArrowLeft, PanelLeftClose, PanelLeft, MessageSquare, X,
  Sparkles, Image as ImageIcon, Loader2, Rocket, FolderOpen,
  Plus, Clock, ChevronRight, Grid3X3
} from 'lucide-react';
import { Sidebar } from '@/components/enjineer/Sidebar';
import { MainArea } from '@/components/enjineer/MainArea';
import { NicoleChat } from '@/components/enjineer/NicoleChat';
import { useEnjineerStore } from '@/lib/enjineer/store';

// View states
type ViewState = 'loading' | 'projects' | 'intake' | 'workspace';

// Cached project list type
interface ProjectListItem {
  id: number;
  name: string;
  description: string | undefined;
  status: string;
  createdAt: Date;
  updatedAt: Date;
}

export default function EnjineerPage() {
  const router = useRouter();
  const {
    isSidebarCollapsed,
    toggleSidebar,
    isChatCollapsed,
    toggleChat,
    currentProject,
    setCurrentProject,
    setFiles,
    setPlan,
    setPlanOverview,
    setLoading,
    isLoading,
    clearMessages,
  } = useEnjineerStore();

  // View state management
  const [viewState, setViewState] = React.useState<ViewState>('loading');
  
  // Project list state
  const [projects, setProjects] = React.useState<ProjectListItem[]>([]);
  
  // Intake form state
  const [projectName, setProjectName] = React.useState('');
  const [projectDescription, setProjectDescription] = React.useState('');
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [referenceImage, setReferenceImage] = React.useState<File | null>(null);
  const [imagePreview, setImagePreview] = React.useState<string | null>(null);
  const [isCreating, setIsCreating] = React.useState(false);

  /**
   * Load all projects from backend.
   * Called on initial mount and after creating a project.
   */
  const loadProjectList = React.useCallback(async () => {
    try {
      const { enjineerApi } = await import('@/lib/enjineer/api');
      const projectList = await enjineerApi.listProjects();
      
      setProjects(projectList.map(p => ({
        id: p.id,
        name: p.name,
        description: p.description,
        status: p.status,
        createdAt: new Date(p.createdAt),
        updatedAt: new Date(p.updatedAt),
      })));
      
      return projectList;
    } catch (error) {
      console.error('[Enjineer] Failed to load projects:', error);
      return [];
    }
  }, []);

  /**
   * Load a specific project into the workspace.
   */
  const loadProject = React.useCallback(async (project: ProjectListItem) => {
    try {
      setLoading(true);
      const { enjineerApi } = await import('@/lib/enjineer/api');
      
      // Set current project
      setCurrentProject({
        id: project.id,
        name: project.name,
        description: project.description,
        status: project.status,
        createdAt: project.createdAt,
        updatedAt: project.updatedAt,
      });
      
      // Clear previous chat messages
      clearMessages();
      
      // Load project files
      const files = await enjineerApi.getFiles(project.id);
      setFiles(files);
      
      // Load project plan with full phase data
      const { overview, phases } = await enjineerApi.getPlan(project.id);
      setPlanOverview(overview);
      setPlan(phases);
      
      setViewState('workspace');
    } catch (error) {
      console.error('[Enjineer] Failed to load project:', error);
      alert('Failed to load project. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [setLoading, setCurrentProject, clearMessages, setFiles, setPlan, setPlanOverview]);

  // Initial load
  React.useEffect(() => {
    async function init() {
      setLoading(true);
      const projectList = await loadProjectList();
      
      if (projectList.length === 0) {
        // No projects - show intake screen
        setViewState('intake');
      } else {
        // Show project list to choose
        setViewState('projects');
      }
      setLoading(false);
    }
    
    init();
  }, [loadProjectList, setLoading]);

  // Handle image upload
  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setReferenceImage(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  // Handle showing new project form
  const handleNewProject = () => {
    setProjectName('');
    setProjectDescription('');
    setReferenceImage(null);
    setImagePreview(null);
    setViewState('intake');
  };

  // Handle project creation
  const handleCreateProject = async () => {
    if (!projectDescription.trim()) return;
    
    setIsCreating(true);
    try {
      const { enjineerApi } = await import('@/lib/enjineer/api');
      
      const name = projectName.trim() || 'New Project';
      
      // Collect inspiration images as base64 data URLs
      const inspirationImages: string[] = [];
      if (imagePreview) {
        inspirationImages.push(imagePreview);
      }
      
      const newProject = await enjineerApi.createProject(
        name, 
        projectDescription,
        inspirationImages.length > 0 ? inspirationImages : undefined
      );
      
      // Clear messages for fresh start
      clearMessages();
      
      setCurrentProject({
        id: newProject.id,
        name: newProject.name,
        description: newProject.description,
        status: newProject.status,
        createdAt: newProject.createdAt,
        updatedAt: newProject.updatedAt,
      });
      
      // Refresh project list
      await loadProjectList();
      
      setViewState('workspace');
    } catch (error) {
      console.error('[Enjineer] Failed to create project:', error);
      alert('Failed to create project. Please try again.');
    } finally {
      setIsCreating(false);
    }
  };

  // Handle going back to project list from workspace
  const handleSwitchProject = async () => {
    await loadProjectList();
    setViewState('projects');
  };

  // Loading state
  if (viewState === 'loading' || isLoading) {
    return (
      <div className="h-screen bg-[#0A0A0F] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-[#8B5CF6] to-[#6366F1] flex items-center justify-center animate-pulse">
            <Sparkles size={28} className="text-white" />
          </div>
          <p className="text-[#94A3B8] text-sm">Loading Enjineer...</p>
        </div>
      </div>
    );
  }

  // Project List view - select or create projects
  if (viewState === 'projects') {
    return (
      <div className="h-screen bg-[#0A0A0F] flex flex-col">
        {/* Header */}
        <header className="h-14 bg-[#0D0D12] border-b border-[#1E1E2E] flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-4">
            <button
              onClick={() => router.push('/chat')}
              className="flex items-center gap-2 text-[#64748B] hover:text-white transition-colors text-sm"
            >
              <ArrowLeft size={16} />
              <span>Back</span>
            </button>
            <div className="w-px h-6 bg-[#1E1E2E]" />
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#8B5CF6] to-[#6366F1] flex items-center justify-center">
                <Grid3X3 size={16} className="text-white" />
              </div>
              <h1 className="text-lg font-semibold text-white">Projects</h1>
            </div>
          </div>
          
          <button
            onClick={handleNewProject}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#8B5CF6] to-[#6366F1] hover:from-[#7C3AED] hover:to-[#5558DD] rounded-lg text-white font-medium text-sm transition-all"
          >
            <Plus size={16} />
            New Project
          </button>
        </header>

        {/* Project Grid */}
        <div className="flex-1 overflow-auto p-6">
          {projects.length === 0 ? (
            // Empty state
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md">
                <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-[#12121A] border border-[#1E1E2E] flex items-center justify-center">
                  <FolderOpen size={36} className="text-[#64748B]" />
                </div>
                <h2 className="text-xl font-semibold text-white mb-2">No projects yet</h2>
                <p className="text-[#94A3B8] mb-6">
                  Create your first project and let Nicole help you build it.
                </p>
                <button
                  onClick={handleNewProject}
                  className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-[#8B5CF6] to-[#6366F1] hover:from-[#7C3AED] hover:to-[#5558DD] rounded-xl text-white font-medium transition-all"
                >
                  <Plus size={18} />
                  Create Project
                </button>
              </div>
            </div>
          ) : (
            // Project cards grid
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 max-w-7xl mx-auto">
              {projects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => loadProject(project)}
                  className="group text-left bg-[#12121A] border border-[#1E1E2E] hover:border-[#8B5CF6]/50 rounded-xl p-5 transition-all hover:shadow-lg hover:shadow-[#8B5CF6]/5"
                >
                  {/* Project Icon */}
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#8B5CF6]/20 to-[#6366F1]/20 border border-[#8B5CF6]/30 flex items-center justify-center mb-4 group-hover:border-[#8B5CF6]/50 transition-colors">
                    <Sparkles size={20} className="text-[#8B5CF6]" />
                  </div>
                  
                  {/* Project Name */}
                  <h3 className="font-semibold text-white mb-1 group-hover:text-[#8B5CF6] transition-colors truncate">
                    {project.name}
                  </h3>
                  
                  {/* Description */}
                  <p className="text-sm text-[#94A3B8] line-clamp-2 mb-4 min-h-[40px]">
                    {project.description || 'No description'}
                  </p>
                  
                  {/* Footer */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-xs text-[#64748B]">
                      <Clock size={12} />
                      <span>
                        {project.updatedAt.toLocaleDateString(undefined, { 
                          month: 'short', 
                          day: 'numeric' 
                        })}
                      </span>
                    </div>
                    
                    <div className="flex items-center gap-1 text-[#8B5CF6] opacity-0 group-hover:opacity-100 transition-opacity">
                      <span className="text-xs font-medium">Open</span>
                      <ChevronRight size={14} />
                    </div>
                  </div>
                  
                  {/* Status badge */}
                  <div className="mt-3 pt-3 border-t border-[#1E1E2E]">
                    <span className={`
                      inline-flex items-center px-2 py-0.5 rounded text-xs font-medium
                      ${project.status === 'active' ? 'bg-green-500/10 text-green-400' :
                        project.status === 'complete' ? 'bg-blue-500/10 text-blue-400' :
                        'bg-[#8B5CF6]/10 text-[#8B5CF6]'}
                    `}>
                      {project.status || 'New'}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // Intake/Project Creation screen
  if (viewState === 'intake') {
    return (
      <div className="h-screen bg-[#0A0A0F] flex flex-col">
        {/* Header */}
        <header className="h-12 bg-[#0D0D12] border-b border-[#1E1E2E] flex items-center px-4 shrink-0">
          <button
            onClick={() => projects.length > 0 ? setViewState('projects') : router.push('/chat')}
            className="flex items-center gap-2 text-[#64748B] hover:text-white transition-colors text-sm"
          >
            <ArrowLeft size={16} />
            <span>{projects.length > 0 ? 'Back to Projects' : 'Back to Chat'}</span>
          </button>
        </header>

        {/* Intake Form */}
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="max-w-2xl w-full">
            {/* Logo & Title */}
            <div className="text-center mb-10">
              <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-[#8B5CF6] to-[#6366F1] flex items-center justify-center shadow-lg shadow-[#8B5CF6]/25">
                <Sparkles size={36} className="text-white" />
              </div>
              <h1 className="text-3xl font-bold text-white mb-2">
                Welcome to Enjineer
              </h1>
              <p className="text-[#94A3B8] text-lg">
                Tell Nicole what you want to build
              </p>
            </div>

            {/* Form */}
            <div className="space-y-6">
              {/* Project Name (Optional) */}
              <div>
                <label className="block text-sm font-medium text-[#94A3B8] mb-2">
                  Project Name <span className="text-[#64748B]">(optional)</span>
                </label>
                <input
                  type="text"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  placeholder="My Awesome App"
                  className="w-full bg-[#12121A] border border-[#1E1E2E] rounded-xl px-4 py-3 text-white placeholder-[#64748B] focus:outline-none focus:border-[#8B5CF6] transition-colors"
                />
              </div>

              {/* Description/Prompt */}
              <div>
                <label className="block text-sm font-medium text-[#94A3B8] mb-2">
                  What do you want to build? <span className="text-[#8B5CF6]">*</span>
                </label>
                <textarea
                  value={projectDescription}
                  onChange={(e) => setProjectDescription(e.target.value)}
                  placeholder="Describe your project in detail. For example: 'A modern SaaS landing page with a hero section, pricing table, testimonials, and a contact form. Use a dark theme with purple accents.'"
                  rows={5}
                  className="w-full bg-[#12121A] border border-[#1E1E2E] rounded-xl px-4 py-3 text-white placeholder-[#64748B] focus:outline-none focus:border-[#8B5CF6] transition-colors resize-none"
                />
              </div>

              {/* Reference Image Upload */}
              <div>
                <label className="block text-sm font-medium text-[#94A3B8] mb-2">
                  Reference Image <span className="text-[#64748B]">(optional)</span>
                </label>
                <div className="relative">
                  {imagePreview ? (
                    <div className="relative rounded-xl overflow-hidden border border-[#1E1E2E]">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img 
                        src={imagePreview} 
                        alt="Reference" 
                        className="w-full h-48 object-cover"
                      />
                      <button
                        onClick={() => {
                          setReferenceImage(null);
                          setImagePreview(null);
                        }}
                        className="absolute top-2 right-2 p-1.5 bg-black/60 hover:bg-black/80 rounded-lg text-white transition-colors"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  ) : (
                    <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-[#1E1E2E] rounded-xl cursor-pointer hover:border-[#8B5CF6]/50 transition-colors bg-[#12121A]/50">
                      <div className="flex flex-col items-center justify-center py-4">
                        <div className="w-10 h-10 rounded-full bg-[#1E1E2E] flex items-center justify-center mb-2">
                          <ImageIcon size={20} className="text-[#64748B]" />
                        </div>
                        <p className="text-sm text-[#64748B]">
                          Drop an image or <span className="text-[#8B5CF6]">browse</span>
                        </p>
                        <p className="text-xs text-[#4B5563] mt-1">
                          Upload a design mockup, screenshot, or inspiration
                        </p>
                      </div>
                      <input 
                        type="file" 
                        accept="image/*" 
                        className="hidden" 
                        onChange={handleImageUpload}
                      />
                    </label>
                  )}
                </div>
              </div>

              {/* Submit Button */}
              <button
                onClick={handleCreateProject}
                disabled={!projectDescription.trim() || isCreating}
                className="w-full py-4 bg-gradient-to-r from-[#8B5CF6] to-[#6366F1] hover:from-[#7C3AED] hover:to-[#5558DD] disabled:opacity-50 disabled:cursor-not-allowed rounded-xl text-white font-semibold text-lg flex items-center justify-center gap-3 transition-all shadow-lg shadow-[#8B5CF6]/25"
              >
                {isCreating ? (
                  <>
                    <Loader2 size={20} className="animate-spin" />
                    Creating Project...
                  </>
                ) : (
                  <>
                    <Rocket size={20} />
                    Start Building
                  </>
                )}
              </button>

              {/* Hint */}
              <p className="text-center text-xs text-[#64748B]">
                Nicole will help you plan and build your project step by step
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Workspace view (main dashboard)
  return (
    <div className="h-screen bg-[#0A0A0F] flex flex-col overflow-hidden">
      {/* Top Bar */}
      <header className="h-12 bg-[#0D0D12] border-b border-[#1E1E2E] flex items-center justify-between px-4 shrink-0">
        {/* Left: Navigation & Project */}
        <div className="flex items-center gap-4">
          {/* Switch Project Button */}
          <button
            onClick={handleSwitchProject}
            className="flex items-center gap-2 text-[#64748B] hover:text-white transition-colors text-sm group"
            title="Switch Project"
          >
            <Grid3X3 size={16} />
            <span className="hidden sm:inline">Projects</span>
          </button>
          
          <div className="w-px h-6 bg-[#1E1E2E]" />
          
          {/* Current Project */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#8B5CF6] to-[#6366F1] flex items-center justify-center">
              <Sparkles size={14} className="text-white" />
            </div>
            <div>
              <h1 className="text-sm font-semibold text-white max-w-[200px] truncate">
                {currentProject?.name || 'Enjineer'}
              </h1>
              <p className="text-[10px] text-[#64748B]">
                Powered by Nicole
              </p>
            </div>
          </div>
          
          <div className="w-px h-6 bg-[#1E1E2E] hidden sm:block" />
          
          {/* New Project Button */}
          <button
            onClick={handleNewProject}
            className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs text-[#64748B] hover:text-white hover:bg-[#1E1E2E] rounded-lg transition-colors"
            title="New Project"
          >
            <Plus size={14} />
            <span>New</span>
          </button>
        </div>

        {/* Right: Panel Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={toggleSidebar}
            className="p-2 text-[#64748B] hover:text-white hover:bg-[#1E1E2E] rounded-lg transition-colors"
            title={isSidebarCollapsed ? 'Show sidebar' : 'Hide sidebar'}
          >
            {isSidebarCollapsed ? <PanelLeft size={18} /> : <PanelLeftClose size={18} />}
          </button>
          <button
            onClick={toggleChat}
            className="p-2 text-[#64748B] hover:text-white hover:bg-[#1E1E2E] rounded-lg transition-colors"
            title={isChatCollapsed ? 'Show chat' : 'Hide chat'}
          >
            {isChatCollapsed ? <MessageSquare size={18} /> : <X size={18} />}
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Files & Plan */}
        <Sidebar />

        {/* Center - Editor/Preview/Terminal */}
        <MainArea />

        {/* Right - Nicole Chat */}
        <NicoleChat />
      </div>
    </div>
  );
}

