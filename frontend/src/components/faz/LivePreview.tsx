'use client';

/**
 * LivePreview Component
 * 
 * Renders project files in an iframe with live updates.
 * Supports HTML/CSS/JS preview with hot reload on file changes.
 */

import { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Monitor,
  Smartphone,
  Tablet,
  RefreshCw,
  ExternalLink,
  Maximize2,
  Minimize2,
  Code2,
  Eye,
  Loader2
} from 'lucide-react';
import { useFazStore } from '@/lib/faz/store';
import type { FazFile } from '@/types/faz';

type ViewportSize = 'desktop' | 'tablet' | 'mobile';

const VIEWPORT_SIZES: Record<ViewportSize, { width: number; label: string }> = {
  desktop: { width: 1280, label: 'Desktop' },
  tablet: { width: 768, label: 'Tablet' },
  mobile: { width: 375, label: 'Mobile' },
};

interface LivePreviewProps {
  files?: FazFile[];
  initialFile?: string;
  className?: string;
}

export function LivePreview({ files: propFiles, initialFile, className = '' }: LivePreviewProps) {
  const { currentProject, files: storeFiles } = useFazStore();
  const iframeRef = useRef<HTMLIFrameElement>(null);
  
  const [viewport, setViewport] = useState<ViewportSize>('desktop');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showCode, setShowCode] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  
  // Use prop files or store files
  const files = propFiles || storeFiles;
  
  // Find the entry HTML file
  const entryFile = useMemo(() => {
    if (selectedFile) {
      return files.find(f => f.path === selectedFile);
    }
    // Priority: initialFile -> index.html -> page.tsx -> App.tsx -> first HTML
    const priorities = [
      initialFile,
      'index.html',
      'public/index.html',
      'src/index.html',
      'app/page.tsx',
      'src/app/page.tsx',
      'pages/index.tsx',
      'src/pages/index.tsx',
      'src/App.tsx',
      'App.tsx',
    ].filter(Boolean);
    
    for (const path of priorities) {
      const file = files.find(f => f.path === path || f.path.endsWith(`/${path}`));
      if (file) return file;
    }
    
    // Fallback to first HTML file
    return files.find(f => f.extension === 'html');
  }, [files, initialFile, selectedFile]);
  
  // Generate preview HTML
  const previewHTML = useMemo(() => {
    if (!entryFile) return null;
    
    // If it's an HTML file, inject CSS and JS
    if (entryFile.extension === 'html') {
      let html = entryFile.content;
      
      // Find CSS files and inject
      const cssFiles = files.filter(f => f.extension === 'css');
      const cssContent = cssFiles.map(f => f.content).join('\n');
      if (cssContent && !html.includes('<style')) {
        html = html.replace('</head>', `<style>\n${cssContent}\n</style>\n</head>`);
      }
      
      // Find JS files and inject
      const jsFiles = files.filter(f => f.extension === 'js' && !f.path.includes('.config'));
      const jsContent = jsFiles.map(f => f.content).join('\n');
      if (jsContent && !html.includes('<script src')) {
        html = html.replace('</body>', `<script>\n${jsContent}\n</script>\n</body>`);
      }
      
      return html;
    }
    
    // For React/TSX files, create a wrapper
    if (entryFile.extension === 'tsx' || entryFile.extension === 'jsx') {
      // Extract and display a simple preview message for now
      // Full React rendering would require a bundler
      return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>React Preview</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #e0e0e0;
    }
    .preview-container {
      text-align: center;
      padding: 3rem;
      max-width: 600px;
    }
    h1 { 
      font-size: 2rem; 
      margin-bottom: 1rem;
      background: linear-gradient(90deg, #ff6b6b, #ffd93d, #6bcb77);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }
    p { color: #a0a0a0; line-height: 1.6; margin-bottom: 1.5rem; }
    .code-box {
      background: #0d1117;
      border: 1px solid #30363d;
      border-radius: 8px;
      padding: 1rem;
      text-align: left;
      font-family: 'Fira Code', monospace;
      font-size: 0.85rem;
      color: #7ee787;
      overflow-x: auto;
    }
    .file-name { color: #79c0ff; margin-bottom: 0.5rem; }
  </style>
</head>
<body>
  <div class="preview-container">
    <h1>React Component Preview</h1>
    <p>This is a React/Next.js component. Full preview requires the development server to be running.</p>
    <div class="code-box">
      <div class="file-name">${entryFile.path}</div>
      <pre>${escapeHtml(entryFile.content.slice(0, 500))}${entryFile.content.length > 500 ? '\n...' : ''}</pre>
    </div>
  </div>
</body>
</html>
      `;
    }
    
    return null;
  }, [entryFile, files]);
  
  // Update iframe content
  const updatePreview = useCallback(() => {
    if (!iframeRef.current || !previewHTML) return;
    
    setIsLoading(true);
    
    const iframe = iframeRef.current;
    const doc = iframe.contentDocument || iframe.contentWindow?.document;
    
    if (doc) {
      doc.open();
      doc.write(previewHTML);
      doc.close();
    }
    
    setTimeout(() => setIsLoading(false), 300);
  }, [previewHTML]);
  
  // Update preview when content changes
  useEffect(() => {
    updatePreview();
  }, [updatePreview]);
  
  // File list for navigation
  const previewableFiles = useMemo(() => {
    return files.filter(f => 
      ['html', 'htm', 'tsx', 'jsx'].includes(f.extension || '')
    );
  }, [files]);
  
  if (!entryFile && files.length === 0) {
    return (
      <div className={`flex items-center justify-center h-full bg-zinc-900 ${className}`}>
        <div className="text-center text-zinc-500">
          <Eye className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No files to preview</p>
          <p className="text-sm mt-1">Generate some code first!</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className={`flex flex-col bg-zinc-900 rounded-lg overflow-hidden border border-zinc-700/50 ${className}`}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 bg-zinc-800/80 border-b border-zinc-700/50">
        <div className="flex items-center gap-2">
          {/* File selector */}
          <select
            value={selectedFile || entryFile?.path || ''}
            onChange={(e) => setSelectedFile(e.target.value)}
            className="bg-zinc-700 text-zinc-200 text-sm px-2 py-1 rounded border border-zinc-600 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {previewableFiles.map(f => (
              <option key={f.file_id} value={f.path}>
                {f.filename}
              </option>
            ))}
          </select>
        </div>
        
        <div className="flex items-center gap-1">
          {/* Viewport switcher */}
          {Object.entries(VIEWPORT_SIZES).map(([key, { label }]) => {
            const Icon = key === 'desktop' ? Monitor : key === 'tablet' ? Tablet : Smartphone;
            return (
              <button
                key={key}
                onClick={() => setViewport(key as ViewportSize)}
                className={`p-1.5 rounded transition-colors ${
                  viewport === key 
                    ? 'bg-blue-500/20 text-blue-400' 
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700'
                }`}
                title={label}
              >
                <Icon className="w-4 h-4" />
              </button>
            );
          })}
          
          <div className="w-px h-4 bg-zinc-600 mx-1" />
          
          {/* Actions */}
          <button
            onClick={updatePreview}
            className="p-1.5 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          
          <button
            onClick={() => setShowCode(!showCode)}
            className={`p-1.5 rounded transition-colors ${
              showCode 
                ? 'bg-purple-500/20 text-purple-400' 
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700'
            }`}
            title="View Source"
          >
            <Code2 className="w-4 h-4" />
          </button>
          
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 transition-colors"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          
          {currentProject?.preview_url && (
            <a
              href={currentProject.preview_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 rounded text-zinc-400 hover:text-zinc-200 hover:bg-zinc-700 transition-colors"
              title="Open in New Tab"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </div>
      </div>
      
      {/* Preview Area */}
      <div className="flex-1 relative bg-white overflow-hidden">
        {/* Loading overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-zinc-900/80 flex items-center justify-center z-10">
            <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
          </div>
        )}
        
        {/* Iframe container with viewport sizing */}
        <div 
          className="h-full flex items-start justify-center overflow-auto p-4 bg-zinc-800"
          style={{ backgroundColor: '#1e1e1e' }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ 
              opacity: 1, 
              scale: 1,
              width: isFullscreen ? '100%' : VIEWPORT_SIZES[viewport].width,
            }}
            transition={{ duration: 0.2 }}
            className="bg-white shadow-2xl rounded-lg overflow-hidden h-full"
            style={{ 
              minHeight: 500,
              maxWidth: '100%',
            }}
          >
            {showCode ? (
              <div className="h-full bg-zinc-900 overflow-auto">
                <pre className="p-4 text-sm text-zinc-300 font-mono">
                  {entryFile?.content}
                </pre>
              </div>
            ) : (
              <iframe
                ref={iframeRef}
                className="w-full h-full border-0"
                sandbox="allow-scripts allow-same-origin allow-forms"
                title="Preview"
              />
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

export default LivePreview;

