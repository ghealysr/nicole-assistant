'use client';

import React, { useState, useEffect, useRef, memo } from 'react';
import { NicoleOrbAnimation } from './NicoleOrbAnimation';

// Subtle color palette - blends with tan background
const colors = {
  // Main background is #F5F4ED (tan)
  bgThinking: '#EFEDE5',      // Slightly darker tan for thinking box
  borderLight: 'rgba(184, 168, 212, 0.3)', // Very light purple stroke
  borderActive: 'rgba(184, 168, 212, 0.5)', // Slightly more visible when active
  textPrimary: '#4b5563',
  textSecondary: '#6b7280',
  textMuted: '#9ca3af',
  lavender: '#B8A8D4',
  lavenderLight: 'rgba(184, 168, 212, 0.15)',
  sage: '#7A9B93',
  sageLight: 'rgba(122, 155, 147, 0.15)',
} as const;

// Animated thinking dots - subtle
const ThinkingDots = memo(function ThinkingDots() {
  return (
    <span className="inline-flex items-center gap-0.5 ml-1">
      {[0, 1, 2].map((i) => (
        <span 
          key={i}
          className="w-1 h-1 rounded-full animate-pulse"
          style={{ 
            backgroundColor: colors.lavender,
            opacity: 0.6,
            animationDelay: `${i * 200}ms`,
          }}
        />
      ))}
    </span>
  );
});

// Tool use indicator - minimal style
interface ToolIndicatorProps {
  toolName: string;
  isActive: boolean;
  success?: boolean;
}

