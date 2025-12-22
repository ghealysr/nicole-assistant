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
  Layout, Layers, Terminal, X
} from 'lucide-react';
import { useEnjineerStore, PlanStep, EnjineerFile } from '@/lib/enjineer/store';

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
            files={files}
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
// Plan View Component
// ============================================================================

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
            "p-3 rounded-lg border transition-all duration-300",
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
