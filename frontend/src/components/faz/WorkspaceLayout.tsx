import React from 'react';
import { Code2, Monitor, Columns, Menu, X, ArrowLeft } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useFazStore } from '@/lib/faz/store';
import Link from 'next/link';

interface WorkspaceLayoutProps {
  children: React.ReactNode;
  sidebar: React.ReactNode;
  rightPanel: React.ReactNode;
}

export function WorkspaceLayout({ children, sidebar, rightPanel }: WorkspaceLayoutProps) {
  const { activeTab, setActiveTab, isSidebarOpen, toggleSidebar } = useFazStore();

  return (
    <div className="flex h-screen bg-[#0A0A0F] overflow-hidden">
      {/* Sidebar */}
      <div 
        className={cn(
          "w-[280px] border-r border-[#1E1E2E] bg-[#0A0A0F] flex flex-col transition-all duration-300 ease-in-out relative z-20",
          !isSidebarOpen && "-ml-[280px]"
        )}
      >
        <div className="h-14 border-b border-[#1E1E2E] flex items-center px-4 justify-between bg-[#12121A]">
          <Link href="/faz" className="flex items-center text-[#94A3B8] hover:text-white transition-colors">
            <ArrowLeft size={16} className="mr-2" />
            <span className="font-semibold text-sm tracking-tight">FAZ CODE</span>
          </Link>
          <button onClick={toggleSidebar} className="text-[#64748B] hover:text-white">
            <X size={16} />
          </button>
        </div>
        <div className="flex-1 overflow-hidden">
          {sidebar}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header / Tabs */}
        <header className="h-14 border-b border-[#1E1E2E] bg-[#0A0A0F] flex items-center justify-between px-4">
          <div className="flex items-center gap-2">
            {!isSidebarOpen && (
              <button 
                onClick={toggleSidebar} 
                className="mr-2 p-1.5 hover:bg-[#1E1E2E] rounded-md text-[#64748B] hover:text-white"
              >
                <Menu size={16} />
              </button>
            )}
            
            <div className="flex items-center bg-[#12121A] rounded-lg p-1 border border-[#1E1E2E]">
              <button
                onClick={() => setActiveTab('code')}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                  activeTab === 'code' ? "bg-[#1E1E2E] text-white shadow-sm" : "text-[#94A3B8] hover:text-[#F1F5F9]"
                )}
              >
                <Code2 size={14} />
                Code
              </button>
              <button
                onClick={() => setActiveTab('preview')}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                  activeTab === 'preview' ? "bg-[#1E1E2E] text-white shadow-sm" : "text-[#94A3B8] hover:text-[#F1F5F9]"
                )}
              >
                <Monitor size={14} />
                Preview
              </button>
              <div className="w-[1px] h-4 bg-[#1E1E2E] mx-1" />
              <button
                onClick={() => setActiveTab('split')}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all",
                  activeTab === 'split' ? "bg-[#1E1E2E] text-white shadow-sm" : "text-[#94A3B8] hover:text-[#F1F5F9]"
                )}
              >
                <Columns size={14} />
                Split
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Additional header actions can go here */}
          </div>
        </header>

        {/* Content Area */}
        <main className="flex-1 overflow-hidden relative">
          {children}
        </main>
      </div>

      {/* Right Panel (Activity/Chat) */}
      <div className="w-[320px] border-l border-[#1E1E2E] bg-[#0A0A0F] flex flex-col z-10 shadow-xl">
        {rightPanel}
      </div>
    </div>
  );
}

