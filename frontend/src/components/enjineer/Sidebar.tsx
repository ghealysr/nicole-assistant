'use client';

/**
 * Enjineer Sidebar Component
 * 
 * Left panel containing:
 * - Files tab: File tree browser
 * - Plan tab: Nicole's plan steps
 */

import React from 'react';
import { cn } from '@/lib/utils';
import { 
  FileCode, ListChecks, ChevronRight, ChevronDown,
  FolderOpen, Folder, File, FileJson, FileType,
  CheckCircle2, Circle, Loader2
} from 'lucide-react';
import { useEnjineerStore, PlanStep } from '@/lib/enjineer/store';

export function Sidebar() {
  const {
    sidebarTab,
    setSidebarTab,
    files,
    selectedFile,
    selectFile,
    openFile,
    plan,
    isSidebarCollapsed,
  } = useEnjineerStore();

  if (isSidebarCollapsed) {
    return null;
  }

  return (
    <div className="w-64 bg-[#0D0D12] border-r border-[#1E1E2E] flex flex-col h-full">
      {/* Tab Headers */}
      <div className="flex border-b border-[#1E1E2E]">
        <button
          onClick={() => setSidebarTab('files')}
          className={cn(
            "flex-1 px-4 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-2",
            sidebarTab === 'files'
              ? "text-[#F1F5F9] border-b-2 border-[#8B5CF6]"
              : "text-[#64748B] hover:text-[#94A3B8]"
          )}
        >
          <FileCode size={16} />
          Files
        </button>
        <button
          onClick={() => setSidebarTab('plan')}
          className={cn(
            "flex-1 px-4 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-2",
            sidebarTab === 'plan'
              ? "text-[#F1F5F9] border-b-2 border-[#8B5CF6]"
              : "text-[#64748B] hover:text-[#94A3B8]"
          )}
        >
          <ListChecks size={16} />
          Plan
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {sidebarTab === 'files' ? (
          <FileTree 
            files={Array.from(files.keys())}
            selectedFile={selectedFile}
            onSelectFile={(path) => {
              selectFile(path);
              openFile(path);
            }}
          />
        ) : (
          <PlanView plan={plan} />
        )}
      </div>
    </div>
  );
}

// File Tree Component
interface FileTreeProps {
  files: string[];
  selectedFile: string | null;
  onSelectFile: (path: string) => void;
}

interface TreeNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  children?: Record<string, TreeNode>;
}

