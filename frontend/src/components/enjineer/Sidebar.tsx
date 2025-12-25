'use client';

/**
 * Enjineer Sidebar Component
 * 
 * Left panel containing:
 * - Files tab: File tree browser with smooth animations
 * - Plan tab: Nicole's plan steps
 * 
 * Features:
 * - All folders expanded by default
 * - Smooth streaming animations when files appear
 * - Context menu for file operations
 * - Comprehensive file type icons
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { 
  FileCode, ListChecks, ChevronRight, ChevronDown,
  FolderOpen, Folder, File, FileJson, FileType, FileText,
  CheckCircle2, Circle, Loader2, Plus, Trash2, Edit3,
  Image as ImageIcon, Settings, Package, Globe, Database,
  Layout, Layers, Terminal, X, Clock, Code, Shield
} from 'lucide-react';
import { useEnjineerStore, PlanStep, EnjineerFile } from '@/lib/enjineer/store';
import { enjineerApi } from '@/lib/enjineer/api';
import { QAReportPanel } from './QAReportPanel';

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
            "flex-1 px-3 py-3 text-xs font-medium transition-colors flex items-center justify-center gap-1.5",
            sidebarTab === 'files'
              ? "text-[#F1F5F9] border-b-2 border-[#8B5CF6]"
              : "text-[#64748B] hover:text-[#94A3B8]"
          )}
        >
          <FileCode size={14} />
          Files
        </button>
        <button
          onClick={() => setSidebarTab('plan')}
          className={cn(
            "flex-1 px-3 py-3 text-xs font-medium transition-colors flex items-center justify-center gap-1.5",
            sidebarTab === 'plan'
              ? "text-[#F1F5F9] border-b-2 border-[#8B5CF6]"
              : "text-[#64748B] hover:text-[#94A3B8]"
          )}
        >
          <ListChecks size={14} />
          Plan
        </button>
        <button
          onClick={() => setSidebarTab('qa')}
          className={cn(
            "flex-1 px-3 py-3 text-xs font-medium transition-colors flex items-center justify-center gap-1.5",
            sidebarTab === 'qa'
              ? "text-[#F1F5F9] border-b-2 border-[#8B5CF6]"
              : "text-[#64748B] hover:text-[#94A3B8]"
          )}
        >
          <Shield size={14} />
          QA
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {sidebarTab === 'files' && (
          <FileTree 
            files={files}
            selectedFile={selectedFile}
            onSelectFile={(path) => {
              selectFile(path);
              openFile(path);
            }}
          />
        )}
        {sidebarTab === 'plan' && <PlanView plan={plan} />}
        {sidebarTab === 'qa' && <QATabContent selectFile={selectFile} openFile={openFile} />}
      </div>
      
      {/* Token Usage & Cost Footer - Only show in files tab */}
      {sidebarTab === 'files' && <TokenUsageFooter />}
    </div>
  );
}

// ============================================================================
// Token Usage Footer Component
// ============================================================================

function TokenUsageFooter() {
  const { currentProject, messages } = useEnjineerStore();
  const [usage, setUsage] = React.useState<{
    inputTokens: number;
    outputTokens: number;
    totalCost: number;
  }>({ inputTokens: 0, outputTokens: 0, totalCost: 0 });

  // Fetch real usage from backend API
  React.useEffect(() => {
    if (currentProject?.id) {
      enjineerApi.getUsage(currentProject.id)
        .then(data => {
          setUsage({
            inputTokens: data.inputTokens,
            outputTokens: data.outputTokens,
            totalCost: data.totalCost,
          });
        })
        .catch(console.error);
    }
  }, [currentProject?.id, messages.length]); // Refresh when messages change

  const formatNumber = (n: number) => {
    if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
    return n.toString();
  };

  return (
    <div className="border-t border-[#1E1E2E] px-3 py-2 bg-[#0A0A0F]">
      <div className="flex items-center justify-between text-[10px]">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 text-[#64748B]">
            <Terminal size={10} />
            <span>{formatNumber(usage.inputTokens)}</span>
          </div>
          <span className="text-[#3E3E4E]">/</span>
          <div className="flex items-center gap-1 text-[#8B5CF6]">
            <Code size={10} />
            <span>{formatNumber(usage.outputTokens)}</span>
          </div>
        </div>
        <div className="text-[#22C55E] font-medium">
          ${usage.totalCost.toFixed(4)}
        </div>
      </div>
      <div className="text-[9px] text-[#4A4A5A] mt-1 text-center">
        Token usage · Project cost
      </div>
    </div>
  );
}

// ============================================================================
// File Tree Component - Enhanced with animations and context menu
// ============================================================================

interface FileTreeProps {
  files: Map<string, EnjineerFile>;
  selectedFile: string | null;
  onSelectFile: (path: string) => void;
}

interface TreeNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  children?: Record<string, TreeNode>;
  isNew?: boolean;
}

