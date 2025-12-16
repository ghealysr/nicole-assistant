'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, Sparkles, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { fazApi } from '@/lib/faz/api';

export default function CreateProjectPage() {
  const router = useRouter();
  const [prompt, setPrompt] = React.useState('');
  const [creating, setCreating] = React.useState(false);

  const handleCreate = async () => {
    if (!prompt.trim() || creating) return;
    
    setCreating(true);
    try {
      // Extract a name from the prompt (first few words)
      const name = prompt.split(' ').slice(0, 4).join(' ') || 'New Project';
      
      const project = await fazApi.createProject(name, prompt);
      
      // Start pipeline immediately
      await fazApi.runPipeline(project.project_id, prompt);
      
      // Navigate to workspace
      router.push(`/faz/projects/${project.project_id}`);
    } catch (error) {
      console.error('Failed to create project:', error);
      setCreating(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleCreate();
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0F] text-[#F1F5F9] flex flex-col">
      <header className="h-16 border-b border-[#1E1E2E] flex items-center px-6">
        <Link href="/faz" className="flex items-center text-[#94A3B8] hover:text-white transition-colors">
          <ArrowLeft size={18} className="mr-2" />
          Back to Dashboard
        </Link>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center p-6 pb-32">
        <div className="w-full max-w-2xl animate-in fade-in slide-in-from-bottom-4 duration-500">
          <div className="text-center mb-10">
            <h1 className="text-4xl font-bold mb-3 bg-clip-text text-transparent bg-gradient-to-r from-white to-[#94A3B8]">
              What would you like to build?
            </h1>
            <p className="text-[#94A3B8]">
              Describe your idea, and Faz Code will handle the rest.
            </p>
          </div>

          <div className="bg-[#12121A] border border-[#1E1E2E] rounded-2xl p-2 shadow-2xl focus-within:border-[#6366F1] focus-within:ring-1 focus-within:ring-[#6366F1] transition-all">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Build a landing page for my AI startup called AlphaWave..."
              className="w-full h-40 bg-transparent text-[#F1F5F9] placeholder-[#475569] p-4 text-lg resize-none outline-none font-medium"
              autoFocus
            />
            <div className="flex justify-between items-center px-4 pb-2">
              <span className="text-xs text-[#64748B]">
                Cmd + Enter to create
              </span>
              <button
                onClick={handleCreate}
                disabled={!prompt.trim() || creating}
                className="flex items-center gap-2 bg-[#6366F1] hover:bg-[#5659D8] disabled:opacity-50 disabled:hover:bg-[#6366F1] text-white px-6 py-2.5 rounded-xl font-medium transition-all"
              >
                {creating ? (
                  <>
                    <Loader2 size={18} className="animate-spin" />
                    Initializing...
                  </>
                ) : (
                  <>
                    <Sparkles size={18} />
                    Create
                  </>
                )}
              </button>
            </div>
          </div>

          <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <button 
              onClick={() => setPrompt("Build a modern portfolio website with a dark theme, projects gallery, and contact form.")}
              className="text-left p-4 bg-[#12121A] hover:bg-[#1E1E2E] border border-[#1E1E2E] rounded-xl text-sm text-[#94A3B8] transition-all hover:border-[#6366F1]/50 group"
            >
              <span className="block text-[#F1F5F9] font-medium mb-1 group-hover:text-[#6366F1]">Portfolio Site</span>
              Dark theme, gallery, contact form
            </button>
            <button 
              onClick={() => setPrompt("Create a SaaS dashboard with sidebar navigation, data tables, and analytics charts.")}
              className="text-left p-4 bg-[#12121A] hover:bg-[#1E1E2E] border border-[#1E1E2E] rounded-xl text-sm text-[#94A3B8] transition-all hover:border-[#6366F1]/50 group"
            >
              <span className="block text-[#F1F5F9] font-medium mb-1 group-hover:text-[#6366F1]">SaaS Dashboard</span>
              Sidebar, tables, charts
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}

