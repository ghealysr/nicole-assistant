'use client';

/**
 * Enjineer Main Area Component
 * 
 * Center panel containing:
 * - File tabs at top
 * - Code editor (Monaco) / Preview / Terminal tabs
 * - Sandpack-powered preview for React projects
 * - Static HTML preview for simple sites
 */

import React, { useState, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { X, Code, Eye, Terminal, RefreshCw } from 'lucide-react';
import { useEnjineerStore } from '@/lib/enjineer/store';
import dynamic from 'next/dynamic';

// Dynamic import for Monaco to avoid SSR issues
const MonacoEditor = dynamic(
  () => import('@monaco-editor/react').then(mod => mod.default),
  { 
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full bg-[#0D0D12] text-[#64748B]">
        Loading editor...
      </div>
    )
  }
);

// Dynamic import for PreviewPane
const PreviewPane = dynamic(
  () => import('./PreviewPane').then(mod => mod.PreviewPane),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full bg-[#0D0D12] text-[#64748B]">
        Loading preview...
      </div>
    )
  }
);

export function MainArea() {
  const {
    mainTab,
    setMainTab,
    previewMode,
    setPreviewMode,
    openFiles,
    selectedFile,
    files,
    closeFile,
    selectFile,
    updateFile,
    terminalOutput,
    currentProject,
    previewRefreshTrigger,
    triggerPreviewRefresh,
  } = useEnjineerStore();

  const currentFile = selectedFile ? files.get(selectedFile) ?? null : null;
  
  // Local refresh key combined with store trigger for full control
  const [localRefreshKey, setLocalRefreshKey] = useState(0);
  const combinedRefreshKey = previewRefreshTrigger + localRefreshKey;
  
  // Refresh preview when switching to preview tab or when explicitly requested
  const refreshPreview = useCallback(() => {
    setLocalRefreshKey(k => k + 1);
    triggerPreviewRefresh();
  }, [triggerPreviewRefresh]);

  return (
    <div className="flex-1 bg-[#0A0A0F] flex flex-col min-w-0">
      {/* Toolbar */}
      <div className="h-10 bg-[#0D0D12] border-b border-[#1E1E2E] flex items-center justify-between px-2">
        {/* Left: View Tabs */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setMainTab('code')}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded transition-colors flex items-center gap-1.5",
              mainTab === 'code'
                ? "bg-[#8B5CF6] text-white"
                : "text-[#94A3B8] hover:text-white hover:bg-[#1E1E2E]"
            )}
          >
            <Code size={14} />
            Code
          </button>
          <button
            onClick={() => {
              setMainTab('preview');
              refreshPreview(); // Refresh when switching to preview
            }}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded transition-colors flex items-center gap-1.5",
              mainTab === 'preview'
                ? "bg-[#8B5CF6] text-white"
                : "text-[#94A3B8] hover:text-white hover:bg-[#1E1E2E]"
            )}
          >
            <Eye size={14} />
            Preview
          </button>
          <button
            onClick={() => setMainTab('terminal')}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded transition-colors flex items-center gap-1.5",
              mainTab === 'terminal'
                ? "bg-[#8B5CF6] text-white"
                : "text-[#94A3B8] hover:text-white hover:bg-[#1E1E2E]"
            )}
          >
            <Terminal size={14} />
            Terminal
          </button>
        </div>

        {/* Right: Preview refresh (only in preview mode - other controls are in PreviewPane) */}
        {mainTab === 'preview' && (
          <button 
            onClick={refreshPreview}
            className="p-1.5 text-[#64748B] hover:text-white transition-colors"
            title="Refresh Preview"
          >
            <RefreshCw size={14} />
          </button>
        )}
      </div>

      {/* File Tabs (only show in code mode) */}
      {mainTab === 'code' && openFiles.length > 0 && (
        <div className="h-9 bg-[#0D0D12] border-b border-[#1E1E2E] flex items-center overflow-x-auto custom-scrollbar">
          {openFiles.map(path => {
            const file = files.get(path);
            const isActive = selectedFile === path;
            const fileName = path.split('/').pop();
            
            return (
              <div
                key={path}
                className={cn(
                  "flex items-center gap-2 px-3 h-full border-r border-[#1E1E2E] cursor-pointer group",
                  isActive
                    ? "bg-[#0A0A0F] text-white border-t-2 border-t-[#8B5CF6]"
                    : "text-[#64748B] hover:text-[#94A3B8] hover:bg-[#12121A]"
                )}
                onClick={() => selectFile(path)}
              >
                <span className="text-xs font-mono truncate max-w-[120px]">
                  {fileName}
                  {file?.isModified && <span className="text-[#8B5CF6] ml-1">●</span>}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    closeFile(path);
                  }}
                  className="opacity-0 group-hover:opacity-100 hover:text-white transition-opacity"
                >
                  <X size={12} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {mainTab === 'code' && (
          <CodePanel 
            file={currentFile} 
            onContentChange={(content) => {
              if (selectedFile) updateFile(selectedFile, content);
            }}
          />
        )}
        {mainTab === 'preview' && (
          <PreviewPane 
            projectId={currentProject?.id ?? null} 
            previewMode={previewMode}
            onModeChange={setPreviewMode}
            refreshTrigger={combinedRefreshKey}
          />
        )}
        {mainTab === 'terminal' && (
          <TerminalPanel output={terminalOutput} />
        )}
      </div>
    </div>
  );
}

// Code Panel Component
interface CodePanelProps {
  file: { path: string; content: string; language: string } | null;
  onContentChange: (content: string) => void;
}

function CodePanel({ file, onContentChange }: CodePanelProps) {
  if (!file) {
    return (
      <div className="flex flex-col items-center justify-center h-full bg-[#0A0A0F] text-[#64748B]">
        <Code size={48} className="mb-4 opacity-30" />
        <p className="text-sm">Select a file to edit</p>
        <p className="text-xs mt-1">or ask Nicole to create files</p>
      </div>
    );
  }

  return (
    <MonacoEditor
      height="100%"
      language={file.language}
      value={file.content}
      onChange={(value) => onContentChange(value || '')}
      theme="vs-dark"
      options={{
        minimap: { enabled: false },
        fontSize: 13,
        fontFamily: 'JetBrains Mono, Fira Code, monospace',
        lineNumbers: 'on',
        padding: { top: 16 },
        scrollBeyondLastLine: false,
        automaticLayout: true,
        tabSize: 2,
        wordWrap: 'on',
        bracketPairColorization: { enabled: true },
        cursorBlinking: 'smooth',
        smoothScrolling: true,
      }}
    />
  );
}

// Terminal Panel Component
interface TerminalPanelProps {
  output: string[];
}

function TerminalPanel({ output }: TerminalPanelProps) {
  const terminalRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [output]);

  return (
    <div 
      ref={terminalRef}
      className="h-full bg-[#0A0A0F] p-4 overflow-y-auto font-mono text-sm custom-scrollbar"
    >
      {output.length === 0 ? (
        <div className="text-[#64748B]">
          <span className="text-[#8B5CF6]">$</span> Terminal ready. Nicole will show command output here.
        </div>
      ) : (
        output.map((line, i) => (
          <div key={i} className="text-[#94A3B8] leading-relaxed">
            {line}
          </div>
        ))
      )}
    </div>
  );
}