interface ContextMenuState {
  x: number;
  y: number;
  path: string;
  type: 'file' | 'folder';
}

function FileTree({ files, selectedFile, onSelectFile }: FileTreeProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [newFiles, setNewFiles] = useState<Set<string>>(new Set());
  const prevFilesRef = useRef<Set<string>>(new Set());
  const contextMenuRef = useRef<HTMLDivElement>(null);
  
  const { deleteFile, renameFile, addFile } = useEnjineerStore();

  // Track new files for animation
  useEffect(() => {
    const currentPaths = new Set(files.keys());
    const previousPaths = prevFilesRef.current;
    
    // Find newly added files
    const added = new Set<string>();
    currentPaths.forEach(path => {
      if (!previousPaths.has(path)) {
        added.add(path);
      }
    });
    
    if (added.size > 0) {
      setNewFiles(prev => new Set([...Array.from(prev), ...Array.from(added)]));
      
      // Remove "new" status after animation
      setTimeout(() => {
        setNewFiles(prev => {
          const next = new Set(prev);
          added.forEach(p => next.delete(p));
          return next;
        });
      }, 600);
    }
    
    prevFilesRef.current = currentPaths;
  }, [files]);

  // Auto-expand all folders when files change
  useEffect(() => {
    const allFolders = new Set<string>();
    files.forEach((_, path) => {
      const parts = path.split('/');
      for (let i = 1; i < parts.length; i++) {
        allFolders.add(parts.slice(0, i).join('/'));
      }
    });
    setExpanded(allFolders);
  }, [files]);

  // Close context menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(e.target as Node)) {
        setContextMenu(null);
      }
    };
    
    if (contextMenu) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [contextMenu]);

  // Build tree structure
  const tree: Record<string, TreeNode> = {};
  
  files.forEach((file, path) => {
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
          children: isFile ? undefined : {},
          isNew: newFiles.has(fullPath)
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

  const handleContextMenu = useCallback((e: React.MouseEvent, path: string, type: 'file' | 'folder') => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      path,
      type
    });
  }, []);

  const handleDeleteFile = (path: string) => {
    if (deleteFile) {
      deleteFile(path);
    }
    setContextMenu(null);
  };

  const handleNewFile = (folderPath: string) => {
    const fileName = prompt('Enter file name:');
    if (fileName && addFile) {
      const newPath = folderPath ? `${folderPath}/${fileName}` : fileName;
      addFile({
        path: newPath,
        content: '',
        language: getLanguageFromPath(fileName),
        isModified: false
      });
    }
    setContextMenu(null);
  };

  const handleRenameFile = (oldPath: string) => {
    const parts = oldPath.split('/');
    const oldName = parts.pop() || '';
    const newName = prompt('Enter new name:', oldName);
    if (newName && newName !== oldName && renameFile) {
      const newPath = [...parts, newName].join('/');
      renameFile(oldPath, newPath);
    }
    setContextMenu(null);
  };

  const getLanguageFromPath = (path: string): string => {
    if (path.endsWith('.tsx') || path.endsWith('.ts')) return 'typescript';
    if (path.endsWith('.jsx') || path.endsWith('.js')) return 'javascript';
    if (path.endsWith('.css')) return 'css';
    if (path.endsWith('.json')) return 'json';
    if (path.endsWith('.html')) return 'html';
    if (path.endsWith('.md')) return 'markdown';
    return 'plaintext';
  };

  const getFileIcon = (name: string) => {
    const lower = name.toLowerCase();
    
    // TypeScript/JavaScript
    if (lower.endsWith('.tsx')) return <FileCode size={14} className="text-blue-400" />;
    if (lower.endsWith('.ts')) return <FileCode size={14} className="text-blue-500" />;
    if (lower.endsWith('.jsx')) return <FileCode size={14} className="text-yellow-400" />;
    if (lower.endsWith('.js')) return <FileCode size={14} className="text-yellow-500" />;
    
    // Styles
    if (lower.endsWith('.css')) return <FileType size={14} className="text-pink-400" />;
    if (lower.endsWith('.scss') || lower.endsWith('.sass')) return <FileType size={14} className="text-pink-500" />;
    if (lower.endsWith('.less')) return <FileType size={14} className="text-purple-400" />;
    
    // Data/Config
    if (lower.endsWith('.json')) return <FileJson size={14} className="text-yellow-400" />;
    if (lower.endsWith('.yaml') || lower.endsWith('.yml')) return <Settings size={14} className="text-red-400" />;
    if (lower.endsWith('.toml')) return <Settings size={14} className="text-orange-400" />;
    if (lower.endsWith('.env') || lower.includes('.env.')) return <Settings size={14} className="text-green-400" />;
    
    // Markup
    if (lower.endsWith('.html')) return <Globe size={14} className="text-orange-500" />;
    if (lower.endsWith('.md') || lower.endsWith('.mdx')) return <FileText size={14} className="text-[#64748B]" />;
    if (lower.endsWith('.xml')) return <FileText size={14} className="text-orange-400" />;
    
    // Images
    if (lower.endsWith('.png') || lower.endsWith('.jpg') || lower.endsWith('.jpeg') || 
        lower.endsWith('.gif') || lower.endsWith('.svg') || lower.endsWith('.webp') ||
        lower.endsWith('.ico')) {
      return <ImageIcon size={14} className="text-emerald-400" />;
    }
    
    // Package files
    if (lower === 'package.json') return <Package size={14} className="text-red-400" />;
    if (lower === 'package-lock.json' || lower === 'yarn.lock' || lower === 'pnpm-lock.yaml') {
      return <Package size={14} className="text-[#64748B]" />;
    }
    
    // Config files
    if (lower.includes('config') || lower.startsWith('.')) {
      return <Settings size={14} className="text-[#64748B]" />;
    }
    if (lower === 'dockerfile' || lower.endsWith('.dockerfile')) {
      return <Layers size={14} className="text-blue-400" />;
    }
    
    // Next.js specific
    if (lower === 'next.config.js' || lower === 'next.config.mjs') {
      return <Layout size={14} className="text-white" />;
    }
    if (lower === 'tailwind.config.js' || lower === 'tailwind.config.ts') {
      return <FileCode size={14} className="text-cyan-400" />;
    }
    
    // Database
    if (lower.endsWith('.sql') || lower.endsWith('.prisma')) {
      return <Database size={14} className="text-blue-300" />;
    }
    
    // Shell
    if (lower.endsWith('.sh') || lower.endsWith('.bash') || lower.endsWith('.zsh')) {
      return <Terminal size={14} className="text-green-400" />;
    }
    
    // Default
    return <File size={14} className="text-[#64748B]" />;
  };

  const renderNode = (node: TreeNode, level: number = 0) => {
    const isExpanded = expanded.has(node.path);
    const isSelected = selectedFile === node.path;
    const isNew = newFiles.has(node.path);
    const paddingLeft = level * 12 + 12;

    if (node.type === 'folder') {
      return (
        <div key={node.path} className={cn(
          "transition-all duration-300 ease-out",
          isNew && "animate-fadeSlideIn"
        )}>
          <div
            className="flex items-center py-1.5 px-2 hover:bg-[#1E1E2E] cursor-pointer text-sm text-[#94A3B8] select-none group"
            style={{ paddingLeft }}
            onClick={() => toggleFolder(node.path)}
            onContextMenu={(e) => handleContextMenu(e, node.path, 'folder')}
          >
            <span className="transition-transform duration-150">
              {isExpanded ? (
                <ChevronDown size={14} className="mr-1 text-[#64748B]" />
              ) : (
                <ChevronRight size={14} className="mr-1 text-[#64748B]" />
              )}
            </span>
            {isExpanded ? (
              <FolderOpen size={14} className="mr-2 text-[#8B5CF6]" />
            ) : (
              <Folder size={14} className="mr-2 text-[#8B5CF6]" />
            )}
            <span className="truncate flex-1">{node.name}</span>
            <button
              onClick={(e) => { e.stopPropagation(); handleNewFile(node.path); }}
              className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-[#2E2E3E] rounded transition-opacity"
              title="New file"
            >
              <Plus size={12} className="text-[#64748B]" />
            </button>
          </div>
          <div className={cn(
            "overflow-hidden transition-all duration-200 ease-out",
            isExpanded ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0"
          )}>
            {node.children && Object.values(node.children)
              .sort((a, b) => {
                if (a.type === b.type) return a.name.localeCompare(b.name);
                return a.type === 'folder' ? -1 : 1;
              })
              .map(child => renderNode(child, level + 1))}
          </div>
        </div>
      );
    }

    return (
      <div
        key={node.path}
        className={cn(
          "flex items-center py-1.5 px-2 cursor-pointer text-sm select-none group",
          "transition-all duration-300 ease-out",
          isNew && "animate-fadeSlideIn bg-[#8B5CF6]/10",
          isSelected
            ? "bg-[#1E1E2E] text-white border-l-2 border-[#8B5CF6]"
            : "text-[#94A3B8] hover:bg-[#12121A] hover:text-[#F1F5F9] border-l-2 border-transparent"
        )}
        style={{ paddingLeft: paddingLeft + 14 }}
        onClick={() => onSelectFile(node.path)}
        onContextMenu={(e) => handleContextMenu(e, node.path, 'file')}
      >
        <span className="mr-2 transition-transform duration-150">{getFileIcon(node.name)}</span>
        <span className="truncate flex-1">{node.name}</span>
        <button
          onClick={(e) => { e.stopPropagation(); handleDeleteFile(node.path); }}
          className="opacity-0 group-hover:opacity-100 p-0.5 hover:bg-[#2E2E3E] rounded transition-opacity"
          title="Delete file"
        >
          <Trash2 size={12} className="text-[#64748B] hover:text-red-400" />
        </button>
      </div>
    );
  };

  if (files.size === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-[#64748B] p-6 text-center">
        <FileCode size={32} className="mb-3 opacity-50" />
        <p className="text-sm">No files yet</p>
        <p className="text-xs mt-1">Ask Nicole to create a project</p>
      </div>
    );
  }

  return (
    <>
      <div className="py-2">
        {Object.values(tree)
          .sort((a, b) => {
            if (a.type === b.type) return a.name.localeCompare(b.name);
            return a.type === 'folder' ? -1 : 1;
          })
          .map(node => renderNode(node))}
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <div
          ref={contextMenuRef}
          className="fixed bg-[#1E1E2E] border border-[#2E2E3E] rounded-lg shadow-xl py-1 z-50 min-w-[160px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          {contextMenu.type === 'folder' && (
            <button
              onClick={() => handleNewFile(contextMenu.path)}
              className="w-full px-3 py-2 text-left text-sm text-[#F1F5F9] hover:bg-[#2E2E3E] flex items-center gap-2"
            >
              <Plus size={14} />
              New File
            </button>
          )}
          <button
            onClick={() => handleRenameFile(contextMenu.path)}
            className="w-full px-3 py-2 text-left text-sm text-[#F1F5F9] hover:bg-[#2E2E3E] flex items-center gap-2"
          >
            <Edit3 size={14} />
            Rename
          </button>
          <button
            onClick={() => handleDeleteFile(contextMenu.path)}
            className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-[#2E2E3E] flex items-center gap-2"
          >
            <Trash2 size={14} />
            Delete
          </button>
          <div className="border-t border-[#2E2E3E] my-1" />
          <button
            onClick={() => setContextMenu(null)}
            className="w-full px-3 py-2 text-left text-sm text-[#64748B] hover:bg-[#2E2E3E] flex items-center gap-2"
          >
            <X size={14} />
            Cancel
          </button>
        </div>
      )}

      {/* Animation styles */}
      <style jsx global>{`
        @keyframes fadeSlideIn {
          from {
            opacity: 0;
            transform: translateX(-8px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        .animate-fadeSlideIn {
          animation: fadeSlideIn 0.3s ease-out forwards;
        }
      `}</style>
    </>
  );
}

