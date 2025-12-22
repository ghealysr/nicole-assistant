'use client';

/**
 * Enjineer Preview Pane
 * 
 * Live preview via Vercel preview deployments with persistent URLs.
 * Each project gets a permanent preview domain: project-{id}.enjineer.alphawavetech.com
 * 
 * Features:
 * - Persistent preview URLs
 * - Auto-cleanup of old deployments
 * - Production deployment with custom domain support
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { cn } from '@/lib/utils';
import { 
  Smartphone, Tablet, Monitor, AlertCircle, 
  Loader2, Maximize2, Minimize2, ExternalLink, Rocket, 
  Globe, CheckCircle2, Clock
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

export function PreviewPane({ 
  projectId, 
  previewMode,
  onModeChange,
  className,
  refreshTrigger = 0
}: PreviewPaneProps) {
  const [state, setState] = useState<PreviewState>({ type: 'loading' });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

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
      setState({ 
        type: 'error', 
        message: error instanceof Error ? error.message : 'Failed to deploy preview' 
      });
    }
  }, [projectId]);

  // Open URL in new tab
  const openUrl = (url: string) => {
    window.open(url, '_blank', 'noopener,noreferrer');
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
          
          {(state.type === 'ready' || state.type === 'idle' && state.existingPreview) && (
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
            <span className="text-sm">Loading preview info...</span>
          </div>
        )}

        {/* Idle State - Show deploy button or existing preview */}
        {state.type === 'idle' && (
          <div className="flex flex-col items-center gap-6 text-center max-w-md">
            {state.existingPreview ? (
              <>
                {/* Existing preview available */}
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[#10B981]/20 to-[#059669]/20 flex items-center justify-center">
                  <Globe size={40} className="text-[#10B981]" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-white mb-2">Preview Available</h3>
                  <p className="text-sm text-[#64748B] mb-3">
                    Your project has an existing preview deployment.
                  </p>
                  
                  {/* Domain Badge */}
                  {state.existingPreview.domain && (
                    <div className="bg-[#1E1E2E] rounded-lg px-4 py-2 text-xs text-[#10B981] font-mono break-all mb-2">
                      {state.existingPreview.domain}
                    </div>
                  )}
                  
                  {/* Last deployed time */}
                  {state.existingPreview.lastDeployedAt && (
                    <div className="flex items-center justify-center gap-1 text-xs text-[#64748B]">
                      <Clock size={12} />
                      <span>Updated {formatRelativeTime(state.existingPreview.lastDeployedAt)}</span>
                    </div>
                  )}
                </div>
                
                <div className="flex gap-3">
                  <a
                    href={state.existingPreview.domain || state.existingPreview.lastUrl!}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-6 py-3 rounded-lg font-medium bg-[#10B981] hover:bg-[#059669] text-white transition-all flex items-center gap-2"
                  >
                    <ExternalLink size={18} />
                    View Preview
                  </a>
                  <button
                    onClick={deployPreview}
                    disabled={!projectId}
                    className="px-6 py-3 rounded-lg font-medium bg-[#1E1E2E] hover:bg-[#2E2E3E] text-white transition-all flex items-center gap-2"
                  >
                    <Rocket size={18} />
                    Update
                  </button>
                </div>
              </>
            ) : (
              <>
                {/* No preview yet */}
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[#8B5CF6]/20 to-[#6366F1]/20 flex items-center justify-center">
                  <Rocket size={40} className="text-[#8B5CF6]" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-white mb-2">Preview Your Project</h3>
                  <p className="text-sm text-[#64748B]">
                    Deploy to see your project live. Each project gets a permanent preview URL.
                  </p>
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
                
                {/* Persistent URL hint */}
                <div className="text-xs text-[#64748B] bg-[#1E1E2E]/50 px-4 py-2 rounded-lg">
                  <span className="text-[#8B5CF6]">project-{projectId}</span>.enjineer.alphawavetech.com
                </div>
              </>
            )}
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
                {state.previewDomain}
              </div>
            )}
          </div>
        )}

        {/* Ready State */}
        {state.type === 'ready' && (
          <div className="flex flex-col items-center gap-6 text-center max-w-lg">
            <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-[#10B981]/20 to-[#059669]/20 flex items-center justify-center">
              <div className="w-16 h-16 rounded-xl bg-[#10B981] flex items-center justify-center">
                <CheckCircle2 size={32} className="text-white" />
              </div>
            </div>
            
            <div>
              <h3 className="text-xl font-semibold text-white mb-2">Preview Ready! 🎉</h3>
              <p className="text-sm text-[#64748B] mb-4">
                Your project has been deployed successfully.
              </p>
              
              {/* Persistent Domain */}
              {state.previewDomain && (
                <button
                  onClick={() => openUrl(state.previewDomain!)}
                  className="group bg-[#1E1E2E] hover:bg-[#2E2E3E] rounded-lg px-4 py-3 w-full transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="text-left">
                      <div className="text-xs text-[#64748B] mb-1">Persistent URL</div>
                      <div className="text-sm text-[#10B981] font-mono break-all">
                        {state.previewDomain}
                      </div>
                    </div>
                    <ExternalLink size={16} className="text-[#64748B] group-hover:text-white transition-colors" />
                  </div>
                </button>
              )}
            </div>
            
            <div className="flex gap-3">
              <button
                onClick={() => openUrl(state.previewDomain || state.deployment.url)}
                className="px-6 py-3 rounded-lg font-medium bg-[#8B5CF6] hover:bg-[#7C3AED] text-white transition-all flex items-center gap-2"
              >
                <ExternalLink size={18} />
                Open Preview
              </button>
            </div>
            
            <p className="text-xs text-[#64748B]">
              This URL will always show your latest preview deployment.
            </p>
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
      {(state.type === 'ready' || state.type === 'building') && (
        <div className="h-6 bg-[#0D0D12] border-t border-[#1E1E2E] flex items-center px-3 text-xs text-[#64748B]">
          <span className="flex items-center gap-1.5">
            <span className={cn(
              "w-2 h-2 rounded-full",
              state.type === 'ready' ? "bg-[#10B981]" : "bg-[#F59E0B] animate-pulse"
            )}></span>
            {state.type === 'ready' ? 'Live' : 'Building'}
          </span>
          <span className="mx-2">•</span>
          <span className="truncate">
            {state.type === 'ready' 
              ? (state.previewDomain || state.deployment.url)
              : 'Deploying to Vercel...'}
          </span>
        </div>
      )}
    </div>
  );
}

export default PreviewPane;
