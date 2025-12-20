'use client';

/**
 * LivePreview Component
 * 
 * Displays the live Vercel deployment in an iframe.
 * Supports accurate device viewports (Desktop, iPad, iPhone).
 * Falls back to "Coming Soon" placeholder when no deployment exists.
 */

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Monitor,
  Smartphone,
  Tablet,
  RefreshCw,
  ExternalLink,
  Maximize2,
  Minimize2,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { useFazStore } from '@/lib/faz/store';

type ViewportSize = 'desktop' | 'ipad' | 'iphone';

// Accurate device dimensions
const VIEWPORT_SIZES: Record<ViewportSize, { width: number; height: number; label: string }> = {
  desktop: { width: 1440, height: 900, label: 'Desktop (1440×900)' },
  ipad: { width: 820, height: 1180, label: 'iPad Pro 11" (820×1180)' },
  iphone: { width: 390, height: 844, label: 'iPhone 14 Pro (390×844)' },
};

interface LivePreviewProps {
  className?: string;
  externalUrl?: string; // Optional override URL
}

export function LivePreview({ className = '', externalUrl }: LivePreviewProps) {
  const { currentProject } = useFazStore();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  
  const [viewport, setViewport] = useState<ViewportSize>('desktop');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  
  // Determine the URL to display
  const previewUrl = useMemo(() => {
    if (externalUrl) return externalUrl;
    if (currentProject?.preview_url) return currentProject.preview_url;
    if (currentProject?.production_url) return currentProject.production_url;
    return null;
  }, [externalUrl, currentProject?.preview_url, currentProject?.production_url]);
  
  // Handle iframe load
  const handleIframeLoad = useCallback(() => {
    setIsLoading(false);
    setHasError(false);
  }, []);
  
  // Handle iframe error
  const handleIframeError = useCallback(() => {
    setIsLoading(false);
    setHasError(true);
  }, []);
  
  // Refresh preview
  const handleRefresh = useCallback(() => {
    setIsLoading(true);
    setHasError(false);
    setRefreshKey(prev => prev + 1);
  }, []);
  
  // Open in new tab
  const handleOpenExternal = useCallback(() => {
    if (previewUrl) {
      window.open(previewUrl, '_blank', 'noopener,noreferrer');
    }
  }, [previewUrl]);
  
  // Current viewport dimensions
  const currentViewport = VIEWPORT_SIZES[viewport];
  
  // Calculate scale to fit container
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        setContainerSize({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight
        });
      }
    };
    
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);
  
  // Calculate scale to fit viewport in container
  const scale = useMemo(() => {
    if (isFullscreen) return 1;
    
    const padding = 32; // 16px on each side
    const availableWidth = containerSize.width - padding;
    const availableHeight = containerSize.height - padding;
    
    const scaleX = availableWidth / currentViewport.width;
    const scaleY = availableHeight / currentViewport.height;
    
    return Math.min(scaleX, scaleY, 1); // Never scale up
  }, [containerSize, currentViewport, isFullscreen]);
  
  // Coming Soon placeholder
  const ComingSoonPlaceholder = () => (
    <div 
      className="w-full h-full flex flex-col items-center justify-center"
      style={{ 
        backgroundColor: '#FFF8E7', // Cream color
        color: '#F97316' // Orange
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center"
      >
        <h1 className="text-6xl font-bold mb-4" style={{ color: '#F97316' }}>
          Coming Soon
        </h1>
        <p className="text-xl opacity-70">
          {currentProject?.name || 'Your website is being built'}
        </p>
      </motion.div>
    </div>
  );
  
  return (
    <div className={`flex flex-col bg-zinc-900 rounded-lg overflow-hidden border border-zinc-700/50 ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 bg-zinc-800/80 border-b border-zinc-700/50">
        <div className="flex items-center gap-2">
          {/* URL display */}
          <div className="flex items-center gap-2 px-2 py-1 bg-zinc-900/50 rounded text-xs text-zinc-400 max-w-[200px] truncate">
            {previewUrl ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <span className="truncate">{new URL(previewUrl).hostname}</span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                <span>No deployment</span>
              </>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-1">
          {/* Viewport switcher */}
          {(Object.entries(VIEWPORT_SIZES) as [ViewportSize, typeof VIEWPORT_SIZES[ViewportSize]][]).map(([key, { label }]) => {
            const Icon = key === 'desktop' ? Monitor : key === 'ipad' ? Tablet : Smartphone;
            return (
              <button
                key={key}
                onClick={() => setViewport(key)}
                className={`p-1.5 rounded transition-colors ${
                  viewport === key 
                    ? 'bg-orange-500/20 text-orange-400' 
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700'
                }`}
                title={label}
              >
                <Icon className="w-4 h-4" />
              </button>
            );
          })}
          
          <div className="w-px h-4 bg-zinc-600 mx-1" />
          
          {/* Refresh */}
          <button
            onClick={handleRefresh}
            disabled={!previewUrl}
            className="p-1.5 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          
          {/* Fullscreen */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 transition-colors"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          
          {/* Open external */}
          {previewUrl && (
            <button
              onClick={handleOpenExternal}
              className="p-1.5 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 transition-colors"
              title="Open in New Tab"
            >
              <ExternalLink className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
      
      {/* Preview Area */}
      <div 
        ref={containerRef}
        className="flex-1 relative bg-zinc-800 overflow-hidden flex items-center justify-center p-4"
        style={{ minHeight: 400 }}
      >
        {/* Loading overlay */}
        <AnimatePresence>
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-zinc-900/80 flex items-center justify-center z-10"
            >
              <div className="text-center">
                <Loader2 className="w-8 h-8 text-orange-400 animate-spin mx-auto mb-2" />
                <p className="text-sm text-zinc-400">Loading preview...</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Error state */}
        {hasError && (
          <div className="absolute inset-0 flex items-center justify-center z-10">
            <div className="text-center text-zinc-400">
              <AlertCircle className="w-12 h-12 mx-auto mb-3 text-amber-500" />
              <p className="font-medium mb-1">Preview unavailable</p>
              <p className="text-sm">The site may still be deploying</p>
              <button
                onClick={handleRefresh}
                className="mt-3 px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        )}
        
        {/* Device frame */}
        <motion.div
          layout
          className="relative bg-black rounded-lg shadow-2xl overflow-hidden"
          style={{
            width: currentViewport.width * scale,
            height: currentViewport.height * scale,
            // Add device bezel styling
            border: viewport !== 'desktop' ? '8px solid #1a1a1a' : 'none',
            borderRadius: viewport !== 'desktop' ? 24 * scale : 8,
          }}
        >
          {previewUrl ? (
            <iframe
              ref={iframeRef}
              key={refreshKey}
              src={previewUrl}
              onLoad={handleIframeLoad}
              onError={handleIframeError}
              className="w-full h-full border-0 bg-white"
              style={{
                width: currentViewport.width,
                height: currentViewport.height,
                transform: `scale(${scale})`,
                transformOrigin: 'top left',
              }}
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
              title="Live Preview"
            />
          ) : (
            <div 
              className="overflow-hidden"
              style={{
                width: currentViewport.width,
                height: currentViewport.height,
                transform: `scale(${scale})`,
                transformOrigin: 'top left',
              }}
            >
              <ComingSoonPlaceholder />
            </div>
          )}
        </motion.div>
        
        {/* Viewport label */}
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 px-3 py-1 bg-black/50 rounded-full text-xs text-zinc-400">
          {currentViewport.label}
        </div>
      </div>
    </div>
  );
}

export default LivePreview;