// ============================================================================
// Plan View Component - Rich progress tracking with approvals
// ============================================================================

interface PlanViewProps {
  plan: PlanStep[];
}

function PlanView({ plan }: PlanViewProps) {
  // All hooks must be at the top, before any conditional returns
  const { planOverview, currentProject, openFile, files, setPlanOverview, updatePlanStep: updateStep } = useEnjineerStore();
  const [expandedPhases, setExpandedPhases] = useState<Set<string>>(new Set());
  const [approvingPhase, setApprovingPhase] = useState<string | null>(null);
  const [approvingPlan, setApprovingPlan] = useState(false);

  // Toggle phase expansion
  const togglePhase = (phaseId: string) => {
    setExpandedPhases(prev => {
      const next = new Set(prev);
      if (next.has(phaseId)) {
        next.delete(phaseId);
      } else {
        next.add(phaseId);
      }
      return next;
    });
  };

  // Handle phase approval
  const handleApprove = async (phaseId: string) => {
    if (!currentProject) return;
    setApprovingPhase(phaseId);
    try {
      const { enjineerApi } = await import('@/lib/enjineer/api');
      await enjineerApi.approvePhase(currentProject.id, phaseId);
      // Update local state
      useEnjineerStore.getState().updatePlanStep(phaseId, { 
        status: 'in_progress', 
        approvalStatus: 'approved' 
      });
    } catch (err) {
      console.error('Failed to approve phase:', err);
    } finally {
      setApprovingPhase(null);
    }
  };

  // Handle phase rejection
  const handleReject = async (phaseId: string) => {
    if (!currentProject) return;
    const reason = window.prompt('Reason for rejection (optional):');
    setApprovingPhase(phaseId);
    try {
      const { enjineerApi } = await import('@/lib/enjineer/api');
      await enjineerApi.rejectPhase(currentProject.id, phaseId, reason || undefined);
      useEnjineerStore.getState().updatePlanStep(phaseId, { 
        status: 'pending', 
        approvalStatus: 'rejected' 
      });
    } catch (err) {
      console.error('Failed to reject phase:', err);
    } finally {
      setApprovingPhase(null);
    }
  };

  // Empty state
  if (plan.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-[#64748B] p-6 text-center">
        <div className="relative mb-4">
          <ListChecks size={40} className="opacity-30" />
          <div className="absolute inset-0 bg-gradient-to-t from-[#0A0A0F] to-transparent" />
        </div>
        <p className="text-sm font-medium text-[#94A3B8]">No plan yet</p>
        <p className="text-xs mt-1 max-w-[200px]">
          Nicole will create a detailed plan when you describe your project
        </p>
      </div>
    );
  }

  // Calculate progress
  const completedCount = plan.filter(s => s.status === 'complete').length;
  const progressPercent = Math.round((completedCount / plan.length) * 100);
  const totalEstimatedMinutes = plan.reduce((sum, s) => sum + (s.estimatedMinutes || 0), 0);
  const totalActualMinutes = plan.reduce((sum, s) => sum + (s.actualMinutes || 0), 0);

  // Get status icon with enhanced visuals
  const getStatusIcon = (status: PlanStep['status']) => {
    switch (status) {
      case 'complete':
        return (
          <div className="relative">
            <CheckCircle2 size={18} className="text-emerald-400" />
            <div className="absolute inset-0 animate-ping opacity-30">
              <CheckCircle2 size={18} className="text-emerald-400" />
            </div>
          </div>
        );
      case 'in_progress':
        return (
          <div className="relative">
            <div className="absolute inset-0 bg-violet-500/20 rounded-full animate-pulse" />
            <Loader2 size={18} className="text-violet-400 animate-spin" />
          </div>
        );
      case 'awaiting_approval':
        return (
          <div className="relative">
            <div className="absolute inset-0 bg-amber-500/20 rounded-full animate-pulse" />
            <Clock size={18} className="text-amber-400" />
          </div>
        );
      case 'skipped':
        return <Circle size={18} className="text-[#475569] opacity-50" />;
      default:
        return <Circle size={18} className="text-[#475569]" />;
    }
  };

  // Agent badge component
  const AgentBadge = ({ agent }: { agent: string }) => {
    const colors: Record<string, string> = {
      engineer: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      qa: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      sr_qa: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    };
    const icons: Record<string, typeof Code> = {
      engineer: Code,
      qa: Terminal,
      sr_qa: Layers,
    };
    const Icon = icons[agent] || Code;
    return (
      <span className={cn(
        "inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border font-medium",
        colors[agent] || 'bg-[#1E1E2E] text-[#94A3B8] border-[#2D2D3D]'
      )}>
        <Icon size={10} />
        {agent.replace('_', ' ').toUpperCase()}
      </span>
    );
  };

  // Format time display
  const formatTime = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

  // Handle approving the entire plan
  const handleApprovePlan = async () => {
    if (!currentProject || !planOverview) return;
    setApprovingPlan(true);
    try {
      const { enjineerApi } = await import('@/lib/enjineer/api');
      await enjineerApi.approvePlan(currentProject.id, planOverview.id);
      setPlanOverview({ ...planOverview, status: 'approved' });
      // Also set first phase to in_progress
      if (plan.length > 0) {
        updateStep(plan[0].id, { status: 'in_progress' });
      }
    } catch (err) {
      console.error('Failed to approve plan:', err);
    } finally {
      setApprovingPlan(false);
    }
  };
  
  // Check if plan.md exists (files is a Map)
  const planMdFile = files.get('/plan.md') || files.get('plan.md');
  const needsPlanApproval = planOverview?.status === 'awaiting_approval';

  return (
    <div className="flex flex-col h-full">
      {/* Plan Documents Section */}
      {planMdFile && (
        <div className="p-3 border-b border-[#1E1E2E] bg-[#0A0A0F]">
          <div className="text-[10px] uppercase tracking-wider text-[#475569] mb-2">Plan Documents</div>
          <button
            onClick={() => openFile('/plan.md')}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-[#12121A] hover:bg-[#1E1E2E] border border-[#1E1E2E] transition-colors text-left group"
          >
            <FileText size={16} className="text-[#8B5CF6]" />
            <span className="text-sm text-[#E2E8F0] group-hover:text-white">plan.md</span>
          </button>
        </div>
      )}
      
      {/* Approval Banner */}
      {needsPlanApproval && (
        <div className="p-4 bg-gradient-to-r from-amber-500/10 to-orange-500/10 border-b border-amber-500/20">
          <div className="flex items-center gap-2 mb-2">
            <Clock size={16} className="text-amber-400" />
            <span className="text-sm font-medium text-amber-300">Awaiting Approval</span>
          </div>
          <p className="text-xs text-[#94A3B8] mb-3">
            Review the plan above, then approve to begin implementation.
          </p>
          <button
            onClick={handleApprovePlan}
            disabled={approvingPlan}
            className="w-full py-2 px-4 rounded-lg bg-gradient-to-r from-emerald-500 to-green-500 text-white text-sm font-medium hover:from-emerald-600 hover:to-green-600 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {approvingPlan ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <CheckCircle2 size={14} />
            )}
            Approve Plan
          </button>
        </div>
      )}

      {/* Progress Header */}
      <div className="p-4 border-b border-[#1E1E2E] bg-gradient-to-b from-[#12121A] to-transparent">
        {/* Overall progress bar */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-[#94A3B8]">Progress</span>
          <span className="text-xs font-mono text-[#8B5CF6]">
            {completedCount}/{plan.length} phases
          </span>
        </div>
        <div className="h-2 bg-[#1E1E2E] rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-all duration-500 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex items-center justify-between mt-2">
          <span className="text-[10px] text-[#64748B]">
            {progressPercent}% complete
          </span>
          {totalEstimatedMinutes > 0 && (
            <span className="text-[10px] text-[#64748B] flex items-center gap-1">
              <Clock size={10} />
              {totalActualMinutes > 0 
                ? `${formatTime(totalActualMinutes)} / ${formatTime(totalEstimatedMinutes)}`
                : `Est. ${formatTime(totalEstimatedMinutes)}`
              }
            </span>
          )}
        </div>
        
        {/* Plan version & status */}
        {planOverview && !needsPlanApproval && (
          <div className="flex items-center gap-2 mt-3 pt-3 border-t border-[#1E1E2E]/50">
            <span className={cn(
              "text-[10px] px-2 py-0.5 rounded-full font-medium",
              planOverview.status === 'approved' || planOverview.status === 'in_progress'
                ? "bg-emerald-500/20 text-emerald-400"
                : planOverview.status === 'completed'
                ? "bg-blue-500/20 text-blue-400"
                : "bg-[#1E1E2E] text-[#64748B]"
            )}>
              {planOverview.status.toUpperCase()}
            </span>
            <span className="text-[10px] text-[#475569]">
              v{planOverview.version}
            </span>
          </div>
        )}
      </div>

      {/* Phase List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2">
        {plan.map((step, idx) => {
          const isExpanded = expandedPhases.has(step.id);
          const isCurrent = step.status === 'in_progress' || step.status === 'awaiting_approval';
          const needsApproval = step.status === 'awaiting_approval';
          
          return (
            <div
              key={step.id}
              className={cn(
                "rounded-lg border transition-all duration-300 overflow-hidden",
                isCurrent
                  ? "bg-gradient-to-r from-violet-500/10 to-fuchsia-500/10 border-violet-500/30 shadow-lg shadow-violet-500/5"
                  : step.status === 'complete'
                  ? "bg-emerald-500/5 border-emerald-500/20"
                  : needsApproval
                  ? "bg-amber-500/5 border-amber-500/20"
                  : "bg-[#0F0F15] border-[#1E1E2E] hover:border-[#2D2D3D]"
              )}
            >
              {/* Phase Header - Clickable */}
              <button
                onClick={() => togglePhase(step.id)}
                className="w-full p-3 flex items-start gap-3 text-left"
              >
                <div className="mt-0.5 flex-shrink-0">{getStatusIcon(step.status)}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-[#475569] font-mono bg-[#1E1E2E] px-1.5 py-0.5 rounded">
                      {String(step.phaseNumber || idx + 1).padStart(2, '0')}
                    </span>
                    <span className={cn(
                      "text-sm font-medium truncate",
                      step.status === 'complete' 
                        ? "text-emerald-400" 
                        : isCurrent 
                        ? "text-violet-300"
                        : "text-[#E2E8F0]"
                    )}>
                      {step.title}
                    </span>
                    <ChevronDown 
                      size={14} 
                      className={cn(
                        "text-[#475569] transition-transform duration-200 ml-auto flex-shrink-0",
                        isExpanded && "rotate-180"
                      )}
                    />
                  </div>
                  
                  {/* Time & agents row */}
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    {step.estimatedMinutes && (
                      <span className="text-[10px] text-[#475569] flex items-center gap-1">
                        <Clock size={10} />
                        {step.actualMinutes 
                          ? `${formatTime(step.actualMinutes)} / ${formatTime(step.estimatedMinutes)}`
                          : formatTime(step.estimatedMinutes)
                        }
                      </span>
                    )}
                    {step.agentsRequired?.map(agent => (
                      <AgentBadge key={agent} agent={agent} />
                    ))}
                    {step.requiresApproval && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                        Approval Required
                      </span>
                    )}
                  </div>
                </div>
              </button>

              {/* Expanded Content */}
              {isExpanded && (
                <div className="px-3 pb-3 pt-0 border-t border-[#1E1E2E]/50 mt-0">
                  {/* Description */}
                  {step.description && (
                    <p className="text-xs text-[#94A3B8] mt-3 leading-relaxed">
                      {step.description}
                    </p>
                  )}
                  
                  {/* QA Info */}
                  {step.qaDepth && (
                    <div className="mt-3 flex items-center gap-2">
                      <span className="text-[10px] text-[#475569]">QA Depth:</span>
                      <span className={cn(
                        "text-[10px] px-1.5 py-0.5 rounded font-medium",
                        step.qaDepth === 'thorough' 
                          ? "bg-red-500/20 text-red-400"
                          : step.qaDepth === 'standard'
                          ? "bg-amber-500/20 text-amber-400"
                          : "bg-green-500/20 text-green-400"
                      )}>
                        {step.qaDepth.toUpperCase()}
                      </span>
                    </div>
                  )}
                  
                  {/* QA Focus areas */}
                  {step.qaFocus && step.qaFocus.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {step.qaFocus.map(focus => (
                        <span 
                          key={focus}
                          className="text-[10px] px-1.5 py-0.5 bg-[#1E1E2E] rounded text-[#94A3B8]"
                        >
                          {focus}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Files */}
                  {step.files && step.files.length > 0 && (
                    <div className="mt-3">
                      <span className="text-[10px] text-[#475569] block mb-1.5">Files:</span>
                      <div className="flex flex-wrap gap-1">
                        {step.files.map(file => (
                          <span
                            key={file}
                            className="text-[10px] px-1.5 py-0.5 bg-[#1E1E2E] rounded text-[#94A3B8] font-mono"
                          >
                            {file.split('/').pop()}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Timestamps */}
                  {(step.startedAt || step.completedAt) && (
                    <div className="mt-3 text-[10px] text-[#475569] space-y-0.5">
                      {step.startedAt && (
                        <div>Started: {new Date(step.startedAt).toLocaleString()}</div>
                      )}
                      {step.completedAt && (
                        <div>Completed: {new Date(step.completedAt).toLocaleString()}</div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Approval Actions */}
              {needsApproval && (
                <div className="px-3 pb-3 pt-2 border-t border-amber-500/20 bg-amber-500/5">
                  <p className="text-xs text-amber-400 mb-2 flex items-center gap-1.5">
                    <Clock size={12} />
                    Awaiting your approval to proceed
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleApprove(step.id)}
                      disabled={approvingPhase === step.id}
                      className={cn(
                        "flex-1 px-3 py-1.5 text-xs font-medium rounded transition-colors",
                        "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30",
                        "disabled:opacity-50 disabled:cursor-not-allowed"
                      )}
                    >
                      {approvingPhase === step.id ? (
                        <Loader2 size={12} className="animate-spin mx-auto" />
                      ) : (
                        "Approve"
                      )}
                    </button>
                    <button
                      onClick={() => handleReject(step.id)}
                      disabled={approvingPhase === step.id}
                      className={cn(
                        "flex-1 px-3 py-1.5 text-xs font-medium rounded transition-colors",
                        "bg-red-500/20 text-red-400 hover:bg-red-500/30",
                        "disabled:opacity-50 disabled:cursor-not-allowed"
                      )}
                    >
                      Reject
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// QA Tab Content Component
// ============================================================================

function QATabContent({ 
  selectFile, 
  openFile 
}: { 
  selectFile: (path: string) => void;
  openFile: (path: string) => void;
}) {
  const { selectedProject } = useEnjineerStore();
  
  const handleFileClick = useCallback((path: string, line?: number) => {
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    selectFile(normalizedPath);
    openFile(normalizedPath);
    // Note: Line number navigation could be enhanced with Monaco editor integration
    if (line) {
      console.log(`[QA] Navigate to ${normalizedPath}:${line}`);
    }
  }, [selectFile, openFile]);
  
  return (
    <QAReportPanel 
      projectId={selectedProject?.id ?? null}
      onFileClick={handleFileClick}
    />
  );
}
