'use client';

/**
 * Enjineer Preview Pane
 * 
 * Versatile preview system that supports:
 * - Static HTML/CSS/JS sites (iframe with srcdoc)
 * - React/TypeScript projects (Sandpack in-browser bundling)
 * - Next.js projects (Sandpack with Next template)
 * - Responsive preview modes (mobile, tablet, desktop)
 * - Live refresh when files change
 * - Console output capture
 * - Error boundary
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { cn } from '@/lib/utils';
import { 
  Smartphone, Tablet, Monitor, RefreshCw, AlertCircle, 
  Loader2, Terminal, Maximize2, Minimize2,
  Play, Pause
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

const SandpackConsole = dynamic(
  () => import('@codesandbox/sandpack-react').then(mod => mod.SandpackConsole),
  { ssr: false }
);

// Types
interface PreviewPaneProps {
  projectId: number | null;
  previewMode: 'mobile' | 'tablet' | 'desktop';
  onModeChange?: (mode: 'mobile' | 'tablet' | 'desktop') => void;
  className?: string;
  refreshTrigger?: number; // Increment to force refresh
}

type PreviewState = 
  | { type: 'loading' }
  | { type: 'empty' }
  | { type: 'error'; message: string }
  | { type: 'static'; html: string }
  | { type: 'sandpack'; bundle: PreviewBundle };

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
  const [showConsole, setShowConsole] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const lastRefresh = useRef(Date.now());

  // Load preview bundle
  const loadPreview = useCallback(async () => {
    if (!projectId) {
      setState({ type: 'empty' });
      return;
    }

    setState({ type: 'loading' });
    lastRefresh.current = Date.now();

    try {
      const bundle = await enjineerApi.getPreviewBundle(projectId);
      
      if (Object.keys(bundle.files).length === 0) {
        setState({ type: 'empty' });
        return;
      }

      // Decide rendering strategy based on project type
      if (bundle.project_type === 'static' || bundle.project_type === 'html') {
        // For static sites, get the rendered HTML
        const html = await enjineerApi.getPreviewHtml(projectId);
        setState({ type: 'static', html });
      } else {
        // For React/Next.js, use Sandpack
        setState({ type: 'sandpack', bundle });
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

  // Manual refresh handler
  const handleRefresh = () => {
    loadPreview();
  };

  // Get container width based on preview mode
  const containerStyle = previewMode === 'desktop' 
    ? { width: '100%' }
    : { width: PREVIEW_WIDTHS[previewMode], maxWidth: '100%' };

  return (
    <div className={cn('flex flex-col h-full bg-[#0A0A0F]', isFullscreen && 'fixed inset-0 z-50', className)}>
      {/* Toolbar */}
      <div className="h-10 bg-[#0D0D12] border-b border-[#1E1E2E] flex items-center justify-between px-3 shrink-0">
        {/* Left: Device toggles */}
        <div className="flex items-center gap-1">
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
          
          {state.type !== 'loading' && state.type !== 'empty' && (
            <span className="ml-2 text-xs text-[#64748B]">
              {previewMode === 'mobile' && '375px'}
              {previewMode === 'tablet' && '768px'}
              {previewMode === 'desktop' && 'Full width'}
            </span>
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
            onClick={handleRefresh}
            className="p-1.5 text-[#64748B] hover:text-white transition-colors"
            title="Refresh preview"
            disabled={state.type === 'loading'}
          >
            <RefreshCw size={14} className={state.type === 'loading' ? 'animate-spin' : ''} />
          </button>
          
          {(state.type === 'sandpack' || state.type === 'static') && (
            <button
              onClick={() => setShowConsole(!showConsole)}
              className={cn(
                "p-1.5 rounded transition-colors",
                showConsole ? "text-[#8B5CF6]" : "text-[#64748B] hover:text-white"
              )}
              title="Toggle console"
            >
              <Terminal size={14} />
            </button>
          )}
          
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
      <div className="flex-1 overflow-hidden flex flex-col">
        <div className="flex-1 flex items-center justify-center p-4 overflow-auto">
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
                onClick={handleRefresh}
                className="mt-2 px-4 py-2 bg-[#1E1E2E] text-white rounded-lg text-sm hover:bg-[#2E2E3E] transition-colors"
              >
                Retry
              </button>
            </div>
          )}

          {state.type === 'static' && (
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

          {state.type === 'sandpack' && (
            <SandpackPreviewWrapper 
              bundle={state.bundle}
              previewMode={previewMode}
              showConsole={showConsole}
            />
          )}
        </div>

        {/* Console Panel (for static preview) */}
        {state.type === 'static' && showConsole && (
          <div className="h-48 border-t border-[#1E1E2E] bg-[#0D0D12]">
            <div className="h-8 flex items-center px-3 border-b border-[#1E1E2E]">
              <span className="text-xs font-medium text-[#64748B]">Console</span>
            </div>
            <div className="p-3 font-mono text-xs text-[#94A3B8]">
              <div className="flex items-center gap-2 text-[#64748B]">
                <Terminal size={12} />
                <span>Console output will appear here...</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Sandpack Preview Wrapper Component
interface SandpackPreviewWrapperProps {
  bundle: PreviewBundle;
  previewMode: 'mobile' | 'tablet' | 'desktop';
  showConsole: boolean;
}

function SandpackPreviewWrapper({ bundle, previewMode, showConsole }: SandpackPreviewWrapperProps) {
  // Convert bundle files to Sandpack format
  const sandpackFiles: Record<string, { code: string }> = {};
  
  for (const [path, content] of Object.entries(bundle.files)) {
    // Sandpack expects paths without leading slash for most files
    const sandpackPath = path.startsWith('/') ? path : `/${path}`;
    sandpackFiles[sandpackPath] = { code: content };
  }

  // Determine template based on project type
  const template = bundle.project_type === 'nextjs' 
    ? 'nextjs' 
    : bundle.project_type === 'react' 
      ? 'react-ts' 
      : 'vanilla-ts';

  // Add default files if missing for React projects
  if (bundle.project_type === 'react' && !sandpackFiles['/index.tsx'] && !sandpackFiles['/src/index.tsx']) {
    // Find the main app file
    const appFile = Object.keys(sandpackFiles).find(f => 
      f.includes('App.tsx') || f.includes('App.jsx') || f.includes('App.js')
    );
    
    if (appFile && !sandpackFiles['/index.tsx']) {
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

  return (
    <div className="h-full w-full flex flex-col">
      <div 
        className="flex-1 transition-all duration-300 bg-white rounded-lg shadow-2xl overflow-hidden border border-[#1E1E2E] mx-auto"
        style={containerStyle}
      >
        <SandpackProvider
          template={template}
          files={sandpackFiles}
          customSetup={{
            dependencies: bundle.dependencies,
            entry: bundle.entry_file,
          }}
          theme="dark"
          options={{
            bundlerTimeOut: 60000,
            skipEval: false,
          }}
        >
          <div className="h-full flex flex-col">
            <div className={showConsole ? 'flex-1' : 'h-full'}>
              <SandpackPreview 
                showOpenInCodeSandbox={false}
                showRefreshButton={false}
                style={{ height: '100%' }}
              />
            </div>
            {showConsole && (
              <div className="h-48 border-t border-[#1E1E2E]">
                <SandpackConsole 
                  showHeader={true}
                  showResetConsoleButton={true}
                  style={{ height: '100%' }}
                />
              </div>
            )}
          </div>
        </SandpackProvider>
      </div>
    </div>
  );
}

export default PreviewPane;