function FileTree({ files, selectedFile, onSelectFile }: FileTreeProps) {
  const [expanded, setExpanded] = React.useState<Set<string>>(
    new Set(['app', 'components', 'lib', 'src'])
  );

  // Build tree structure
  const tree: Record<string, TreeNode> = {};
  
  files.forEach(path => {
    const parts = path.split('/');
    let current = tree;
    
    parts.forEach((part, idx) => {
      const isFile = idx === parts.length - 1;
      const fullPath = parts.slice(0, idx + 1).join('/');
      
      if (!current[part]) {
        current[part] = {
          name: part,
          path: fullPath,
          type: isFile ? 'file' : 'folder',
          children: isFile ? undefined : {}
        };
      }
      
      if (!isFile && current[part].children) {
        current = current[part].children!;
      }
    });
  });

  const toggleFolder = (path: string) => {
    const newExpanded = new Set(expanded);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpanded(newExpanded);
  };

  const getFileIcon = (name: string) => {
    if (name.endsWith('.tsx') || name.endsWith('.ts')) 
      return <FileCode size={14} className="text-blue-400" />;
    if (name.endsWith('.css')) 
      return <FileType size={14} className="text-pink-400" />;
    if (name.endsWith('.json')) 
      return <FileJson size={14} className="text-yellow-400" />;
    return <File size={14} className="text-[#64748B]" />;
  };

  const renderNode = (node: TreeNode, level: number = 0) => {
    const isExpanded = expanded.has(node.path);
    const isSelected = selectedFile === node.path;
    const paddingLeft = level * 12 + 12;

    if (node.type === 'folder') {
      return (
        <div key={node.path}>
          <div
            className="flex items-center py-1.5 px-2 hover:bg-[#1E1E2E] cursor-pointer text-sm text-[#94A3B8] select-none"
            style={{ paddingLeft }}
            onClick={() => toggleFolder(node.path)}
          >
            {isExpanded ? (
              <ChevronDown size={14} className="mr-1 text-[#64748B]" />
            ) : (
              <ChevronRight size={14} className="mr-1 text-[#64748B]" />
            )}
            {isExpanded ? (
              <FolderOpen size={14} className="mr-2 text-[#8B5CF6]" />
            ) : (
              <Folder size={14} className="mr-2 text-[#8B5CF6]" />
            )}
            <span className="truncate">{node.name}</span>
          </div>
          {isExpanded && node.children && (
            <div>
              {Object.values(node.children)
                .sort((a, b) => {
                  if (a.type === b.type) return a.name.localeCompare(b.name);
                  return a.type === 'folder' ? -1 : 1;
                })
                .map(child => renderNode(child, level + 1))}
            </div>
          )}
        </div>
      );
    }

    return (
      <div
        key={node.path}
        className={cn(
          "flex items-center py-1.5 px-2 cursor-pointer text-sm select-none transition-colors",
          isSelected
            ? "bg-[#1E1E2E] text-white border-l-2 border-[#8B5CF6]"
            : "text-[#94A3B8] hover:bg-[#12121A] hover:text-[#F1F5F9] border-l-2 border-transparent"
        )}
        style={{ paddingLeft: paddingLeft + 14 }}
        onClick={() => onSelectFile(node.path)}
      >
        <span className="mr-2">{getFileIcon(node.name)}</span>
        <span className="truncate">{node.name}</span>
      </div>
    );
  };

  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-[#64748B] p-6 text-center">
        <FileCode size={32} className="mb-3 opacity-50" />
        <p className="text-sm">No files yet</p>
        <p className="text-xs mt-1">Ask Nicole to create a project</p>
      </div>
    );
  }

  return (
    <div className="py-2">
      {Object.values(tree)
        .sort((a, b) => {
          if (a.type === b.type) return a.name.localeCompare(b.name);
          return a.type === 'folder' ? -1 : 1;
        })
        .map(node => renderNode(node))}
    </div>
  );
}

// Plan View Component
interface PlanViewProps {
  plan: PlanStep[];
}

function PlanView({ plan }: PlanViewProps) {
  if (plan.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-[#64748B] p-6 text-center">
        <ListChecks size={32} className="mb-3 opacity-50" />
        <p className="text-sm">No plan yet</p>
        <p className="text-xs mt-1">Nicole will create a plan when you start a project</p>
      </div>
    );
  }

  const getStatusIcon = (status: PlanStep['status']) => {
    switch (status) {
      case 'complete':
        return <CheckCircle2 size={16} className="text-green-500" />;
      case 'in_progress':
        return <Loader2 size={16} className="text-[#8B5CF6] animate-spin" />;
      case 'skipped':
        return <Circle size={16} className="text-[#64748B] line-through" />;
      default:
        return <Circle size={16} className="text-[#64748B]" />;
    }
  };

  return (
    <div className="p-4 space-y-3">
      {plan.map((step, idx) => (
        <div
          key={step.id}
          className={cn(
            "p-3 rounded-lg border transition-colors",
            step.status === 'in_progress'
              ? "bg-[#8B5CF6]/10 border-[#8B5CF6]/30"
              : step.status === 'complete'
              ? "bg-green-500/10 border-green-500/20"
              : "bg-[#12121A] border-[#1E1E2E]"
          )}
        >
          <div className="flex items-start gap-3">
            <div className="mt-0.5">{getStatusIcon(step.status)}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-xs text-[#64748B] font-mono">
                  {String(idx + 1).padStart(2, '0')}
                </span>
                <span className={cn(
                  "text-sm font-medium truncate",
                  step.status === 'complete' ? "text-green-400" : "text-[#F1F5F9]"
                )}>
                  {step.title}
                </span>
              </div>
              {step.description && (
                <p className="text-xs text-[#64748B] mt-1 line-clamp-2">
                  {step.description}
                </p>
              )}
              {step.files && step.files.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {step.files.slice(0, 3).map(file => (
                    <span
                      key={file}
                      className="text-[10px] px-1.5 py-0.5 bg-[#1E1E2E] rounded text-[#94A3B8] font-mono"
                    >
                      {file.split('/').pop()}
                    </span>
                  ))}
                  {step.files.length > 3 && (
                    <span className="text-[10px] px-1.5 py-0.5 text-[#64748B]">
                      +{step.files.length - 3} more
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

