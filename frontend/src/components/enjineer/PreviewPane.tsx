'use client';

/**
 * Enjineer Preview Pane
 * 
 * Live preview system that works for ALL project types:
 * - Static HTML/CSS/JS sites
 * - React projects (rendered via React CDN + Babel)
 * - Next.js projects (rendered via React CDN + Babel with mocked Next components)
 * 
 * NO deployment required - everything renders in an iframe using backend-generated HTML.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { cn } from '@/lib/utils';
import { 
  Smartphone, Tablet, Monitor, RefreshCw, AlertCircle, 
  Loader2, Maximize2, Minimize2, ExternalLink
} from 'lucide-react';
import { enjineerApi } from '@/lib/enjineer/api';

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
  | { type: 'ready'; html: string };

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
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Load preview HTML from backend
  const loadPreview = useCallback(async () => {
    if (!projectId) {
      setState({ type: 'empty' });
      return;
    }

    setState({ type: 'loading' });

    try {
      // Backend now handles ALL project types - returns complete HTML
      const html = await enjineerApi.getPreviewHtml(projectId);
      setState({ type: 'ready', html });
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
  }, [loadPreview, refreshTrigger, refreshKey]);

  // Handle manual refresh
  const handleRefresh = () => {
    setRefreshKey(k => k + 1);
  };

  // Open in new tab
  const handleOpenInNewTab = () => {
    if (state.type === 'ready') {
      const blob = new Blob([state.html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
    }
  };

  // Get container width based on preview mode
  const getContainerStyle = () => {
    if (previewMode === 'desktop') {
      return { width: '100%', height: '100%' };
    }
    return { 
      width: PREVIEW_WIDTHS[previewMode], 
      maxWidth: '100%',
      height: '100%'
    };
  };

  return (
    <div className={cn(
      'flex flex-col h-full bg-[#0A0A0F]', 
      isFullscreen && 'fixed inset-0 z-50', 
      className
    )}>
      {/* Toolbar */}
      <div className="h-10 bg-[#0D0D12] border-b border-[#1E1E2E] flex items-center justify-between px-3 shrink-0">
        {/* Left: Device toggles */}
        <div className="flex items-center gap-2">
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
          
          {state.type === 'ready' && (
            <span className="text-xs text-[#64748B]">
              {previewMode === 'mobile' && '375px'}
              {previewMode === 'tablet' && '768px'}
              {previewMode === 'desktop' && 'Full width'}
            </span>
          )}
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-1">
          <button
            onClick={handleRefresh}
            className="p-1.5 text-[#64748B] hover:text-white transition-colors"
            title="Refresh preview"
            disabled={state.type === 'loading'}
          >
            <RefreshCw size={14} className={state.type === 'loading' ? 'animate-spin' : ''} />
          </button>
          
          {state.type === 'ready' && (
            <button
              onClick={handleOpenInNewTab}
              className="p-1.5 text-[#64748B] hover:text-white transition-colors"
              title="Open in new tab"
            >
              <ExternalLink size={14} />
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
      <div className="flex-1 overflow-hidden bg-[#12121A] flex items-center justify-center p-4">
        {state.type === 'loading' && (
          <div className="flex flex-col items-center gap-3 text-[#64748B]">
            <Loader2 size={32} className="animate-spin text-[#8B5CF6]" />
            <span className="text-sm">Loading preview...</span>
          </div>
        )}

        {state.type === 'empty' && (
          <div className="flex flex-col items-center gap-3 text-[#64748B]">
            <div className="w-16 h-16 rounded-xl bg-[#1E1E2E] flex items-center justify-center">
              <Monitor size={32} className="opacity-30" />
            </div>
            <p className="text-sm font-medium">No files to preview</p>
            <p className="text-xs">Ask Nicole to create your project files</p>
          </div>
        )}

        {state.type === 'error' && (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-xl bg-[#EF4444]/10 flex items-center justify-center">
              <AlertCircle size={32} className="text-[#EF4444]" />
            </div>
            <p className="text-sm text-[#EF4444]">{state.message}</p>
            <button
              onClick={handleRefresh}
              className="mt-2 px-4 py-2 bg-[#1E1E2E] text-white rounded-lg text-sm hover:bg-[#2E2E3E] transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {state.type === 'ready' && (
          <div 
            className="transition-all duration-300 bg-white rounded-lg shadow-2xl overflow-hidden border border-[#2E2E3E]"
            style={getContainerStyle()}
          >
            <iframe
              ref={iframeRef}
              key={refreshKey}
              srcDoc={state.html}
              className="w-full h-full border-0"
              title="Preview"
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
            />
          </div>
        )}
      </div>

      {/* Status bar */}
      {state.type === 'ready' && (
        <div className="h-6 bg-[#0D0D12] border-t border-[#1E1E2E] flex items-center px-3 text-xs text-[#64748B]">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-[#10B981]"></span>
            Live Preview
          </span>
          <span className="mx-2">•</span>
          <span>React/Next.js rendered via CDN</span>
        </div>
      )}
    </div>
  );
}

export default PreviewPane;
