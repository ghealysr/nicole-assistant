import React from 'react';
import { cn } from '@/lib/utils';
import { ProjectStatus } from '@/types/faz';

interface StatusBadgeProps {
  status: ProjectStatus;
  className?: string;
  animate?: boolean;
}

const statusConfig: Record<ProjectStatus, { bg: string; text: string; label: string; glow?: string }> = {
  intake: { bg: 'bg-[#2a2a3a]/60', text: 'text-[#94A3B8]', label: 'Intake' },
  planning: { bg: 'bg-indigo-500/20', text: 'text-indigo-400', label: 'Planning', glow: 'shadow-indigo-500/20' },
  researching: { bg: 'bg-blue-500/20', text: 'text-blue-400', label: 'Researching', glow: 'shadow-blue-500/20' },
  designing: { bg: 'bg-pink-500/20', text: 'text-pink-400', label: 'Designing', glow: 'shadow-pink-500/20' },
  building: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', label: 'Building', glow: 'shadow-yellow-500/20' },
  processing: { bg: 'bg-amber-500/20', text: 'text-amber-400', label: 'Processing', glow: 'shadow-amber-500/20' },
  qa: { bg: 'bg-orange-500/20', text: 'text-orange-400', label: 'QA Testing', glow: 'shadow-orange-500/20' },
  review: { bg: 'bg-cyan-500/20', text: 'text-cyan-400', label: 'Review', glow: 'shadow-cyan-500/20' },
  approved: { bg: 'bg-green-500/20', text: 'text-green-400', label: 'Approved', glow: 'shadow-green-500/20' },
  deploying: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', label: 'Deploying', glow: 'shadow-emerald-500/20' },
  deployed: { bg: 'bg-green-500/30', text: 'text-green-300', label: 'Live ✓', glow: 'shadow-green-500/30' },
  failed: { bg: 'bg-red-500/20', text: 'text-red-400', label: 'Failed' },
  paused: { bg: 'bg-slate-500/20', text: 'text-slate-400', label: 'Paused' },
  archived: { bg: 'bg-gray-500/20', text: 'text-gray-500', label: 'Archived' },
};

export function StatusBadge({ status, className, animate = false }: StatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.intake;
  const isActive = ['planning', 'researching', 'designing', 'building', 'processing', 'qa', 'deploying', 'review'].includes(status);

  return (
    <span
      className={cn(
        'px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wider inline-flex items-center gap-1.5 border',
        config.bg,
        config.text,
        isActive && config.glow && `shadow-lg ${config.glow}`,
        isActive ? 'border-current/30' : 'border-transparent',
        animate && isActive && 'animate-pulse',
        className
      )}
    >
      {isActive && (
        <span className="relative flex h-1.5 w-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75" />
          <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-current" />
        </span>
      )}
      {config.label}
    </span>
  );
}

