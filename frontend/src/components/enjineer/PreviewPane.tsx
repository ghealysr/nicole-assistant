'use client';

/**
 * Enjineer Preview Pane
 * 
 * Live preview via Vercel with in-dashboard iframe display.
 * Each project gets a permanent preview domain: project-{id}.enjineer.alphawavetech.com
 * 
 * Features:
 * - Persistent preview URLs with custom domains
 * - In-dashboard iframe preview (enabled by vercel.json headers)
 * - Responsive device simulation (mobile/tablet/desktop)
 * - Auto-cleanup of old deployments
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { cn } from '@/lib/utils';
import { 
  Smartphone, Tablet, Monitor, AlertCircle, 
  Loader2, Maximize2, Minimize2, ExternalLink, Rocket, 
  RefreshCw, Clock
} from 'lucide-react';
import { enjineerApi } from '@/lib/enjineer/api';

interface PreviewPaneProps {
  projectId: number | null;
  previewMode: 'mobile' | 'tablet' | 'desktop';
  onModeChange?: (mode: 'mobile' | 'tablet' | 'desktop') => void;
  className?: string;
  refreshTrigger?: number;
}

interface DeploymentInfo {
  id: string;
  url: string;
}

interface PreviewInfo {
  domain: string | null;
  lastUrl: string | null;
  lastDeployedAt: string | null;
}

type PreviewState = 
  | { type: 'loading' }
  | { type: 'idle'; existingPreview: PreviewInfo | null }
  | { type: 'deploying' }
  | { type: 'building'; deployment: DeploymentInfo; previewDomain: string | null }
  | { type: 'ready'; deployment: DeploymentInfo; previewDomain: string | null }
  | { type: 'error'; message: string };

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
  const [iframeKey, setIframeKey] = useState(0);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Load existing preview info on mount or project change
  useEffect(() => {
    const loadPreviewInfo = async () => {
      if (!projectId) {
        setState({ type: 'idle', existingPreview: null });
        return;
      }

      try {
        const info = await enjineerApi.getPreviewInfo(projectId);
        setState({ 
          type: 'idle', 
          existingPreview: info.preview.last_url ? {
            domain: info.preview.domain,
            lastUrl: info.preview.last_url,
            lastDeployedAt: info.preview.last_deployed_at
          } : null
        });
      } catch (error) {
        console.warn('Failed to load preview info:', error);
        setState({ type: 'idle', existingPreview: null });
      }
    };

    loadPreviewInfo();
  }, [projectId, refreshTrigger]);

  // Stop polling when component unmounts
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  // Deploy preview
  const deployPreview = useCallback(async () => {
    if (!projectId) {
      setState({ type: 'idle', existingPreview: null });
      return;
    }

    setState({ type: 'deploying' });

    try {
      const result = await enjineerApi.deployPreview(projectId);
      
      const deployment: DeploymentInfo = {
        id: result.deployment_id,
        url: result.url
      };
      
      setState({ 
        type: 'building', 
        deployment,
        previewDomain: result.preview_domain
      });
      
      // Poll for deployment status
      pollIntervalRef.current = setInterval(async () => {
        try {
          const status = await enjineerApi.getPreviewStatus(projectId, deployment.id);
          
          if (status.status === 'READY') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setState({ 
              type: 'ready', 
              deployment: { id: deployment.id, url: status.url },
              previewDomain: result.preview_domain
            });
            // Force iframe refresh
            setIframeKey(k => k + 1);
          } else if (status.status === 'ERROR' || status.status === 'CANCELED') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setState({ 
              type: 'error', 
              message: 'Deployment failed. Check your project files for errors.' 
            });
          }
        } catch (error) {
          console.error('Error polling deployment status:', error);
        }
      }, 3000);
      
    } catch (error) {
      console.error('Deploy error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to deploy preview';
      
      // Check if it's an auth error
      if (errorMessage.includes('Invalid or expired token') || errorMessage.includes('401')) {
        setState({ 
          type: 'error', 
          message: 'Session expired. Please refresh the page to continue.' 
        });
      } else {
        setState({ 
          type: 'error', 
          message: errorMessage 
        });
      }
    }
  }, [projectId]);

  // Refresh iframe
  const refreshPreview = () => {
    setIframeKey(k => k + 1);
  };

  // Open URL in new tab
  const openInNewTab = (url: string) => {
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Get the current preview URL
  const getPreviewUrl = (): string | null => {
    if (state.type === 'ready') {
      return state.previewDomain || state.deployment.url;
    }
    if (state.type === 'idle' && state.existingPreview) {
      return state.existingPreview.domain || state.existingPreview.lastUrl;
    }
    return null;
  };

  // Format relative time
  const formatRelativeTime = (isoString: string | null) => {
    if (!isoString) return null;
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  };

  // Get container style for device preview
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

  // Check if we have a preview to show
  const hasPreview = state.type === 'ready' || (state.type === 'idle' && state.existingPreview);
  const previewUrl = getPreviewUrl();

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
          
          {hasPreview && (
            <span className="text-xs text-[#64748B]">
              {previewMode === 'mobile' && '375px'}
              {previewMode === 'tablet' && '768px'}
              {previewMode === 'desktop' && 'Full'}
            </span>
          )}
        </div>

        {/* Center: URL */}
        {previewUrl && (
          <div className="flex-1 mx-4 max-w-md">
            <div className="bg-[#12121A] rounded px-3 py-1 text-xs text-[#64748B] truncate text-center">
              {previewUrl.replace('https://', '')}
            </div>
          </div>
        )}

        {/* Right: Actions */}
        <div className="flex items-center gap-1">
          {hasPreview && (
            <>
              <button
                onClick={refreshPreview}
                className="p-1.5 text-[#64748B] hover:text-white transition-colors"
                title="Refresh preview"
              >
                <RefreshCw size={14} />
              </button>
              <button
                onClick={() => previewUrl && openInNewTab(previewUrl)}
                className="p-1.5 text-[#64748B] hover:text-white transition-colors"
                title="Open in new tab"
              >
                <ExternalLink size={14} />
              </button>
            </>
          )}
          <button
            onClick={deployPreview}
            disabled={!projectId || state.type === 'deploying' || state.type === 'building'}
            className={cn(
              "px-2 py-1 text-xs rounded transition-colors flex items-center gap-1",
              state.type === 'deploying' || state.type === 'building'
                ? "bg-[#1E1E2E] text-[#64748B] cursor-not-allowed"
                : "bg-[#8B5CF6] hover:bg-[#7C3AED] text-white"
            )}
            title={hasPreview ? "Update preview" : "Deploy preview"}
          >
            {state.type === 'deploying' || state.type === 'building' ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <Rocket size={12} />
            )}
            {hasPreview ? 'Update' : 'Deploy'}
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
      <div className="flex-1 overflow-hidden bg-[#12121A] flex items-center justify-center p-4">
        {/* Loading State */}
        {state.type === 'loading' && (
          <div className="flex flex-col items-center gap-3 text-[#64748B]">
            <Loader2 size={32} className="animate-spin text-[#8B5CF6]" />
            <span className="text-sm">Loading...</span>
          </div>
        )}

        {/* Idle State - No preview yet */}
        {state.type === 'idle' && !state.existingPreview && (
          <div className="flex flex-col items-center gap-6 text-center max-w-md">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[#8B5CF6]/20 to-[#6366F1]/20 flex items-center justify-center">
              <Rocket size={40} className="text-[#8B5CF6]" />
            </div>
            <div>
              <h3 className="text-lg font-medium text-white mb-2">Preview Your Project</h3>
              <p className="text-sm text-[#64748B] mb-4">
                Deploy to see your project live in this panel.
              </p>
              {/* Persistent URL hint */}
              <div className="text-xs text-[#64748B] bg-[#1E1E2E]/50 px-4 py-2 rounded-lg inline-block">
                <span className="text-[#8B5CF6]">project-{projectId}</span>.enjineer.alphawavetech.com
              </div>
            </div>
            <button
              onClick={deployPreview}
              disabled={!projectId}
              className={cn(
                "px-6 py-3 rounded-lg font-medium transition-all flex items-center gap-2",
                projectId 
                  ? "bg-[#8B5CF6] hover:bg-[#7C3AED] text-white" 
                  : "bg-[#1E1E2E] text-[#64748B] cursor-not-allowed"
              )}
            >
              <Rocket size={18} />
              Deploy Preview
            </button>
          </div>
        )}

        {/* Idle State WITH existing preview - Show preview or prompt to update */}
        {state.type === 'idle' && state.existingPreview && previewUrl && (
          <div className="relative w-full h-full">
            {/* Iframe */}
            <div 
              className="transition-all duration-300 bg-white rounded-lg shadow-2xl overflow-hidden border border-[#2E2E3E]"
              style={getContainerStyle()}
            >
              <iframe
                ref={iframeRef}
                key={iframeKey}
                src={previewUrl}
                className="w-full h-full border-0"
                title="Preview"
                sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
              />
            </div>
            
            {/* Hint banner for stale previews */}
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-[#1E1E2E]/95 backdrop-blur-sm border border-[#2E2E3E] rounded-lg px-4 py-2 flex items-center gap-3 text-xs shadow-lg">
              <span className="text-[#94A3B8]">
                Seeing an error? Old previews expire after cleanup.
              </span>
              <button
                onClick={deployPreview}
                className="bg-[#8B5CF6] hover:bg-[#7C3AED] text-white px-3 py-1 rounded text-xs font-medium transition-colors"
              >
                Redeploy
              </button>
            </div>
          </div>
        )}

        {/* Deploying State */}
        {state.type === 'deploying' && (
          <div className="flex flex-col items-center gap-3 text-[#64748B]">
            <Loader2 size={32} className="animate-spin text-[#8B5CF6]" />
            <span className="text-sm">Starting deployment...</span>
          </div>
        )}

        {/* Building State */}
        {state.type === 'building' && (
          <div className="flex flex-col items-center gap-4 text-center">
            <div className="relative">
              <div className="w-20 h-20 rounded-2xl bg-[#8B5CF6]/10 flex items-center justify-center">
                <Loader2 size={36} className="animate-spin text-[#8B5CF6]" />
              </div>
              <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-[#F59E0B] flex items-center justify-center animate-pulse">
                <span className="text-xs">⏳</span>
              </div>
            </div>
            <div>
              <h3 className="text-white font-medium mb-1">Building Preview</h3>
              <p className="text-sm text-[#64748B]">
                This usually takes 30-60 seconds...
              </p>
            </div>
            
            {/* Progress indicator */}
            <div className="w-48 h-1 bg-[#1E1E2E] rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-[#8B5CF6] to-[#6366F1] animate-pulse" style={{ width: '60%' }} />
            </div>
            
            {state.previewDomain && (
              <div className="text-xs text-[#64748B] bg-[#1E1E2E] px-3 py-1.5 rounded-full">
                {state.previewDomain.replace('https://', '')}
              </div>
            )}
          </div>
        )}

        {/* Ready State - Show iframe */}
        {state.type === 'ready' && previewUrl && (
          <div 
            className="transition-all duration-300 bg-white rounded-lg shadow-2xl overflow-hidden border border-[#2E2E3E]"
            style={getContainerStyle()}
          >
            <iframe
              ref={iframeRef}
              key={iframeKey}
              src={previewUrl}
              className="w-full h-full border-0"
              title="Preview"
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
            />
          </div>
        )}

        {/* Error State */}
        {state.type === 'error' && (
          <div className="flex flex-col items-center gap-4 max-w-md text-center">
            <div className="w-16 h-16 rounded-xl bg-[#EF4444]/10 flex items-center justify-center">
              <AlertCircle size={32} className="text-[#EF4444]" />
            </div>
            <div>
              <h3 className="text-lg font-medium text-[#EF4444] mb-2">Deployment Failed</h3>
              <p className="text-sm text-[#64748B]">{state.message}</p>
            </div>
            <button
              onClick={deployPreview}
              className="px-6 py-3 bg-[#1E1E2E] hover:bg-[#2E2E3E] text-white rounded-lg font-medium transition-colors flex items-center gap-2"
            >
              <Rocket size={18} />
              Try Again
            </button>
          </div>
        )}
      </div>

      {/* Status bar */}
      {(hasPreview || state.type === 'building') && (
        <div className="h-6 bg-[#0D0D12] border-t border-[#1E1E2E] flex items-center justify-between px-3 text-xs text-[#64748B]">
          <span className="flex items-center gap-1.5">
            <span className={cn(
              "w-2 h-2 rounded-full",
              state.type === 'building' ? "bg-[#F59E0B] animate-pulse" : "bg-[#10B981]"
            )}></span>
            {state.type === 'building' ? 'Building' : 'Live'}
          </span>
          {state.type === 'idle' && state.existingPreview?.lastDeployedAt && (
            <span className="flex items-center gap-1">
              <Clock size={10} />
              Updated {formatRelativeTime(state.existingPreview.lastDeployedAt)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export default PreviewPane;
