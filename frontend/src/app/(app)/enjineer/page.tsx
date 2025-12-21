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
import { ArrowLeft, PanelLeftClose, PanelLeft, MessageSquare, X } from 'lucide-react';
import { Sidebar } from '@/components/enjineer/Sidebar';
import { MainArea } from '@/components/enjineer/MainArea';
import { NicoleChat } from '@/components/enjineer/NicoleChat';
import { useEnjineerStore } from '@/lib/enjineer/store';

export default function EnjineerPage() {
  const router = useRouter();
  const {
    isSidebarCollapsed,
    toggleSidebar,
    isChatCollapsed,
    toggleChat,
    currentProject,
    setCurrentProject,
  } = useEnjineerStore();

  const {
    setFiles,
    setPlan,
    setLoading,
  } = useEnjineerStore();

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
        } else {
          // No projects, show welcome state
          setCurrentProject(null);
        }
      } catch (error) {
        console.error('[Enjineer] Failed to load projects:', error);
        // Set to demo mode if backend unavailable
        if (!currentProject) {
          setCurrentProject({
            id: 0,
            name: 'New Project',
            description: 'Start building with Nicole',
            status: 'draft',
            createdAt: new Date(),
            updatedAt: new Date(),
          });
        }
      } finally {
        setLoading(false);
      }
    }
    
    loadProjects();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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

