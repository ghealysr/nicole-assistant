import React from 'react';
import { cn } from '@/lib/utils';
import { ProjectStatus } from '@/types/faz';

interface StatusBadgeProps {
  status: ProjectStatus;
  className?: string;
  animate?: boolean;
}

const statusConfig: Record<ProjectStatus, { color: string; label: string }> = {
  intake: { color: 'bg-gray-500 text-white', label: 'Intake' },
  planning: { color: 'bg-indigo-500 text-white', label: 'Planning' },
  researching: { color: 'bg-blue-500 text-white', label: 'Researching' },
  designing: { color: 'bg-purple-500 text-white', label: 'Designing' },
  building: { color: 'bg-yellow-500 text-white', label: 'Building' },
  processing: { color: 'bg-blue-600 text-white', label: 'Processing' },
  qa: { color: 'bg-orange-500 text-white', label: 'QA Testing' },
  review: { color: 'bg-teal-500 text-white', label: 'In Review' },
  approved: { color: 'bg-green-600 text-white', label: 'Approved' },
  deploying: { color: 'bg-cyan-600 text-white', label: 'Deploying' },
  deployed: { color: 'bg-green-500 text-white', label: 'Live' },
  failed: { color: 'bg-red-500 text-white', label: 'Failed' },
  paused: { color: 'bg-slate-600 text-white', label: 'Paused' },
  archived: { color: 'bg-gray-700 text-gray-300', label: 'Archived' },
};

export function StatusBadge({ status, className, animate = false }: StatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.intake;
  const isActive = ['planning', 'researching', 'designing', 'building', 'processing', 'qa', 'deploying'].includes(status);

  return (
    <span
      className={cn(
        'px-2.5 py-0.5 rounded-full text-xs font-medium inline-flex items-center gap-1.5',
        config.color,
        animate && isActive && 'animate-pulse',
        className
      )}
    >
      {isActive && (
        <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />
      )}
      {config.label}
    </span>
  );
}