const ToolIndicator = memo(function ToolIndicator({ toolName, isActive, success }: ToolIndicatorProps) {
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
      'search_tools': 'Finding tools',
      'dashboard_status': 'System status',
      'mcp_status': 'MCP status',
    };
    return displayMap[name.toLowerCase()] || name.replace(/_/g, ' ');
  };

  return (
    <div 
      className={`
        inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs
        transition-all duration-200
      `}
      style={{
        backgroundColor: isActive ? colors.lavenderLight : (success === false ? 'rgba(239, 68, 68, 0.1)' : colors.sageLight),
        border: `1px solid ${isActive ? colors.borderActive : (success === false ? 'rgba(239, 68, 68, 0.3)' : 'rgba(122, 155, 147, 0.3)')}`,
        color: colors.textSecondary,
      }}
    >
      <span className="text-xs">{getToolIcon(toolName)}</span>
      <span>{getToolDisplayName(toolName)}</span>
      {isActive && <ThinkingDots />}
      {!isActive && success !== false && (
        <span style={{ color: colors.sage }}>✓</span>
      )}
      {!isActive && success === false && (
        <span className="text-red-400">✗</span>
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
  /** Whether streaming is active (spinner should spin) */
  isStreaming?: boolean;
}

export function NicoleThinkingBlock({ 
  isThinking, 
  content, 
  duration,
  isComplete,
  toolUses = [],
  isStreaming = false,
}: ThinkingBlockProps) {
  // Auto-collapse when thinking completes
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const wasCompleteRef = useRef(false);
  
  // Auto-scroll thinking content as it streams
  useEffect(() => {
    if (contentRef.current && !isCollapsed) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [content, isCollapsed]);
  
  // Fade in smoothly when component mounts or becomes active
  useEffect(() => {
    // Small delay for smooth animation
    const timer = setTimeout(() => {
      setIsVisible(true);
    }, 50);
    return () => clearTimeout(timer);
  }, []);
  
  // Auto-collapse when thinking completes (Claude behavior)
  useEffect(() => {
    if (isComplete && !wasCompleteRef.current && content.length > 0) {
      // Delay collapse slightly so user sees it's done
      const timer = setTimeout(() => {
        setIsCollapsed(true);
      }, 600);
      wasCompleteRef.current = true;
      return () => clearTimeout(timer);
    }
  }, [isComplete, content.length]);
  
  const hasContent = content.length > 0;
  const hasToolUses = toolUses.length > 0;
  const activeToolUse = toolUses.find(t => t.isActive);
  
  // Determine if spinner should be active
  const shouldSpin = isStreaming || isThinking || !!activeToolUse;
  
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
        rounded-lg overflow-hidden
        transition-all duration-300 ease-out
        ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}
      `}
      style={{
        backgroundColor: colors.bgThinking,
        border: `1px solid ${shouldSpin ? colors.borderActive : colors.borderLight}`,
      }}
    >
      {/* Header - Claude style with Nicole's avatar */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-black/[0.02] transition-colors"
      >
        <div className="flex items-center gap-2.5">
          {/* Nicole's orb animation - glowing while processing */}
          <NicoleOrbAnimation 
            isActive={shouldSpin}
            size="small"
            variant="single"
            showParticles={false}
          />
          
          {/* Label */}
          <span 
            className="text-xs font-medium"
            style={{ color: colors.textSecondary }}
          >
            {getHeaderText()}
            {shouldSpin && <ThinkingDots />}
          </span>
          
          {/* Duration badge - subtle */}
          {isComplete && duration && duration > 0 && (
            <span 
              className="text-[10px] px-1.5 py-0.5 rounded"
              style={{ 
                backgroundColor: colors.lavenderLight,
                color: colors.textMuted,
              }}
            >
              {duration.toFixed(1)}s
            </span>
          )}
          
          {/* Tool count badge - subtle */}
          {hasToolUses && (
            <span 
              className="text-[10px] px-1.5 py-0.5 rounded"
              style={{ 
                backgroundColor: colors.sageLight,
                color: colors.textMuted,
              }}
            >
              {toolUses.length} tool{toolUses.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        
        {/* Collapse toggle */}
        <svg 
          className={`w-3.5 h-3.5 transition-transform duration-200 ${isCollapsed ? '-rotate-90' : ''}`}
          fill="none" 
          viewBox="0 0 24 24" 
          stroke={colors.textMuted}
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {/* Content - collapsible */}
      <div 
        className={`
          transition-all duration-300 ease-out overflow-hidden
          ${isCollapsed ? 'max-h-0' : 'max-h-[400px]'}
        `}
      >
        {/* Tool uses section */}
        {hasToolUses && (
          <div 
            className="px-3 py-2 flex flex-wrap gap-1.5"
            style={{ borderTop: `1px solid ${colors.borderLight}` }}
          >
            {toolUses.map((tool) => (
              <ToolIndicator 
                key={tool.id}
                toolName={tool.name}
                isActive={tool.isActive}
                success={tool.success}
              />
            ))}
          </div>
        )}
        
        {/* Thinking content - streams fast */}
        {hasContent && (
          <div 
            ref={contentRef}
            className="px-3 pb-3 overflow-y-auto"
            style={{ 
              maxHeight: '300px',
              borderTop: hasToolUses ? `1px solid ${colors.borderLight}` : 'none',
            }}
          >
            <pre 
              className="whitespace-pre-wrap break-words font-mono text-xs leading-relaxed pt-2"
              style={{ color: colors.textMuted }}
            >
              {content}
              {!isComplete && (
                <span 
                  className="inline-block w-1.5 h-3 ml-0.5 animate-pulse"
                  style={{ backgroundColor: colors.lavender, opacity: 0.5 }}
                />
              )}
            </pre>
          </div>
        )}
        
        {/* Empty state when actively thinking but no content yet */}
        {!hasContent && isThinking && (
          <div 
            className="px-3 py-3 text-xs flex items-center gap-2"
            style={{ 
              color: colors.textMuted,
              borderTop: `1px solid ${colors.borderLight}`,
            }}
          >
            <span className="animate-pulse">●</span>
            <span>Nicole is thinking...</span>
          </div>
        )}
        
        {/* Empty state when only tools are shown */}
        {!hasContent && hasToolUses && !isThinking && isComplete && (
          <div 
            className="px-3 pb-2 text-xs"
            style={{ color: colors.textMuted }}
          >
            Used {toolUses.length} tool{toolUses.length !== 1 ? 's' : ''} to help with this response.
          </div>
        )}
      </div>
    </div>
  );
}

export default NicoleThinkingBlock;
