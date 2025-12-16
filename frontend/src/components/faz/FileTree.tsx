import React from 'react';
import { cn } from '@/lib/utils';
import { 
  File, FileJson, FileType, FileCode, Folder, FolderOpen, ChevronRight, ChevronDown 
} from 'lucide-react';
import { useFazStore } from '@/lib/faz/store';

interface FileTreeProps {
  files: string[];
}

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  children?: Record<string, FileNode>;
}

export function FileTree({ files }: FileTreeProps) {
  const { selectedFile, selectFile } = useFazStore();
  const [expandedFolders, setExpandedFolders] = React.useState<Set<string>>(new Set(['app', 'components', 'lib']));

  // Build tree structure
  const tree: Record<string, FileNode> = {};
  
  files.forEach(path => {
    const parts = path.split('/');
    let currentLevel = tree;
    
    parts.forEach((part, index) => {
      const isFile = index === parts.length - 1;
      const fullPath = parts.slice(0, index + 1).join('/');
      
      if (!currentLevel[part]) {
        currentLevel[part] = {
          name: part,
          path: fullPath,
          type: isFile ? 'file' : 'folder',
          children: isFile ? undefined : {}
        };
      }
      
      if (!isFile) {
        currentLevel = currentLevel[part].children!;
      }
    });
  });

  const toggleFolder = (path: string) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedFolders(newExpanded);
  };

  const getFileIcon = (filename: string) => {
    if (filename.endsWith('.tsx') || filename.endsWith('.ts')) return <FileCode size={14} className="text-blue-400" />;
    if (filename.endsWith('.css')) return <FileType size={14} className="text-pink-400" />;
    if (filename.endsWith('.json')) return <FileJson size={14} className="text-yellow-400" />;
    return <File size={14} className="text-gray-400" />;
  };

  const renderNode = (node: FileNode, level: number = 0) => {
    const isExpanded = expandedFolders.has(node.path);
    const isSelected = selectedFile === node.path;
    
    if (node.type === 'folder') {
      return (
        <div key={node.path}>
          <div 
            className="flex items-center py-1 px-2 hover:bg-[#1E1E2E] cursor-pointer text-sm text-[#94A3B8] select-none"
            style={{ paddingLeft: `${level * 12 + 8}px` }}
            onClick={() => toggleFolder(node.path)}
          >
            {isExpanded ? (
              <ChevronDown size={14} className="mr-1 text-[#64748B]" />
            ) : (
              <ChevronRight size={14} className="mr-1 text-[#64748B]" />
            )}
            {isExpanded ? (
              <FolderOpen size={14} className="mr-2 text-[#6366F1]" />
            ) : (
              <Folder size={14} className="mr-2 text-[#6366F1]" />
            )}
            <span>{node.name}</span>
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
          "flex items-center py-1 px-2 cursor-pointer text-sm select-none border-l-2 border-transparent transition-colors",
          isSelected 
            ? "bg-[#1E1E2E] text-white border-[#6366F1]" 
            : "text-[#94A3B8] hover:bg-[#12121A] hover:text-[#F1F5F9]"
        )}
        style={{ paddingLeft: `${level * 12 + 20}px` }}
        onClick={() => selectFile(node.path)}
      >
        <span className="mr-2 opacity-80">{getFileIcon(node.name)}</span>
        <span>{node.name}</span>
      </div>
    );
  };

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

