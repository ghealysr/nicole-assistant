'use client';

/**
 * Enjineer Preview Pane
 * 
 * Versatile preview system that supports:
 * - Static HTML/CSS/JS sites (iframe with srcdoc)
 * - React projects (Sandpack in-browser bundling - lightweight only)
 * - Next.js projects (static preview - too heavy for in-browser bundling)
 * - Responsive preview modes (mobile, tablet, desktop)
 * - File explorer view for complex projects
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { cn } from '@/lib/utils';
import { 
  Smartphone, Tablet, Monitor, RefreshCw, AlertCircle, 
  Loader2, Terminal, Maximize2, Minimize2, FileCode, Eye,
  Play, Pause, FolderTree
} from 'lucide-react';
import { enjineerApi, PreviewBundle } from '@/lib/enjineer/api';
import dynamic from 'next/dynamic';

// Dynamically import Sandpack to avoid SSR issues
const SandpackProvider = dynamic(
  () => import('@codesandbox/sandpack-react').then(mod => mod.SandpackProvider),
  { ssr: false }
);

const SandpackPreview = dynamic(
  () => import('@codesandbox/sandpack-react').then(mod => mod.SandpackPreview),
  { ssr: false }
);

// Types
interface PreviewPaneProps {
  projectId: number | null;
  previewMode: 'mobile' | 'tablet' | 'desktop';
  onModeChange?: (mode: 'mobile' | 'tablet' | 'desktop') => void;
  className?: string;
  refreshTrigger?: number;
}

type PreviewState = 
  | { type: 'loading' }
  | { type: 'empty' }
  | { type: 'error'; message: string }
  | { type: 'static'; html: string }
  | { type: 'sandpack'; bundle: PreviewBundle }
  | { type: 'files'; bundle: PreviewBundle; message: string };

// Responsive widths
const PREVIEW_WIDTHS = {
  mobile: 375,
  tablet: 768,
  desktop: '100%',
};

export function PreviewPane({ 
  projectId, 
  previewMode,
  onModeChange,
  className,
  refreshTrigger = 0
}: PreviewPaneProps) {
  const [state, setState] = useState<PreviewState>({ type: 'loading' });
  const [viewMode, setViewMode] = useState<'preview' | 'files'>('preview');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Load preview bundle
  const loadPreview = useCallback(async () => {
    if (!projectId) {
      setState({ type: 'empty' });
      return;
    }

    setState({ type: 'loading' });

    try {
      const bundle = await enjineerApi.getPreviewBundle(projectId);
      
      if (Object.keys(bundle.files).length === 0) {
        setState({ type: 'empty' });
        return;
      }

      // Decide rendering strategy based on project type
      if (bundle.project_type === 'static' || bundle.project_type === 'html') {
        // Static sites - use iframe with HTML
        const html = await enjineerApi.getPreviewHtml(projectId);
        setState({ type: 'static', html });
      } else if (bundle.project_type === 'nextjs') {
        // Next.js is too heavy for in-browser bundling
        // Show file explorer with message
        setState({ 
          type: 'files', 
          bundle,
          message: 'Next.js projects require deployment for live preview. View your files below or deploy to Vercel.'
        });
      } else if (bundle.project_type === 'react') {
        // Check if it's a simple React project (few dependencies)
        const depCount = Object.keys(bundle.dependencies || {}).length;
        if (depCount <= 5) {
          // Try Sandpack for simple React projects
          setState({ type: 'sandpack', bundle });
        } else {
          // Too many dependencies - show file explorer
          setState({ 
            type: 'files', 
            bundle,
            message: 'This React project has many dependencies. View files below or deploy for live preview.'
          });
        }
      } else {
        // Unknown - try static preview
        const html = await enjineerApi.getPreviewHtml(projectId);
        setState({ type: 'static', html });
      }
    } catch (error) {
      console.error('Preview load error:', error);
      setState({ 
        type: 'error', 
        message: error instanceof Error ? error.message : 'Failed to load preview' 
      });
    }
  }, [projectId]);

  // Initial load and refresh on trigger change
  useEffect(() => {
    loadPreview();
  }, [loadPreview, refreshTrigger]);

  // Get container width based on preview mode
  const containerStyle = previewMode === 'desktop' 
    ? { width: '100%' }
    : { width: PREVIEW_WIDTHS[previewMode], maxWidth: '100%' };

  return (
    <div className={cn('flex flex-col h-full bg-[#0A0A0F]', isFullscreen && 'fixed inset-0 z-50', className)}>
      {/* Toolbar */}
      <div className="h-10 bg-[#0D0D12] border-b border-[#1E1E2E] flex items-center justify-between px-3 shrink-0">
        {/* Left: View toggles */}
        <div className="flex items-center gap-2">
          {/* Preview/Files toggle */}
          <div className="flex items-center bg-[#12121A] rounded p-0.5">
            <button
              onClick={() => setViewMode('preview')}
              className={cn(
                "p-1.5 rounded transition-colors flex items-center gap-1",
                viewMode === 'preview' 
                  ? "bg-[#1E1E2E] text-white" 
                  : "text-[#64748B] hover:text-white"
              )}
              title="Preview"
            >
              <Eye size={14} />
              <span className="text-xs">Preview</span>
            </button>
            <button
              onClick={() => setViewMode('files')}
              className={cn(
                "p-1.5 rounded transition-colors flex items-center gap-1",
                viewMode === 'files' 
                  ? "bg-[#1E1E2E] text-white" 
                  : "text-[#64748B] hover:text-white"
              )}
              title="Files"
            >
              <FolderTree size={14} />
              <span className="text-xs">Files</span>
            </button>
          </div>

          {/* Device toggles (only in preview mode) */}
          {viewMode === 'preview' && (
            <div className="flex items-center bg-[#12121A] rounded p-0.5">
              {(['mobile', 'tablet', 'desktop'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => onModeChange?.(mode)}
                  className={cn(
                    "p-1.5 rounded transition-colors",
                    previewMode === mode 
                      ? "bg-[#1E1E2E] text-white" 
                      : "text-[#64748B] hover:text-white"
                  )}
                  title={mode.charAt(0).toUpperCase() + mode.slice(1)}
                >
                  {mode === 'mobile' && <Smartphone size={14} />}
                  {mode === 'tablet' && <Tablet size={14} />}
                  {mode === 'desktop' && <Monitor size={14} />}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={cn(
              "p-1.5 rounded transition-colors",
              autoRefresh ? "text-[#10B981]" : "text-[#64748B] hover:text-white"
            )}
            title={autoRefresh ? "Auto-refresh on" : "Auto-refresh off"}
          >
            {autoRefresh ? <Play size={14} /> : <Pause size={14} />}
          </button>
          
          <button
            onClick={loadPreview}
            className="p-1.5 text-[#64748B] hover:text-white transition-colors"
            title="Refresh preview"
            disabled={state.type === 'loading'}
          >
            <RefreshCw size={14} className={state.type === 'loading' ? 'animate-spin' : ''} />
          </button>
          
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 text-[#64748B] hover:text-white transition-colors"
            title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
          >
            {isFullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
        </div>
      </div>

      {/* Preview Area */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full flex items-center justify-center p-4 overflow-auto">
          {state.type === 'loading' && (
            <div className="flex flex-col items-center gap-3 text-[#64748B]">
              <Loader2 size={32} className="animate-spin text-[#8B5CF6]" />
              <span className="text-sm">Loading preview...</span>
            </div>
          )}

          {state.type === 'empty' && (
            <div className="flex flex-col items-center gap-3 text-[#64748B]">
              <div className="w-16 h-16 rounded-xl bg-[#12121A] flex items-center justify-center">
                <Monitor size={32} className="opacity-30" />
              </div>
              <p className="text-sm">No files to preview</p>
              <p className="text-xs">Ask Nicole to create your project files</p>
            </div>
          )}

          {state.type === 'error' && (
            <div className="flex flex-col items-center gap-3 text-[#EF4444]">
              <AlertCircle size={32} />
              <p className="text-sm">{state.message}</p>
              <button
                onClick={loadPreview}
                className="mt-2 px-4 py-2 bg-[#1E1E2E] text-white rounded-lg text-sm hover:bg-[#2E2E3E] transition-colors"
              >
                Retry
              </button>
            </div>
          )}

          {state.type === 'static' && viewMode === 'preview' && (
            <div 
              className="h-full transition-all duration-300 bg-white rounded-lg shadow-2xl overflow-hidden border border-[#1E1E2E]"
              style={containerStyle}
            >
              <iframe
                ref={iframeRef}
                srcDoc={state.html}
                className="w-full h-full border-0"
                title="Preview"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
              />
            </div>
          )}

          {state.type === 'sandpack' && viewMode === 'preview' && (
            <SandpackPreviewWrapper 
              bundle={state.bundle}
              previewMode={previewMode}
              onError={() => {
                // Fallback to files view on error
                setState({ 
                  type: 'files', 
                  bundle: state.bundle,
                  message: 'Bundler crashed. Showing files instead.'
                });
              }}
            />
          )}

          {state.type === 'files' && (
            <FileExplorer bundle={state.bundle} message={state.message} />
          )}

          {/* Files view for static/sandpack states */}
          {(state.type === 'static' || state.type === 'sandpack') && viewMode === 'files' && (
            <div className="h-full w-full">
              <div className="text-center text-[#64748B] py-4">
                <p className="text-sm">Switch to Preview mode to see the rendered output</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// File Explorer Component
interface FileExplorerProps {
  bundle: PreviewBundle;
  message: string;
}

function FileExplorer({ bundle, message }: FileExplorerProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const files = Object.entries(bundle.files);

  return (
    <div className="h-full w-full flex flex-col bg-[#0A0A0F] rounded-lg overflow-hidden">
      {/* Message Banner */}
      <div className="bg-[#1E1E2E] px-4 py-3 border-b border-[#2E2E3E]">
        <div className="flex items-center gap-2 text-[#F59E0B]">
          <AlertCircle size={16} />
          <p className="text-sm">{message}</p>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* File List */}
        <div className="w-64 border-r border-[#1E1E2E] overflow-y-auto">
          <div className="p-2">
            <div className="text-xs font-medium text-[#64748B] uppercase tracking-wider mb-2 px-2">
              Project Files ({files.length})
            </div>
            {files.map(([path]) => (
              <button
                key={path}
                onClick={() => setSelectedFile(path)}
                className={cn(
                  "w-full text-left px-2 py-1.5 rounded text-sm font-mono flex items-center gap-2 transition-colors",
                  selectedFile === path
                    ? "bg-[#8B5CF6] text-white"
                    : "text-[#94A3B8] hover:bg-[#1E1E2E] hover:text-white"
                )}
              >
                <FileCode size={14} className="shrink-0" />
                <span className="truncate">{path}</span>
              </button>
            ))}
          </div>
        </div>

        {/* File Content */}
        <div className="flex-1 overflow-hidden">
          {selectedFile ? (
            <div className="h-full flex flex-col">
              <div className="h-8 bg-[#0D0D12] border-b border-[#1E1E2E] flex items-center px-3">
                <span className="text-xs font-mono text-[#94A3B8]">{selectedFile}</span>
              </div>
              <pre className="flex-1 p-4 overflow-auto text-sm font-mono text-[#E2E8F0] bg-[#0D0D12]">
                <code>{bundle.files[selectedFile]}</code>
              </pre>
            </div>
          ) : (
            <div className="h-full flex items-center justify-center text-[#64748B]">
              <div className="text-center">
                <FileCode size={48} className="mx-auto mb-3 opacity-30" />
                <p className="text-sm">Select a file to view its contents</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Sandpack Preview Wrapper Component (simplified, with error handling)
interface SandpackPreviewWrapperProps {
  bundle: PreviewBundle;
  previewMode: 'mobile' | 'tablet' | 'desktop';
  onError?: () => void;
}

function SandpackPreviewWrapper({ bundle, previewMode, onError }: SandpackPreviewWrapperProps) {
  const [hasError, setHasError] = useState(false);

  // Convert bundle files to Sandpack format
  const sandpackFiles: Record<string, { code: string }> = {};
  
  for (const [path, content] of Object.entries(bundle.files)) {
    const sandpackPath = path.startsWith('/') ? path : `/${path}`;
    sandpackFiles[sandpackPath] = { code: content };
  }

  // Only use react-ts template (safest for in-browser bundling)
  const template = 'react-ts';

  // Add minimal entry point if missing
  if (!sandpackFiles['/index.tsx'] && !sandpackFiles['/src/index.tsx']) {
    const appFile = Object.keys(sandpackFiles).find(f => 
      f.includes('App.tsx') || f.includes('App.jsx') || f.includes('App.js')
    );
    
    if (appFile) {
      sandpackFiles['/index.tsx'] = {
        code: `import React from 'react';
import { createRoot } from 'react-dom/client';
import App from '${appFile.replace(/\.(tsx|jsx|js)$/, '')}';

const root = createRoot(document.getElementById('root')!);
root.render(<App />);`
      };
    }
  }

  const containerStyle = previewMode === 'desktop'
    ? { width: '100%', height: '100%' }
    : { width: PREVIEW_WIDTHS[previewMode], maxWidth: '100%', height: '100%' };

  if (hasError) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-[#EF4444]">
        <AlertCircle size={32} />
        <p className="text-sm mt-2">Preview failed to load</p>
        <button
          onClick={() => {
            setHasError(false);
            onError?.();
          }}
          className="mt-3 px-4 py-2 bg-[#1E1E2E] text-white rounded-lg text-sm hover:bg-[#2E2E3E]"
        >
          View Files Instead
        </button>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col">
      <div 
        className="flex-1 transition-all duration-300 bg-white rounded-lg shadow-2xl overflow-hidden border border-[#1E1E2E] mx-auto"
        style={containerStyle}
      >
        <SandpackProvider
          template={template}
          files={sandpackFiles}
          theme="dark"
          options={{
            bundlerTimeOut: 30000, // Shorter timeout
          }}
        >
          <SandpackPreview 
            showOpenInCodeSandbox={false}
            showRefreshButton={true}
            style={{ height: '100%' }}
          />
        </SandpackProvider>
      </div>
    </div>
  );
}

export default PreviewPane;
