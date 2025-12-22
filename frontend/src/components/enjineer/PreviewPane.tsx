'use client';

/**
 * Enjineer Preview Pane
 * 
 * Live preview via Vercel preview deployments.
 * Deploys project files to Vercel for real preview, with automatic cleanup.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { cn } from '@/lib/utils';
import { 
  Smartphone, Tablet, Monitor, AlertCircle, 
  Loader2, Maximize2, Minimize2, ExternalLink, Rocket, Trash2
} from 'lucide-react';
import { enjineerApi } from '@/lib/enjineer/api';

interface PreviewPaneProps {
  projectId: number | null;
  previewMode: 'mobile' | 'tablet' | 'desktop';
  onModeChange?: (mode: 'mobile' | 'tablet' | 'desktop') => void;
  className?: string;
  refreshTrigger?: number;
}

interface DeploymentState {
  id: string;
  url: string;
  status: 'building' | 'ready' | 'error';
}

type PreviewState = 
  | { type: 'idle' }
  | { type: 'deploying' }
  | { type: 'building'; deployment: DeploymentState }
  | { type: 'ready'; deployment: DeploymentState }
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
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  refreshTrigger: _refreshTrigger = 0
}: PreviewPaneProps) {
  const [state, setState] = useState<PreviewState>({ type: 'idle' });
  const [isFullscreen, setIsFullscreen] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

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
      setState({ type: 'idle' });
      return;
    }

    setState({ type: 'deploying' });

    try {
      const result = await enjineerApi.deployPreview(projectId);
      
      const deployment: DeploymentState = {
        id: result.deployment_id,
        url: result.url,
        status: 'building'
      };
      
      setState({ type: 'building', deployment });
      
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
              deployment: { ...deployment, status: 'ready', url: status.url }
            });
          } else if (status.status === 'ERROR' || status.status === 'CANCELED') {
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setState({ 
              type: 'error', 
              message: 'Deployment failed. Check your project files.' 
            });
          }
        } catch (error) {
          console.error('Error polling deployment status:', error);
        }
      }, 3000); // Poll every 3 seconds
      
    } catch (error) {
      console.error('Deploy error:', error);
      setState({ 
        type: 'error', 
        message: error instanceof Error ? error.message : 'Failed to deploy preview' 
      });
    }
  }, [projectId]);

  // Delete deployment
  const deleteDeployment = useCallback(async () => {
    if (state.type !== 'ready' && state.type !== 'building') return;
    
    const deploymentId = state.deployment.id;
    
    try {
      await enjineerApi.deletePreview(projectId!, deploymentId);
      setState({ type: 'idle' });
    } catch (error) {
      console.error('Error deleting deployment:', error);
    }
  }, [projectId, state]);

  // Open in new tab
  const handleOpenInNewTab = () => {
    if (state.type === 'ready') {
      window.open(state.deployment.url, '_blank');
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
          {state.type === 'ready' && (
            <>
              <button
                onClick={handleOpenInNewTab}
                className="p-1.5 text-[#64748B] hover:text-white transition-colors"
                title="Open in new tab"
              >
                <ExternalLink size={14} />
              </button>
              <button
                onClick={deleteDeployment}
                className="p-1.5 text-[#64748B] hover:text-[#EF4444] transition-colors"
                title="Delete preview deployment"
              >
                <Trash2 size={14} />
              </button>
            </>
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
        {/* Idle State - Show deploy button */}
        {state.type === 'idle' && (
          <div className="flex flex-col items-center gap-4 text-center max-w-md">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[#8B5CF6]/20 to-[#6366F1]/20 flex items-center justify-center">
              <Rocket size={40} className="text-[#8B5CF6]" />
            </div>
            <div>
              <h3 className="text-lg font-medium text-white mb-2">Preview Your Project</h3>
              <p className="text-sm text-[#64748B]">
                Deploy a live preview to see your project in action. 
                Previews are temporary and can be deleted anytime.
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
              <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-[#F59E0B] flex items-center justify-center">
                <span className="text-xs">⏳</span>
              </div>
            </div>
            <div>
              <h3 className="text-white font-medium mb-1">Building Preview</h3>
              <p className="text-sm text-[#64748B]">
                This usually takes 30-60 seconds...
              </p>
            </div>
            <div className="text-xs text-[#64748B] bg-[#1E1E2E] px-3 py-1.5 rounded-full">
              Deployment: {state.deployment.id.slice(0, 12)}...
            </div>
          </div>
        )}

        {/* Ready State - Show preview link (iframes blocked by Vercel X-Frame-Options) */}
        {state.type === 'ready' && (
          <div className="flex flex-col items-center gap-6 text-center max-w-lg">
            <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-[#10B981]/20 to-[#059669]/20 flex items-center justify-center">
              <div className="w-16 h-16 rounded-xl bg-[#10B981] flex items-center justify-center">
                <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>
            
            <div>
              <h3 className="text-xl font-semibold text-white mb-2">Preview Ready! 🎉</h3>
              <p className="text-sm text-[#64748B] mb-4">
                Your project has been deployed successfully.
              </p>
              <div className="bg-[#1E1E2E] rounded-lg px-4 py-2 text-xs text-[#8B5CF6] font-mono break-all">
                {state.deployment.url}
              </div>
            </div>
            
            <div className="flex gap-3">
              <a
                href={state.deployment.url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 rounded-lg font-medium bg-[#8B5CF6] hover:bg-[#7C3AED] text-white transition-all flex items-center gap-2"
              >
                <ExternalLink size={18} />
                Open Preview
              </a>
              <button
                onClick={deleteDeployment}
                className="px-4 py-3 rounded-lg font-medium bg-[#1E1E2E] hover:bg-[#2E2E3E] text-[#64748B] hover:text-[#EF4444] transition-all flex items-center gap-2"
                title="Delete this preview deployment"
              >
                <Trash2 size={18} />
              </button>
            </div>
            
            <p className="text-xs text-[#64748B]">
              Preview deployments are temporary and can be deleted anytime.
            </p>
          </div>
        )}

        {/* Error State */}
        {state.type === 'error' && (
          <div className="flex flex-col items-center gap-3">
            <div className="w-16 h-16 rounded-xl bg-[#EF4444]/10 flex items-center justify-center">
              <AlertCircle size={32} className="text-[#EF4444]" />
            </div>
            <p className="text-sm text-[#EF4444]">{state.message}</p>
            <button
              onClick={deployPreview}
              className="mt-2 px-4 py-2 bg-[#1E1E2E] text-white rounded-lg text-sm hover:bg-[#2E2E3E] transition-colors"
            >
              Try Again
            </button>
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
          <span className="truncate">{state.deployment.url}</span>
        </div>
      )}
    </div>
  );
}

export default PreviewPane;
