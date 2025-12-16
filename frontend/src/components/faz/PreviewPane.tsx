import React from 'react';
import { Monitor, Smartphone, Tablet, ExternalLink, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useFazStore } from '@/lib/faz/store';

interface PreviewPaneProps {
  url?: string;
  className?: string;
}

export function PreviewPane({ url, className }: PreviewPaneProps) {
  const { previewMode, setPreviewMode } = useFazStore();
  const [key, setKey] = React.useState(0); // For refresh

  const refresh = () => setKey(prev => prev + 1);

  const getWidth = () => {
    switch (previewMode) {
      case 'mobile': return 'max-w-[375px]';
      case 'tablet': return 'max-w-[768px]';
      default: return 'w-full';
    }
  };

  return (
    <div className={cn("flex flex-col h-full bg-[#0A0A0F]", className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[#1E1E2E] bg-[#12121A]">
        <div className="flex items-center gap-1 bg-[#0A0A0F] p-1 rounded-md border border-[#1E1E2E]">
          <button
            onClick={() => setPreviewMode('mobile')}
            className={cn(
              "p-1.5 rounded transition-colors",
              previewMode === 'mobile' ? "bg-[#1E1E2E] text-white" : "text-[#64748B] hover:text-[#94A3B8]"
            )}
            title="Mobile view"
          >
            <Smartphone size={16} />
          </button>
          <button
            onClick={() => setPreviewMode('tablet')}
            className={cn(
              "p-1.5 rounded transition-colors",
              previewMode === 'tablet' ? "bg-[#1E1E2E] text-white" : "text-[#64748B] hover:text-[#94A3B8]"
            )}
            title="Tablet view"
          >
            <Tablet size={16} />
          </button>
          <button
            onClick={() => setPreviewMode('desktop')}
            className={cn(
              "p-1.5 rounded transition-colors",
              previewMode === 'desktop' ? "bg-[#1E1E2E] text-white" : "text-[#64748B] hover:text-[#94A3B8]"
            )}
            title="Desktop view"
          >
            <Monitor size={16} />
          </button>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-[#64748B] font-mono truncate max-w-[200px]">
            {url || 'Waiting for deployment...'}
          </span>
          <button 
            onClick={refresh}
            className="p-1.5 text-[#64748B] hover:text-white transition-colors"
            title="Refresh preview"
          >
            <RefreshCw size={14} />
          </button>
          {url && (
            <a 
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 text-[#64748B] hover:text-[#6366F1] transition-colors"
              title="Open in new tab"
            >
              <ExternalLink size={14} />
            </a>
          )}
        </div>
      </div>

      {/* Preview Area */}
      <div className="flex-1 bg-[#0A0A0F] p-4 flex items-center justify-center overflow-hidden relative bg-[radial-gradient(#1E1E2E_1px,transparent_1px)] [background-size:16px_16px]">
        {url ? (
          <div className={cn(
            "bg-white shadow-2xl transition-all duration-300 ease-in-out h-full overflow-hidden border border-[#1E1E2E]",
            getWidth(),
            previewMode !== 'desktop' && "rounded-2xl border-4 border-[#1E1E2E] h-[90%]"
          )}>
            <iframe
              key={key}
              src={url}
              className="w-full h-full border-0 bg-white"
              title="Preview"
              sandbox="allow-scripts allow-same-origin allow-forms"
            />
          </div>
        ) : (
          <div className="text-center text-[#64748B]">
            <div className="w-16 h-16 bg-[#12121A] rounded-full flex items-center justify-center mx-auto mb-4 border border-[#1E1E2E]">
              <Monitor className="text-[#1E1E2E]" size={32} />
            </div>
            <p>Preview will appear here once deployed</p>
          </div>
        )}
      </div>
    </div>
  );
}

