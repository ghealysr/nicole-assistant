'use client';

import React, { useState, useEffect, useRef, memo } from 'react';

// Color palette matching the app aesthetic
const colors = {
  lavender: '#B8A8D4',
  lavenderLight: '#F8F6FB',
  lavenderMid: '#E8E0F0',
  lavenderDark: '#9B8AB8',
  textPrimary: '#374151',
  textSecondary: '#6b7280',
  textMuted: '#9ca3af',
  white: '#FFFFFF',
  sage: '#7A9B93',
  sageLight: '#E8F0ED',
} as const;

// Animated thinking dots
const ThinkingDots = memo(function ThinkingDots() {
  return (
    <span className="inline-flex items-center gap-0.5 ml-1">
      {[0, 1, 2].map((i) => (
        <span 
          key={i}
          className="w-1 h-1 rounded-full animate-pulse"
          style={{ 
            backgroundColor: colors.lavender,
            animationDelay: `${i * 200}ms`,
          }}
        />
      ))}
    </span>
  );
});

// Tool use indicator with icon
interface ToolIndicatorProps {
  toolName: string;
  isActive: boolean;
  result?: string;
  success?: boolean;
}

const ToolIndicator = memo(function ToolIndicator({ toolName, isActive, result, success }: ToolIndicatorProps) {
  const getToolIcon = (name: string) => {
    const lowerName = name.toLowerCase();
    if (lowerName.includes('memory')) return '🧠';
    if (lowerName.includes('document')) return '📄';
    if (lowerName.includes('search') || lowerName.includes('brave')) return '🔍';
    if (lowerName.includes('notion')) return '📝';
    if (lowerName.includes('image') || lowerName.includes('recraft')) return '🎨';
    if (lowerName.includes('file')) return '📁';
    if (lowerName.includes('think')) return '💭';
    if (lowerName.includes('skill')) return '⚡';
    return '🔧';
  };

  const getToolDisplayName = (name: string) => {
    const displayMap: Record<string, string> = {
      'memory_search': 'Searching memories',
      'memory_store': 'Saving to memory',
      'document_search': 'Searching documents',
      'bravewebsearch': 'Web search',
      'brave_web_search': 'Web search',
      'think': 'Reasoning',
      'notion_search': 'Searching Notion',
      'recraftgenerateimage': 'Generating image',
      'skills_library': 'Checking skills',
      'dashboard_status': 'System status',
      'mcp_status': 'MCP status',
    };
    return displayMap[name.toLowerCase()] || name.replace(/_/g, ' ');
  };

  return (
    <div 
      className={`
        flex items-center gap-2 px-3 py-1.5 rounded-md text-sm
        transition-all duration-200
        ${isActive ? 'animate-pulse' : ''}
      `}
      style={{
        backgroundColor: isActive ? colors.lavenderMid : (success === false ? '#FEE2E2' : colors.sageLight),
        border: `1px solid ${isActive ? colors.lavender : (success === false ? '#FECACA' : colors.sage)}`,
      }}
    >
      <span>{getToolIcon(toolName)}</span>
      <span style={{ color: colors.textPrimary }}>
        {getToolDisplayName(toolName)}
      </span>
      {isActive && <ThinkingDots />}
      {!isActive && success !== false && (
        <span className="text-xs" style={{ color: colors.sage }}>✓</span>
      )}
      {!isActive && success === false && (
        <span className="text-xs text-red-500">✗</span>
      )}
    </div>
  );
});

export interface ToolUse {
  id: string;
  name: string;
  isActive: boolean;
  result?: string;
  success?: boolean;
}

export interface ThinkingBlockProps {
  /** Whether we're currently receiving thinking content */
  isThinking: boolean;
  /** The accumulated thinking content */
  content: string;
  /** Duration in seconds (set when thinking completes) */
  duration?: number;
  /** Whether thinking has completed */
  isComplete: boolean;
  /** Active and completed tool uses */
  toolUses?: ToolUse[];
}

