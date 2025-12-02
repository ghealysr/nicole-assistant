'use client';

/**
 * Nicole's Sequential Thinking UI Components
 * 
 * Implements Claude-style thinking visualization with Nicole's color palette.
 * 
 * Components:
 * - ThinkingBox: Collapsible steps with complete/running/pending states
 * - FileCard: Download card with copy button + gradient download button
 * - StyledTable: Lavender headers, hover states, italic examples
 * - FileLink: Inline link with external icon
 * - NoteCard: Teal suggestion/note boxes
 * 
 * Color Scheme:
 * - Lavender #B8A8D4 → headers, accents, running states
 * - Teal #BCD1CB → complete states, note cards
 * - Cream #F5F4ED → background
 * - Gradient buttons blend both
 */

import React, { useState } from 'react';

// Nicole's color palette
export const nicoleColors = {
  lavender: '#B8A8D4',
  lavenderLight: '#E8E0F0',
  lavenderDark: '#9B8AB8',
  teal: '#BCD1CB',
  tealDark: '#7A9B93',
  tealLight: '#E5EFEC',
  cream: '#F5F4ED',
  textPrimary: '#1d1d1f',
  textSecondary: '#6e6e73',
  textTertiary: '#9e9b8f',
  border: '#d8d7cc',
  white: '#FFFFFF',
};

// ============================================================================
// ICONS
// ============================================================================

const CheckIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" strokeWidth={3} viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
  </svg>
);

const SpinnerIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

const ChevronDownIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
  </svg>
);

const ChevronRightIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
  </svg>
);

const SparklesIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24">
    <path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
  </svg>
);

const CopyIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>
);

const DownloadIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
  </svg>
);

const ExternalLinkIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
  </svg>
);

const FileCodeIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
  </svg>
);

const FileTextIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
);

const ClockIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const LightbulbIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
  </svg>
);

// ============================================================================
// STEP ICON COMPONENT
// ============================================================================

export type StepStatus = 'complete' | 'running' | 'pending';

interface StepIconProps {
  status: StepStatus;
}

export const StepIcon: React.FC<StepIconProps> = ({ status }) => {
  if (status === 'complete') {
    return (
      <div className="w-5 h-5 rounded-full flex items-center justify-center"
        style={{ background: 'linear-gradient(135deg, #2dd4bf 0%, #10b981 100%)' }}>
        <CheckIcon className="w-3 h-3 text-white" />
      </div>
    );
  }
  
  if (status === 'running') {
    return (
      <div className="w-5 h-5 rounded-full flex items-center justify-center animate-pulse"
        style={{ background: 'linear-gradient(135deg, #c084fc 0%, #8b5cf6 100%)' }}>
        <SpinnerIcon className="w-3 h-3 text-white animate-spin" />
      </div>
    );
  }
  
  // pending
  return (
    <div className="w-5 h-5 rounded-full border-2 border-gray-300 bg-white" />
  );
};

// ============================================================================
// THINKING BOX COMPONENT
// ============================================================================

export interface ThinkingStep {
  description: string;
  status: StepStatus;
  file?: string;
}

interface ThinkingBoxProps {
  steps: ThinkingStep[];
  summary?: string;
  defaultExpanded?: boolean;
}

