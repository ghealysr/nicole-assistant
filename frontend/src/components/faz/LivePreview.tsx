'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Maximize2, Minimize2, RefreshCw, Smartphone, Tablet, Monitor,
  ExternalLink, Loader2, AlertCircle
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { useFazStore } from '@/lib/faz/store';

type ViewportMode = 'desktop' | 'tablet' | 'mobile';

const VIEWPORT_SIZES: Record<ViewportMode, { width: number; height: number; label: string }> = {
  desktop: { width: 1280, height: 800, label: 'Desktop' },
  tablet: { width: 768, height: 1024, label: 'iPad' },
  mobile: { width: 375, height: 812, label: 'iPhone' }
};

interface LivePreviewProps {
  className?: string;
}

// Coming Soon placeholder with cream background and orange text
function ComingSoonPlaceholder() {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-[#FFF8E7]">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center"
      >
        <h1 className="text-5xl md:text-7xl font-bold text-orange-500 mb-4">
          Coming Soon
        </h1>
        <div className="w-24 h-1 bg-orange-400 mx-auto rounded-full" />
        <p className="mt-6 text-orange-400/70 text-lg">
          Your site is being built...
        </p>
      </motion.div>
    </div>
  );
}

// Error state placeholder
function ErrorPlaceholder({ message }: { message?: string }) {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-zinc-900/50">
      <AlertCircle className="w-12 h-12 text-red-400/50 mb-4" />
      <p className="text-zinc-500 text-sm">{message || 'Failed to load preview'}</p>
    </div>
  );
}

// Loading state placeholder
function LoadingPlaceholder() {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-zinc-900/50">
      <Loader2 className="w-8 h-8 text-orange-400 animate-spin mb-4" />
      <p className="text-zinc-500 text-sm">Loading preview...</p>
    </div>
  );
}

