import React from 'react';
import { Eye } from 'lucide-react';
import { cn } from '@/lib/utils';

export type PreviewMode = 'mobile' | 'tablet' | 'desktop';

interface PreviewFrameProps {
  previewUrl?: string;
  previewHtml?: string | null;
  mode: PreviewMode;
}

/**
 * PreviewFrame Component
 * 
 * Displays a live preview or static HTML preview of a Faz Code project
 * with responsive device frame sizing.
 */
export function PreviewFrame({ previewUrl, previewHtml, mode }: PreviewFrameProps) {
  const widthMap: Record<PreviewMode, string> = {
    mobile: 'max-w-[375px]',
    tablet: 'max-w-[768px]',
    desktop: 'max-w-full'
  };

  return (
    <div className="h-full flex items-center justify-center bg-[#0A0A0F] p-4">
      <div className={cn("w-full h-full", widthMap[mode])}>
        {previewUrl ? (
          <iframe
            src={previewUrl}
            className="w-full h-full rounded-lg border border-[#1E1E2E]"
            title="Live Preview"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
          />
        ) : previewHtml ? (
          <iframe
            srcDoc={previewHtml}
            className="w-full h-full rounded-lg border border-[#1E1E2E]"
            title="Preview"
            sandbox="allow-scripts allow-same-origin"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center bg-[#12121A] rounded-lg border border-[#1E1E2E]">
            <div className="text-center">
              <Eye size={48} className="mx-auto text-[#64748B] mb-4" />
              <p className="text-[#94A3B8]">No preview available yet</p>
              <p className="text-sm text-[#64748B] mt-2">Run the pipeline to generate files</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