export const ThinkingBox: React.FC<ThinkingBoxProps> = ({ 
  steps, 
  summary,
  defaultExpanded = false 
}) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  
  const completedSteps = steps.filter(s => s.status === 'complete').length;
  const totalSteps = steps.length;
  const isComplete = completedSteps === totalSteps && !steps.some(s => s.status === 'running');
  
  return (
    <div 
      className="rounded-xl border overflow-hidden transition-all duration-300 my-4"
      style={{ 
        borderColor: isComplete ? nicoleColors.teal : nicoleColors.lavender,
        backgroundColor: nicoleColors.white,
        boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
      }}
    >
      {/* Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 transition-colors"
      >
        <div 
          className="w-6 h-6 rounded-lg flex items-center justify-center transition-transform duration-200"
          style={{ 
            backgroundColor: isComplete ? nicoleColors.tealLight : nicoleColors.lavenderLight,
            transform: isExpanded ? 'rotate(0deg)' : 'rotate(-90deg)'
          }}
        >
          <ChevronDownIcon 
            className="w-4 h-4" 
            style={{ color: isComplete ? nicoleColors.tealDark : nicoleColors.lavenderDark }} 
          />
        </div>
        
        <span className="text-sm font-medium" style={{ color: nicoleColors.textSecondary }}>
          {completedSteps} {completedSteps === 1 ? 'step' : 'steps'}
        </span>
        
        {isComplete && (
          <SparklesIcon className="w-4 h-4 ml-auto" style={{ color: nicoleColors.lavender }} />
        )}
        
        {!isComplete && steps.some(s => s.status === 'running') && (
          <SpinnerIcon className="w-4 h-4 ml-auto animate-spin" style={{ color: nicoleColors.lavender }} />
        )}
      </button>
      
      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-3">
          {steps.map((step, index) => (
            <div key={index} className="flex items-start gap-3">
              <div className="mt-0.5">
                <StepIcon status={step.status} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm" style={{ color: nicoleColors.textPrimary }}>
                  {step.description}
                </p>
                {step.file && (
                  <span 
                    className="text-xs px-2 py-0.5 rounded-full mt-1 inline-block"
                    style={{ backgroundColor: nicoleColors.lavenderLight, color: nicoleColors.lavenderDark }}
                  >
                    {step.file}
                  </span>
                )}
              </div>
            </div>
          ))}
          
          {/* Summary line */}
          {summary && (
            <div 
              className="mt-3 pt-3 border-t text-sm"
              style={{ borderColor: nicoleColors.border, color: nicoleColors.textSecondary }}
            >
              {summary}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// ============================================================================
// FILE CARD COMPONENT
// ============================================================================

type FileIconType = 'code' | 'text' | 'generic';

interface FileCardProps {
  filename: string;
  fileType: string;
  iconType?: FileIconType;
  onDownload?: () => void;
  onCopy?: () => void;
  content?: string;
}

export const FileCard: React.FC<FileCardProps> = ({ 
  filename, 
  fileType, 
  iconType = 'code',
  onDownload,
  onCopy,
  content
}) => {
  const [copied, setCopied] = useState(false);
  
  const handleCopy = async () => {
    if (content) {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      onCopy?.();
    }
  };
  
  const handleDownload = () => {
    if (content) {
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
    onDownload?.();
  };
  
  const IconComponent = iconType === 'code' ? FileCodeIcon : FileTextIcon;
  
  return (
    <div 
      className="rounded-xl border p-4 flex items-center gap-4 transition-all hover:shadow-md my-4"
      style={{ 
        borderColor: nicoleColors.border,
        backgroundColor: nicoleColors.white,
      }}
    >
      {/* Icon */}
      <div 
        className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
        style={{ 
          background: `linear-gradient(135deg, ${nicoleColors.lavenderLight} 0%, ${nicoleColors.tealLight} 100%)`,
        }}
      >
        <IconComponent className="w-6 h-6" style={{ color: nicoleColors.lavenderDark }} />
      </div>
      
      {/* File Info */}
      <div className="flex-1 min-w-0">
        <p className="font-medium truncate" style={{ color: nicoleColors.textPrimary }}>
          {filename}
        </p>
        <p className="text-xs" style={{ color: nicoleColors.textTertiary }}>
          Code: {fileType}
        </p>
      </div>
      
      {/* Actions */}
      <div className="flex items-center gap-2">
        {content && (
          <button
            onClick={handleCopy}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            title="Copy contents"
          >
            {copied ? (
              <CheckIcon className="w-4 h-4" style={{ color: nicoleColors.tealDark }} />
            ) : (
              <CopyIcon className="w-4 h-4" style={{ color: nicoleColors.textTertiary }} />
            )}
          </button>
        )}
        <button
          onClick={handleDownload}
          className="px-4 py-2 rounded-lg text-sm font-medium transition-all hover:shadow-md text-white"
          style={{ 
            background: `linear-gradient(135deg, ${nicoleColors.lavender} 0%, ${nicoleColors.teal} 100%)`,
          }}
        >
          Download
        </button>
      </div>
    </div>
  );
};

// ============================================================================
// STYLED TABLE COMPONENT
// ============================================================================

interface TableColumn<T> {
  header: string;
  key: keyof T;
  render?: (value: T[keyof T], row: T) => React.ReactNode;
}

interface StyledTableProps<T> {
  data: T[];
  columns: TableColumn<T>[];
}

export function StyledTable<T extends Record<string, unknown>>({ 
  data, 
  columns 
}: StyledTableProps<T>) {
  return (
    <div 
      className="rounded-xl border overflow-hidden my-4"
      style={{ borderColor: nicoleColors.border }}
    >
      <table className="w-full">
        <thead>
          <tr style={{ backgroundColor: nicoleColors.lavenderLight }}>
            {columns.map((col, i) => (
              <th 
                key={i}
                className="px-4 py-3 text-left text-sm font-semibold"
                style={{ color: nicoleColors.lavenderDark }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr 
              key={rowIndex}
              className="border-t transition-colors hover:bg-gray-50"
              style={{ borderColor: nicoleColors.border }}
            >
              {columns.map((col, colIndex) => (
                <td 
                  key={colIndex}
                  className="px-4 py-3 text-sm"
                  style={{ 
                    color: colIndex === 0 ? nicoleColors.textPrimary : nicoleColors.textSecondary,
                    fontWeight: colIndex === 0 ? 500 : 400,
                  }}
                >
                  {col.render 
                    ? col.render(row[col.key], row) 
                    : String(row[col.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================================
// FILE LINK COMPONENT
// ============================================================================

interface FileLinkProps {
  href: string;
  children: React.ReactNode;
}

export const FileLink: React.FC<FileLinkProps> = ({ href, children }) => (
  <a 
    href={href}
    target="_blank"
    rel="noopener noreferrer"
    className="inline-flex items-center gap-1.5 text-sm hover:underline"
    style={{ color: nicoleColors.lavenderDark }}
  >
    {children}
    <ExternalLinkIcon className="w-3 h-3" />
  </a>
);

// ============================================================================
// NOTE CARD COMPONENT
// ============================================================================

type NoteIconType = 'clock' | 'lightbulb' | 'info';

interface NoteCardProps {
  children: React.ReactNode;
  iconType?: NoteIconType;
  title?: string;
}

export const NoteCard: React.FC<NoteCardProps> = ({ 
  children, 
  iconType = 'lightbulb',
  title 
}) => {
  const IconComponent = iconType === 'clock' ? ClockIcon : LightbulbIcon;
  
  return (
    <div 
      className="rounded-xl p-4 flex items-start gap-3 my-4"
      style={{ 
        backgroundColor: nicoleColors.tealLight,
        border: `1px solid ${nicoleColors.teal}`,
      }}
    >
      <div 
        className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
        style={{ backgroundColor: nicoleColors.teal }}
      >
        <IconComponent className="w-4 h-4 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        {title && (
          <p className="font-medium text-sm mb-1" style={{ color: nicoleColors.tealDark }}>
            {title}
          </p>
        )}
        <div className="text-sm" style={{ color: nicoleColors.tealDark }}>
          {children}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// STYLED LIST COMPONENTS
// ============================================================================

interface StyledListProps {
  children: React.ReactNode;
  ordered?: boolean;
}

export const StyledList: React.FC<StyledListProps> = ({ children, ordered = false }) => {
  const Tag = ordered ? 'ol' : 'ul';
  
  return (
    <Tag 
      className={`my-3 pl-5 space-y-1.5 ${ordered ? 'list-decimal' : 'list-disc'}`}
      style={{ color: nicoleColors.textPrimary }}
    >
      {children}
    </Tag>
  );
};

interface StyledListItemProps {
  children: React.ReactNode;
}

export const StyledListItem: React.FC<StyledListItemProps> = ({ children }) => (
  <li 
    className="text-sm leading-relaxed"
    style={{ color: nicoleColors.textPrimary }}
  >
    {children}
  </li>
);

// ============================================================================
// FILE BADGE COMPONENT (for inline file references)
// ============================================================================

interface FileBadgeProps {
  filename: string;
}

export const FileBadge: React.FC<FileBadgeProps> = ({ filename }) => (
  <span 
    className="text-xs px-2 py-0.5 rounded-full inline-block"
    style={{ backgroundColor: nicoleColors.lavenderLight, color: nicoleColors.lavenderDark }}
  >
    {filename}
  </span>
);

// ============================================================================
// GRADIENT BUTTON COMPONENT
// ============================================================================

interface GradientButtonProps {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
}

export const GradientButton: React.FC<GradientButtonProps> = ({ 
  children, 
  onClick,
  className = ''
}) => (
  <button
    onClick={onClick}
    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all hover:shadow-md text-white ${className}`}
    style={{ 
      background: `linear-gradient(135deg, ${nicoleColors.lavender} 0%, ${nicoleColors.teal} 100%)`,
    }}
  >
    {children}
  </button>
);

// ============================================================================
// EXPORT ALL
// ============================================================================

export {
  nicoleColors as colors,
  CheckIcon,
  SpinnerIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  SparklesIcon,
  CopyIcon,
  DownloadIcon,
  ExternalLinkIcon,
  FileCodeIcon,
  FileTextIcon,
  ClockIcon,
  LightbulbIcon,
};