export function NicoleThinkingBlock({ 
  isThinking, 
  content, 
  duration,
  isComplete,
  toolUses = [],
}: ThinkingBlockProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll thinking content as it streams
  useEffect(() => {
    if (contentRef.current && !isCollapsed) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [content, isCollapsed]);
  
  // Fade in when content starts
  useEffect(() => {
    if (content.length > 0 || isThinking || toolUses.length > 0) {
      setIsVisible(true);
    }
  }, [content, isThinking, toolUses.length]);
  
  if (!isVisible && !isThinking && toolUses.length === 0) {
    return null;
  }
  
  const hasContent = content.length > 0;
  const hasToolUses = toolUses.length > 0;
  const activeToolUse = toolUses.find(t => t.isActive);
  
  // Calculate header text
  const getHeaderText = () => {
    if (activeToolUse) {
      return 'Working';
    }
    if (isThinking) {
      return 'Thinking';
    }
    if (isComplete) {
      return 'Thought process';
    }
    return 'Processing';
  };
  
  return (
    <div 
      className={`
        rounded-xl overflow-hidden transition-all duration-300 ease-out
        ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}
      `}
      style={{
        backgroundColor: colors.lavenderLight,
        border: `1px solid ${colors.lavenderMid}`,
        boxShadow: '0 2px 12px rgba(184, 168, 212, 0.2)',
      }}
    >
      {/* Header - Claude style */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-opacity-50 transition-colors"
        style={{ backgroundColor: isCollapsed ? colors.lavenderMid : 'transparent' }}
      >
        <div className="flex items-center gap-3">
          {/* Animated sparkle icon */}
          <div 
            className={`
              w-6 h-6 rounded-full flex items-center justify-center
              ${isThinking || activeToolUse ? 'animate-pulse' : ''}
            `}
            style={{ backgroundColor: colors.lavender }}
          >
            <span className="text-white text-xs">
              {isComplete ? '💭' : '✨'}
            </span>
          </div>
          
          {/* Label */}
          <span 
            className="text-sm font-medium"
            style={{ color: colors.textPrimary }}
          >
            {getHeaderText()}
            {(isThinking || activeToolUse) && <ThinkingDots />}
          </span>
          
          {/* Duration badge */}
          {isComplete && duration && (
            <span 
              className="text-xs px-2 py-0.5 rounded-full"
              style={{ 
                backgroundColor: colors.lavenderMid,
                color: colors.textSecondary 
              }}
            >
              {duration.toFixed(1)}s
            </span>
          )}
          
          {/* Tool count badge */}
          {hasToolUses && (
            <span 
              className="text-xs px-2 py-0.5 rounded-full"
              style={{ 
                backgroundColor: colors.sageLight,
                color: colors.sage 
              }}
            >
              {toolUses.length} tool{toolUses.length !== 1 ? 's' : ''} used
            </span>
          )}
        </div>
        
        {/* Collapse toggle */}
        <svg 
          className={`w-4 h-4 transition-transform duration-200 ${isCollapsed ? '-rotate-90' : ''}`}
          fill="none" 
          viewBox="0 0 24 24" 
          stroke={colors.textSecondary}
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {/* Content - collapsible */}
      <div 
        className={`
          transition-all duration-300 ease-out overflow-hidden
          ${isCollapsed ? 'max-h-0' : 'max-h-[500px]'}
        `}
      >
        {/* Tool uses section */}
        {hasToolUses && (
          <div 
            className="px-4 py-2 flex flex-wrap gap-2"
            style={{ borderTop: `1px solid ${colors.lavenderMid}` }}
          >
            {toolUses.map((tool) => (
              <ToolIndicator 
                key={tool.id}
                toolName={tool.name}
                isActive={tool.isActive}
                result={tool.result}
                success={tool.success}
              />
            ))}
          </div>
        )}
        
        {/* Thinking content */}
        {hasContent && (
          <div 
            ref={contentRef}
            className="px-4 pb-4 overflow-y-auto"
            style={{ 
              maxHeight: '350px',
              borderTop: hasToolUses ? `1px solid ${colors.lavenderMid}` : 'none',
            }}
          >
            <pre 
              className="whitespace-pre-wrap break-words font-mono text-sm leading-relaxed pt-3"
              style={{ color: colors.textSecondary }}
            >
              {content}
              {!isComplete && (
                <span 
                  className="inline-block w-2 h-4 ml-0.5 animate-pulse"
                  style={{ backgroundColor: colors.lavender }}
                />
              )}
            </pre>
          </div>
        )}
        
        {/* Empty state when only tools are shown */}
        {!hasContent && hasToolUses && !isThinking && (
          <div 
            className="px-4 pb-3 text-sm"
            style={{ color: colors.textMuted }}
          >
            Nicole used {toolUses.length} tool{toolUses.length !== 1 ? 's' : ''} to help with this response.
          </div>
        )}
      </div>
    </div>
  );
}

export default NicoleThinkingBlock;
