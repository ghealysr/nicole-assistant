import React from 'react';
import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { FileCode, Clock, Coins, ExternalLink } from 'lucide-react';
import { FazProject } from '@/types/faz';
import { StatusBadge } from './StatusBadge';

interface ProjectCardProps {
  project: FazProject;
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Link 
      href={`/faz/projects/${project.project_id}`}
      className="group block bg-[#12121A] border border-[#1E1E2E] rounded-xl overflow-hidden hover:border-[#6366F1] transition-all duration-300"
    >
      <div className="p-5">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold text-[#F1F5F9] group-hover:text-[#6366F1] transition-colors">
              {project.name}
            </h3>
            <p className="text-sm text-[#64748B] mt-1 line-clamp-1">
              {project.original_prompt}
            </p>
          </div>
          <StatusBadge status={project.status} animate />
        </div>

        <div className="grid grid-cols-3 gap-4 py-4 border-t border-[#1E1E2E]">
          <div className="flex flex-col">
            <span className="text-xs text-[#64748B] uppercase tracking-wider mb-1">Files</span>
            <div className="flex items-center text-sm text-[#F1F5F9]">
              <FileCode size={14} className="mr-1.5 text-[#6366F1]" />
              {project.file_count}
            </div>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-[#64748B] uppercase tracking-wider mb-1">Cost</span>
            <div className="flex items-center text-sm text-[#F1F5F9]">
              <Coins size={14} className="mr-1.5 text-[#22C55E]" />
              ${(project.total_cost_cents / 100).toFixed(2)}
            </div>
          </div>
          <div className="flex flex-col">
            <span className="text-xs text-[#64748B] uppercase tracking-wider mb-1">Updated</span>
            <div className="flex items-center text-sm text-[#F1F5F9]">
              <Clock size={14} className="mr-1.5 text-[#22D3EE]" />
              {formatDistanceToNow(new Date(project.updated_at), { addSuffix: true })}
            </div>
          </div>
        </div>
      </div>

      {project.preview_url && (
        <div className="bg-[#0A0A0F] px-5 py-3 flex justify-between items-center text-xs">
          <span className="text-[#64748B]">Live Preview Available</span>
          <a 
            href={project.preview_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center text-[#6366F1] hover:underline"
          >
            Open <ExternalLink size={12} className="ml-1" />
          </a>
        </div>
      )}
    </Link>
  );
}


