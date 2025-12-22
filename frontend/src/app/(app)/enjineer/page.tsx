'use client';

/**
 * Enjineer Dashboard Page
 * 
 * The main entry point for the Enjineer IDE.
 * Layout: Sidebar (Files/Plan) | Main Area (Code/Preview/Terminal) | Chat (Nicole)
 * 
 * This is a Cursor-like coding environment where Nicole is the
 * conversational coding partner.
 */

import React from 'react';
import { useRouter } from 'next/navigation';
import { 
  ArrowLeft, PanelLeftClose, PanelLeft, MessageSquare, X,
  Sparkles, Image as ImageIcon, Loader2, Rocket
} from 'lucide-react';
import { Sidebar } from '@/components/enjineer/Sidebar';
import { MainArea } from '@/components/enjineer/MainArea';
import { NicoleChat } from '@/components/enjineer/NicoleChat';
import { useEnjineerStore } from '@/lib/enjineer/store';

// View states
type ViewState = 'loading' | 'intake' | 'workspace';

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
    setLoading,
    isLoading,
  } = useEnjineerStore();

  // View state management
  const [viewState, setViewState] = React.useState<ViewState>('loading');
  
  // Intake form state
  const [projectName, setProjectName] = React.useState('');
  const [projectDescription, setProjectDescription] = React.useState('');
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [referenceImage, setReferenceImage] = React.useState<File | null>(null);
  const [imagePreview, setImagePreview] = React.useState<string | null>(null);
  const [isCreating, setIsCreating] = React.useState(false);

  // Load projects from backend
  React.useEffect(() => {
    async function loadProjects() {
      try {
        setLoading(true);
        const { enjineerApi } = await import('@/lib/enjineer/api');
        
        // Try to get existing projects
        const projects = await enjineerApi.listProjects();
        
        if (projects.length > 0) {
          // Load most recent project
          const project = projects[0];
          setCurrentProject({
            id: project.id,
            name: project.name,
            description: project.description,
            status: project.status,
            createdAt: new Date(project.createdAt),
            updatedAt: new Date(project.updatedAt),
          });
          
          // Load project files
          const files = await enjineerApi.getFiles(project.id);
          setFiles(files);
          
          // Load project plan
          const plan = await enjineerApi.getPlan(project.id);
          setPlan(plan.map((s, idx) => ({
            id: s.id || String(idx),
            title: s.title,
            description: s.description || '',
            status: s.status || 'pending',
            files: s.files,
          })));
          
          setViewState('workspace');
        } else {
          // No projects exist - show intake screen
          setViewState('intake');
        }
      } catch (error) {
        console.error('[Enjineer] Failed to load projects:', error);
        // Show intake screen on error (allows creating new project)
        setViewState('intake');
      } finally {
        setLoading(false);
      }
    }
    
    loadProjects();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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

  // Handle project creation
  const handleCreateProject = async () => {
    if (!projectDescription.trim()) return;
    
    setIsCreating(true);
    try {
      const { enjineerApi } = await import('@/lib/enjineer/api');
      
      const name = projectName.trim() || 'New Project';
      const newProject = await enjineerApi.createProject(name, projectDescription);
      
      setCurrentProject({
        id: newProject.id,
        name: newProject.name,
        description: newProject.description,
        status: newProject.status,
        createdAt: newProject.createdAt,
        updatedAt: newProject.updatedAt,
      });
      
      // TODO: Upload reference image if provided
      // if (referenceImage && newProject.id) {
      //   await enjineerApi.uploadReferenceImage(newProject.id, referenceImage);
      // }
      
      setViewState('workspace');
    } catch (error) {
      console.error('[Enjineer] Failed to create project:', error);
      alert('Failed to create project. Please try again.');
    } finally {
      setIsCreating(false);
    }
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

  // Intake/Project Creation screen
  if (viewState === 'intake') {
    return (
      <div className="h-screen bg-[#0A0A0F] flex flex-col">
        {/* Header */}
        <header className="h-12 bg-[#0D0D12] border-b border-[#1E1E2E] flex items-center px-4 shrink-0">
          <button
            onClick={() => router.push('/chat')}
            className="flex items-center gap-2 text-[#64748B] hover:text-white transition-colors text-sm"
          >
            <ArrowLeft size={16} />
            <span>Back to Chat</span>
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
          <button
            onClick={() => router.push('/chat')}
            className="flex items-center gap-2 text-[#64748B] hover:text-white transition-colors text-sm"
          >
            <ArrowLeft size={16} />
            <span>Exit</span>
          </button>
          
          <div className="w-px h-6 bg-[#1E1E2E]" />
          
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#8B5CF6] to-[#6366F1] flex items-center justify-center">
              <span className="text-white font-bold text-sm">E</span>
            </div>
            <div>
              <h1 className="text-sm font-semibold text-white">
                {currentProject?.name || 'Enjineer'}
              </h1>
              <p className="text-[10px] text-[#64748B]">
                Powered by Nicole
              </p>
            </div>
          </div>
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

