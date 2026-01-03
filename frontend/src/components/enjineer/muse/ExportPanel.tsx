'use client';

/**
 * Muse Export Panel - Design Documentation Export
 * 
 * Provides interface for generating and downloading design documentation:
 * - Design Report: Full design story for stakeholders
 * - Cursor Prompt: Implementation brief for AI coding assistants
 * - Export Package: ZIP with all documentation and tokens
 */

import React, { useState, useCallback } from 'react';
import { 
  FileText, 
  Download, 
  Package, 
  Code2, 
  Loader2, 
  CheckCircle2,
  FileJson,
  Palette,
  Sparkles,
  ExternalLink
} from 'lucide-react';
import { museApi } from '@/lib/muse/api';
import type { GeneratedReport, CursorPromptResponse } from '@/lib/muse/api';

interface ExportPanelProps {
  sessionId: number;
  projectName?: string;
  onExportComplete?: (type: string) => void;
}

type ExportType = 'design_report' | 'cursor_prompt' | 'package_full' | 'package_cursor' | 'package_tokens';

interface ExportOption {
  id: ExportType;
  title: string;
  description: string;
  icon: React.ReactNode;
  tag?: string;
}

const EXPORT_OPTIONS: ExportOption[] = [
  {
    id: 'cursor_prompt',
    title: 'Cursor Prompt',
    description: 'Implementation brief optimized for AI coding assistants',
    icon: <Code2 className="w-5 h-5" />,
    tag: 'Recommended'
  },
  {
    id: 'design_report',
    title: 'Design Report',
    description: 'Full design story with rationale for stakeholders',
    icon: <FileText className="w-5 h-5" />,
  },
  {
    id: 'package_cursor',
    title: 'Cursor-Ready Package',
    description: 'ZIP with prompt, tokens, and config files',
    icon: <Package className="w-5 h-5" />,
  },
  {
    id: 'package_full',
    title: 'Full Package',
    description: 'Complete documentation, tokens, and Tailwind config',
    icon: <Sparkles className="w-5 h-5" />,
  },
  {
    id: 'package_tokens',
    title: 'Design Tokens Only',
    description: 'JSON and CSS tokens for existing projects',
    icon: <FileJson className="w-5 h-5" />,
  },
];

export function ExportPanel({ sessionId, projectName, onExportComplete }: ExportPanelProps) {
  const [activeExport, setActiveExport] = useState<ExportType | null>(null);
  const [completedExports, setCompletedExports] = useState<Set<ExportType>>(new Set());
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExport = useCallback(async (type: ExportType) => {
    setActiveExport(type);
    setError(null);
    setPreviewContent(null);

    try {
      switch (type) {
        case 'cursor_prompt': {
          const result = await museApi.getCursorPrompt(sessionId);
          setPreviewContent(result.content);
          await museApi.downloadCursorPrompt(sessionId);
          break;
        }
        case 'design_report': {
          const result = await museApi.generateDesignReport(sessionId, 'design_report');
          setPreviewContent(result.content_markdown);
          // Trigger download
          const blob = new Blob([result.content_markdown], { type: 'text/markdown' });
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'design-report.md';
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
          break;
        }
        case 'package_cursor':
          await museApi.downloadExportPackage(sessionId, 'cursor_ready');
          break;
        case 'package_full':
          await museApi.downloadExportPackage(sessionId, 'full');
          break;
        case 'package_tokens':
          await museApi.downloadExportPackage(sessionId, 'tokens_only');
          break;
      }

      setCompletedExports(prev => new Set([...Array.from(prev), type]));
      onExportComplete?.(type);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setActiveExport(null);
    }
  }, [sessionId, onExportComplete]);

  return (
    <div className="bg-white/50 dark:bg-zinc-900/50 backdrop-blur-sm rounded-2xl border border-zinc-200/50 dark:border-zinc-800/50 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-zinc-200/50 dark:border-zinc-800/50">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-violet-500/10 to-purple-500/10 rounded-xl">
            <Download className="w-5 h-5 text-violet-600 dark:text-violet-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">
              Export Design System
            </h3>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              {projectName ? `Documentation for ${projectName}` : 'Generate documentation and tokens'}
            </p>
          </div>
        </div>
      </div>

      {/* Export Options */}
      <div className="p-4 space-y-3">
        {EXPORT_OPTIONS.map((option) => {
          const isActive = activeExport === option.id;
          const isCompleted = completedExports.has(option.id);

          return (
            <button
              key={option.id}
              onClick={() => handleExport(option.id)}
              disabled={isActive}
              className={`
                w-full p-4 rounded-xl border transition-all duration-200
                flex items-start gap-4 text-left group
                ${isCompleted 
                  ? 'bg-emerald-50/50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800' 
                  : 'bg-white dark:bg-zinc-800/50 border-zinc-200 dark:border-zinc-700/50 hover:border-violet-300 dark:hover:border-violet-700 hover:shadow-md'
                }
                ${isActive ? 'opacity-80 cursor-wait' : 'cursor-pointer'}
              `}
            >
              {/* Icon */}
              <div className={`
                p-2.5 rounded-lg transition-colors
                ${isCompleted 
                  ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400' 
                  : 'bg-zinc-100 dark:bg-zinc-700/50 text-zinc-600 dark:text-zinc-400 group-hover:bg-violet-100 dark:group-hover:bg-violet-900/50 group-hover:text-violet-600 dark:group-hover:text-violet-400'
                }
              `}>
                {isActive ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : isCompleted ? (
                  <CheckCircle2 className="w-5 h-5" />
                ) : (
                  option.icon
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-zinc-900 dark:text-zinc-100">
                    {option.title}
                  </span>
                  {option.tag && (
                    <span className="px-2 py-0.5 text-xs font-medium bg-violet-100 dark:bg-violet-900/50 text-violet-700 dark:text-violet-300 rounded-full">
                      {option.tag}
                    </span>
                  )}
                </div>
                <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-0.5">
                  {option.description}
                </p>
              </div>

              {/* Download indicator */}
              <div className={`
                p-2 rounded-lg transition-opacity
                ${isActive || isCompleted ? 'opacity-0' : 'opacity-0 group-hover:opacity-100'}
              `}>
                <Download className="w-4 h-4 text-zinc-400" />
              </div>
            </button>
          );
        })}
      </div>

      {/* Error Message */}
      {error && (
        <div className="mx-4 mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Preview Panel */}
      {previewContent && (
        <div className="border-t border-zinc-200/50 dark:border-zinc-800/50">
          <div className="px-6 py-3 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-800/30">
            <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
              Preview
            </span>
            <button
              onClick={() => setPreviewContent(null)}
              className="text-xs text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
            >
              Close
            </button>
          </div>
          <div className="p-4 max-h-64 overflow-y-auto">
            <pre className="text-xs text-zinc-600 dark:text-zinc-400 whitespace-pre-wrap font-mono">
              {previewContent.slice(0, 1500)}
              {previewContent.length > 1500 && '...\n\n[Content truncated for preview]'}
            </pre>
          </div>
        </div>
      )}

      {/* Quick Actions Footer */}
      <div className="px-6 py-4 border-t border-zinc-200/50 dark:border-zinc-800/50 bg-zinc-50/50 dark:bg-zinc-800/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
            <Palette className="w-4 h-4" />
            <span>Design tokens ready for implementation</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport('cursor_prompt')}
              disabled={activeExport !== null}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {activeExport === 'cursor_prompt' ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Code2 className="w-3.5 h-3.5" />
              )}
              Get Cursor Prompt
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ExportPanel;

