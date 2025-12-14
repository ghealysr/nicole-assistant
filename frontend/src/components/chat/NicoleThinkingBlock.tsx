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

export interface ThinkingBlockProps {
  /** Whether we're currently receiving thinking content */
  isThinking: boolean;
  /** The accumulated thinking content */
  content: string;
  /** Duration in seconds (set when thinking completes) */
  duration?: number;
  /** Whether thinking has completed */
  isComplete: boolean;
}

export function NicoleThinkingBlock({ 
  isThinking, 
  content, 
  duration,
  isComplete 
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
    if (content.length > 0 || isThinking) {
      setIsVisible(true);
    }
  }, [content, isThinking]);
  
  // Auto-collapse after completion (optional - currently disabled)
  // useEffect(() => {
  //   if (isComplete && duration) {
  //     const timer = setTimeout(() => setIsCollapsed(true), 2000);
  //     return () => clearTimeout(timer);
  //   }
  // }, [isComplete, duration]);
  
  if (!isVisible && !isThinking) {
    return null;
  }
  
  return (
    <div 
      className={`
        rounded-lg overflow-hidden transition-all duration-300 ease-out
        ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}
      `}
      style={{
        backgroundColor: colors.lavenderLight,
        border: `1px solid ${colors.lavenderMid}`,
        boxShadow: '0 2px 8px rgba(184, 168, 212, 0.15)',
      }}
    >
      {/* Header - always visible */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-opacity-50 transition-colors"
        style={{ backgroundColor: isCollapsed ? colors.lavenderMid : 'transparent' }}
      >
        <div className="flex items-center gap-2">
          {/* Thinking icon */}
          <span className="text-base">
            {isComplete ? '💭' : '✨'}
          </span>
          
          {/* Label */}
          <span 
            className="text-sm font-medium"
            style={{ color: colors.textPrimary }}
          >
            {isComplete ? 'Thinking' : 'Thinking'}
            {!isComplete && <ThinkingDots />}
          </span>
          
          {/* Duration badge */}
          {isComplete && duration && (
            <span 
              className="text-xs px-1.5 py-0.5 rounded"
              style={{ 
                backgroundColor: colors.lavenderMid,
                color: colors.textSecondary 
              }}
            >
              {duration}s
            </span>
          )}
        </div>
        
        {/* Collapse toggle */}
        <span 
          className="text-sm transition-transform duration-200"
          style={{ 
            color: colors.textSecondary,
            transform: isCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)'
          }}
        >
          ▼
        </span>
      </button>
      
      {/* Content - collapsible */}
      <div 
        className={`
          transition-all duration-300 ease-out overflow-hidden
          ${isCollapsed ? 'max-h-0' : 'max-h-[400px]'}
        `}
      >
        <div 
          ref={contentRef}
          className="px-4 pb-3 overflow-y-auto font-mono text-sm leading-relaxed"
          style={{ 
            color: colors.textSecondary,
            maxHeight: '350px',
          }}
        >
          {/* Stream the content with a cursor */}
          <pre className="whitespace-pre-wrap break-words">
            {content}
            {!isComplete && (
              <span 
                className="inline-block w-2 h-4 ml-0.5 animate-pulse"
                style={{ backgroundColor: colors.lavender }}
              />
            )}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default NicoleThinkingBlock;


