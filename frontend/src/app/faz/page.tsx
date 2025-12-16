'use client';

import React from 'react';
import Link from 'next/link';
import { Plus, Search, Rocket, Grid, List as ListIcon } from 'lucide-react';
import { ProjectCard } from '@/components/faz/ProjectCard';
import { fazApi } from '@/lib/faz/api';
import { useFazStore } from '@/lib/faz/store';
// Types imported via useFazStore

export default function FazDashboard() {
  const { projects, setProjects } = useFazStore();
  const [loading, setLoading] = React.useState(true);
  const [view, setView] = React.useState<'grid' | 'list'>('grid');
  const [search, setSearch] = React.useState('');

  React.useEffect(() => {
    const loadProjects = async () => {
      try {
        const data = await fazApi.listProjects();
        setProjects(data.projects);
      } catch (error) {
        console.error('Failed to load projects:', error);
      } finally {
        setLoading(false);
      }
    };
    loadProjects();
  }, [setProjects]);

  const filteredProjects = projects.filter(p => 
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.original_prompt.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-[#0A0A0F] text-[#F1F5F9]">
      {/* Header */}
      <header className="h-16 border-b border-[#1E1E2E] flex items-center justify-between px-6 bg-[#0A0A0F]/80 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#6366F1] to-[#818CF8] flex items-center justify-center text-white font-bold">
            <Rocket size={18} />
          </div>
          <span className="font-bold text-lg tracking-tight">FAZ CODE</span>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-full bg-[#1E1E2E] border border-[#2E2E3E]" />
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Hero Section */}
        <div className="flex flex-col md:flex-row justify-between items-end mb-12 gap-6">
          <div>
            <h1 className="text-4xl font-bold mb-3 bg-clip-text text-transparent bg-gradient-to-r from-white to-[#94A3B8]">
              Your Projects
            </h1>
            <p className="text-[#94A3B8] text-lg">
              Manage and deploy your AI-generated applications.
            </p>
          </div>
          
          <Link 
            href="/faz/new"
            className="flex items-center gap-2 bg-[#6366F1] hover:bg-[#5659D8] text-white px-6 py-3 rounded-xl font-medium transition-all shadow-lg shadow-indigo-500/20 hover:scale-[1.02] active:scale-[0.98]"
          >
            <Plus size={18} />
            New Project
          </Link>
        </div>

        {/* Toolbar */}
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 mb-8">
          <div className="relative w-full sm:w-96 group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-[#64748B] group-focus-within:text-[#6366F1] transition-colors" size={18} />
            <input
              type="text"
              placeholder="Search projects..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-[#12121A] border border-[#1E1E2E] rounded-xl py-2.5 pl-10 pr-4 text-sm text-[#F1F5F9] focus:outline-none focus:border-[#6366F1] transition-colors placeholder-[#64748B]"
            />
          </div>
          
          <div className="flex bg-[#12121A] p-1 rounded-lg border border-[#1E1E2E]">
            <button
              onClick={() => setView('grid')}
              className={`p-2 rounded-md transition-all ${view === 'grid' ? 'bg-[#1E1E2E] text-white shadow-sm' : 'text-[#64748B] hover:text-[#94A3B8]'}`}
            >
              <Grid size={18} />
            </button>
            <button
              onClick={() => setView('list')}
              className={`p-2 rounded-md transition-all ${view === 'list' ? 'bg-[#1E1E2E] text-white shadow-sm' : 'text-[#64748B] hover:text-[#94A3B8]'}`}
            >
              <ListIcon size={18} />
            </button>
          </div>
        </div>

        {/* Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-48 bg-[#12121A] rounded-xl border border-[#1E1E2E] animate-pulse" />
            ))}
          </div>
        ) : filteredProjects.length > 0 ? (
          <div className={`grid gap-6 ${view === 'grid' ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1'}`}>
            {filteredProjects.map(project => (
              <ProjectCard key={project.project_id} project={project} />
            ))}
          </div>
        ) : (
          <div className="text-center py-20 bg-[#12121A] rounded-xl border border-[#1E1E2E] border-dashed">
            <div className="w-16 h-16 bg-[#1E1E2E] rounded-full flex items-center justify-center mx-auto mb-4">
              <Rocket className="text-[#64748B]" size={32} />
            </div>
            <h3 className="text-lg font-medium text-[#F1F5F9] mb-1">No projects found</h3>
            <p className="text-[#64748B] mb-6">Start building your next idea with Faz Code.</p>
            <Link 
              href="/faz/new"
              className="inline-flex items-center gap-2 bg-[#1E1E2E] hover:bg-[#2E2E3E] text-white px-4 py-2 rounded-lg font-medium transition-colors border border-[#2E2E3E]"
            >
              Create Project
            </Link>
          </div>
        )}
      </main>
    </div>
  );
}