export function LivePreview({ className }: LivePreviewProps) {
  const [viewport, setViewport] = useState<ViewportMode>('desktop');
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  
  const { currentProject, files } = useFazStore();
  
  // Determine what to show in the preview
  const productionUrl = currentProject?.production_url;
  const hasFiles = files.length > 0;
  const showLivePreview = !!productionUrl;
  const showLocalPreview = !showLivePreview && hasFiles;
  const showComingSoon = !showLivePreview && !showLocalPreview;

  // Generate local preview HTML from files
  const generateLocalPreview = useCallback(() => {
    if (!files.length) return '';
    
    // Find index.html or main page
    const indexHtml = files.find(f => 
      f.path.endsWith('index.html') || 
      f.path.endsWith('page.tsx') ||
      f.path.endsWith('index.tsx')
    );
    
    const cssFiles = files.filter(f => 
      f.path.endsWith('.css') || 
      f.path.endsWith('.scss')
    );
    
    if (indexHtml) {
      // If we have an HTML file, use it directly
      if (indexHtml.path.endsWith('.html')) {
        let html = indexHtml.content || '';
        
        // Inject CSS files
        if (cssFiles.length > 0) {
          const cssContent = cssFiles.map(f => f.content).join('\n');
          html = html.replace('</head>', `<style>${cssContent}</style></head>`);
        }
        
        return html;
      }
      
      // For TSX files, create a simple preview wrapper
      return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Preview</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #FFF8E7;
      color: #333;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .preview-notice {
      text-align: center;
      padding: 2rem;
    }
    h1 { 
      font-size: 3rem; 
      color: #F97316; 
      margin-bottom: 1rem;
    }
    p { 
      color: #9CA3AF; 
      font-size: 0.875rem;
    }
    .file-count {
      margin-top: 1.5rem;
      padding: 0.5rem 1rem;
      background: rgba(249, 115, 22, 0.1);
      border-radius: 0.5rem;
      color: #F97316;
      font-size: 0.75rem;
    }
  </style>
</head>
<body>
  <div class="preview-notice">
    <h1>Building...</h1>
    <p>React components are being generated.</p>
    <p class="file-count">${files.length} file${files.length !== 1 ? 's' : ''} created</p>
  </div>
</body>
</html>
      `;
    }
    
    // Default: show file list
    return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Preview</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #0A0A0F;
      color: #E5E7EB;
      padding: 2rem;
    }
    h2 { 
      color: #F97316; 
      margin-bottom: 1rem;
      font-size: 1.25rem;
    }
    .file-list {
      list-style: none;
      font-family: 'SF Mono', Monaco, Consolas, monospace;
      font-size: 0.75rem;
    }
    .file-list li {
      padding: 0.5rem;
      border-radius: 0.25rem;
      margin-bottom: 0.25rem;
      background: rgba(255,255,255,0.03);
    }
    .file-list li:hover {
      background: rgba(249, 115, 22, 0.1);
    }
  </style>
</head>
<body>
  <h2>Generated Files</h2>
  <ul class="file-list">
    ${files.map(f => `<li>${f.path}</li>`).join('\n')}
  </ul>
</body>
</html>
    `;
  }, [files]);

  const handleRefresh = () => {
    setIsLoading(true);
    setHasError(false);
    setRefreshKey(prev => prev + 1);
    
    // Simulate loading
    setTimeout(() => setIsLoading(false), 500);
  };

  const handleIframeLoad = () => {
    setIsLoading(false);
    setHasError(false);
  };

  const handleIframeError = () => {
    setIsLoading(false);
    setHasError(true);
  };

  // Get viewport dimensions
  const viewportSize = VIEWPORT_SIZES[viewport];

  // Calculate scale to fit container
  const containerWidth = isExpanded ? '100vw' : '100%';

  return (
    <div className={cn(
      "flex flex-col h-full bg-[#0A0A0F] rounded-lg overflow-hidden border border-zinc-800/50",
      isExpanded && "fixed inset-0 z-50",
      className
    )}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 bg-zinc-900/80 border-b border-zinc-800/50">
        <div className="flex items-center gap-1">
          {/* Viewport toggles */}
          {(['desktop', 'tablet', 'mobile'] as ViewportMode[]).map((mode) => {
            const Icon = mode === 'desktop' ? Monitor : mode === 'tablet' ? Tablet : Smartphone;
            const size = VIEWPORT_SIZES[mode];
            return (
              <button
                key={mode}
                onClick={() => setViewport(mode)}
                title={`${size.label} (${size.width}×${size.height})`}
                className={cn(
                  "p-1.5 rounded-md transition-colors",
                  viewport === mode 
                    ? "bg-orange-500/20 text-orange-400" 
                    : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800"
                )}
              >
                <Icon size={16} />
              </button>
            );
          })}
        </div>

        <div className="flex items-center gap-3">
          {/* Live indicator */}
          {showLivePreview && (
            <div className="flex items-center gap-2 text-xs text-emerald-400">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
              </span>
              <span>Live</span>
            </div>
          )}

          {/* Viewport info */}
          <span className="text-xs text-zinc-500">
            {viewportSize.width} × {viewportSize.height}
          </span>
        </div>

        <div className="flex items-center gap-1">
          {/* Refresh */}
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          </button>

          {/* Open in new tab */}
          {productionUrl && (
            <a
              href={productionUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
            >
              <ExternalLink size={16} />
            </a>
          )}

          {/* Expand/Collapse */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
          >
            {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
        </div>
      </div>

      {/* Preview Area */}
      <div className="flex-1 relative overflow-hidden bg-zinc-950 flex items-center justify-center">
        <AnimatePresence mode="wait">
          {/* Loading state */}
          {isLoading && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 z-10"
            >
              <LoadingPlaceholder />
            </motion.div>
          )}

          {/* Error state */}
          {hasError && !isLoading && (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0"
            >
              <ErrorPlaceholder message="Failed to load site preview" />
            </motion.div>
          )}

          {/* Coming Soon - no files, no URL */}
          {showComingSoon && !isLoading && !hasError && (
            <motion.div
              key="coming-soon"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0"
            >
              <ComingSoonPlaceholder />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Iframe container with viewport simulation */}
        {(showLivePreview || showLocalPreview) && !hasError && (
          <motion.div
            key={`viewport-${viewport}`}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2 }}
            className={cn(
              "bg-white rounded-lg overflow-hidden shadow-2xl transition-all duration-300",
              viewport === 'mobile' && "max-w-[375px]",
              viewport === 'tablet' && "max-w-[768px]",
              viewport === 'desktop' && "w-full"
            )}
            style={{
              width: viewport === 'desktop' ? '100%' : viewportSize.width,
              maxHeight: '100%',
              aspectRatio: viewport === 'desktop' 
                ? undefined 
                : `${viewportSize.width} / ${viewportSize.height}`
            }}
          >
            {showLivePreview ? (
              <iframe
                ref={iframeRef}
                key={`${productionUrl}-${refreshKey}`}
                src={productionUrl || undefined}
                className="w-full h-full border-0"
                onLoad={handleIframeLoad}
                onError={handleIframeError}
                sandbox="allow-scripts allow-same-origin"
              />
            ) : (
              <iframe
                ref={iframeRef}
                key={`local-${refreshKey}-${files.length}`}
                srcDoc={generateLocalPreview()}
                className="w-full h-full border-0"
                style={{ minHeight: 400 }}
              />
            )}
          </motion.div>
        )}

        {/* Viewport device frame (optional aesthetic) */}
        {viewport !== 'desktop' && (showLivePreview || showLocalPreview) && (
          <div className="absolute inset-0 pointer-events-none">
            <div className={cn(
              "absolute left-1/2 -translate-x-1/2 bottom-2",
              "w-24 h-1 bg-zinc-800 rounded-full opacity-30"
            )} />
          </div>
        )}
      </div>

      {/* Status bar */}
      <div className="px-3 py-1.5 bg-zinc-900/80 border-t border-zinc-800/50 flex items-center justify-between text-xs">
        <span className="text-zinc-500">
          {showLivePreview && (
            <span className="text-emerald-400">● </span>
          )}
          {productionUrl ? (
            <span className="text-zinc-400 truncate max-w-xs">
              {productionUrl.replace('https://', '')}
            </span>
          ) : showLocalPreview ? (
            <span className="text-amber-400">Local preview • {files.length} files</span>
          ) : (
            <span>Ready to build</span>
          )}
        </span>
        <span className="text-zinc-600">
          {VIEWPORT_SIZES[viewport].label}
        </span>
      </div>
    </div>
  );
}

export default LivePreview;
