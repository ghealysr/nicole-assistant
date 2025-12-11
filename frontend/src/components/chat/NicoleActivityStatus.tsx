'use client';

/**
 * NicoleActivityStatus - Claude-style Extended Thinking Display
 * 
 * Mimics Claude's extended thinking UI:
 * - Compact main view with "Thinking..." label
 * - Current thought streams in real-time (3 lines visible, fades)
 * - Completed steps collapse into expandable sections
 * - Final interpretation: "Glen is asking me to..."
 * - Everything folds into a single clean box
 * 
 * Styled with Nicole's light lavender palette
 */

import React, { useEffect, useState, useRef, useCallback, memo } from 'react';
import type { ActivityStatus, ThinkingContent } from '@/lib/hooks/alphawave_use_chat';

// Nicole's light purple palette
const colors = {
  bg: '#FAFAFA',              // Very light gray background
  bgHover: '#F5F5F5',         // Hover state
  border: '#E5E5E5',          // Subtle border
  accent: '#9B8AB8',          // Purple accent
  accentLight: '#E8E0F0',     // Light purple
  text: '#374151',            // Primary text
  textMuted: '#6B7280',       // Muted text
  textLight: '#9CA3AF',       // Light text
} as const;

// How long to keep visible after completion (ms)
const COMPLETION_DELAY = 1500;

interface NicoleActivityStatusProps {
  status: ActivityStatus;
}

/**
 * Chevron icon for expand/collapse
 */
const ChevronIcon = memo(function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg 
      className={`w-4 h-4 transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
      fill="none" 
      viewBox="0 0 24 24" 
      stroke="currentColor" 
      strokeWidth={2}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  );
});

/**
 * Completed thinking step - Collapsible accordion
 */
const CompletedStep = memo(function CompletedStep({ 
  step,
  isLast,
}: { 
  step: ThinkingContent;
  isLast: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Truncate title to ~40 chars
  const shortTitle = step.title.length > 40 
    ? step.title.slice(0, 37) + '...' 
    : step.title;
  
  return (
    <div className={`${isLast ? '' : 'border-b'}`} style={{ borderColor: colors.border }}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-gray-50 transition-colors"
        aria-expanded={isExpanded}
      >
        {/* Completion dot */}
        <div 
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: colors.accent }}
        />
        
        {/* Step title */}
        <span 
          className="flex-1 text-xs truncate"
          style={{ color: colors.textMuted }}
        >
          {shortTitle}
        </span>
        
        {/* Expand arrow */}
        <ChevronIcon expanded={isExpanded} />
      </button>
      
      {/* Expandable content */}
      <div 
        className={`overflow-hidden transition-all duration-200 ease-out ${
          isExpanded ? 'max-h-64 opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div 
          className="px-3 pb-3 pt-1 text-xs whitespace-pre-wrap overflow-y-auto max-h-48"
          style={{ 
            color: colors.textMuted,
            marginLeft: '18px', // Align with text after dot
          }}
        >
          {step.content}
        </div>
      </div>
    </div>
  );
});

/**
 * Current thinking - Streaming display with 3-line fade
 */
const CurrentThinking = memo(function CurrentThinking({
  content,
  category,
}: {
  content: string;
  category: string;
}) {
  // Show last ~3 lines worth of content (roughly 200 chars)
  const visibleContent = content.length > 200 
    ? '...' + content.slice(-197)
    : content;
  
  return (
    <div className="px-3 py-2 border-t" style={{ borderColor: colors.border }}>
      {/* Category label */}
      <div 
        className="text-xs font-medium mb-1 flex items-center gap-1.5"
        style={{ color: colors.accent }}
      >
        <div className="w-2 h-2 rounded-full animate-pulse" style={{ backgroundColor: colors.accent }} />
        {category}
      </div>
      
      {/* Streaming content - 3 lines max with fade */}
      <div 
        className="text-xs leading-relaxed overflow-hidden"
        style={{ 
          color: colors.textMuted,
          maxHeight: '4.5em', // ~3 lines
          maskImage: content.length > 150 
            ? 'linear-gradient(to bottom, black 60%, transparent 100%)'
            : undefined,
          WebkitMaskImage: content.length > 150 
            ? 'linear-gradient(to bottom, black 60%, transparent 100%)'
            : undefined,
        }}
      >
        {visibleContent}
      </div>
    </div>
  );
});

/**
 * Main activity status component - Claude-style extended thinking
 */
export function NicoleActivityStatus({ status }: NicoleActivityStatusProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const [isExpanded, setIsExpanded] = useState(true); // Main box expansion
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Calculate visibility
  const shouldBeVisible = useCallback(() => {
    if (status.isActive) return true;
    if (status.currentThinking) return true;
    if (status.completedAt && status.thinkingSteps.length > 0) {
      const elapsed = Date.now() - status.completedAt;
      return elapsed < COMPLETION_DELAY;
    }
    return false;
  }, [status.isActive, status.currentThinking, status.completedAt, status.thinkingSteps.length]);
  
  // Manage visibility transitions
  useEffect(() => {
    const shouldShow = shouldBeVisible();
    
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
    
    if (shouldShow && !isVisible) {
      setIsExiting(false);
      setIsVisible(true);
      setIsExpanded(true); // Auto-expand when new thinking starts
    } else if (!shouldShow && isVisible && !isExiting) {
      setIsExiting(true);
      hideTimerRef.current = setTimeout(() => {
        setIsVisible(false);
        setIsExiting(false);
      }, 200);
    } else if (shouldShow && status.completedAt) {
      const elapsed = Date.now() - status.completedAt;
      const remaining = COMPLETION_DELAY - elapsed;
      if (remaining > 0) {
        hideTimerRef.current = setTimeout(() => {
          setIsExiting(true);
          hideTimerRef.current = setTimeout(() => {
            setIsVisible(false);
            setIsExiting(false);
          }, 200);
        }, remaining);
      }
    }
    
    return () => {
      if (hideTimerRef.current) {
        clearTimeout(hideTimerRef.current);
      }
    };
  }, [shouldBeVisible, isVisible, isExiting, status.completedAt]);
  
  if (!isVisible) {
    return null;
  }
  
  const hasSteps = status.thinkingSteps.length > 0;
  const hasCurrentThinking = !!status.currentThinking;
  const hasContent = hasSteps || hasCurrentThinking;
  
  return (
    <div className="py-3 px-6">
      <div className="max-w-[800px] mx-auto">
        <div 
          className={`
            rounded-lg overflow-hidden
            transition-all duration-200 ease-out
            ${isExiting ? 'opacity-0 translate-y-1' : 'opacity-100 translate-y-0'}
          `}
          style={{
            backgroundColor: colors.bg,
            border: `1px solid ${colors.border}`,
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          }}
        >
          {/* Header - Always visible, clickable to expand/collapse */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full flex items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-gray-50"
            disabled={!hasContent}
          >
            {/* Thinking indicator */}
            {status.isActive ? (
              <div className="flex items-center gap-1">
                <span 
                  className="w-1.5 h-1.5 rounded-full animate-pulse"
                  style={{ backgroundColor: colors.accent }}
                />
                <span 
                  className="w-1.5 h-1.5 rounded-full animate-pulse"
                  style={{ backgroundColor: colors.accent, animationDelay: '0.15s' }}
                />
                <span 
                  className="w-1.5 h-1.5 rounded-full animate-pulse"
                  style={{ backgroundColor: colors.accent, animationDelay: '0.3s' }}
                />
              </div>
            ) : (
              <svg 
                className="w-4 h-4" 
                style={{ color: colors.accent }}
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor" 
                strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            )}
            
            {/* Status text */}
            <span 
              className="flex-1 text-sm font-medium"
              style={{ color: colors.text }}
            >
              {status.isActive ? 'Thinking...' : 'Thought process'}
            </span>
            
            {/* Step count badge */}
            {hasSteps && (
              <span 
                className="text-xs px-1.5 py-0.5 rounded"
                style={{ 
                  backgroundColor: colors.accentLight,
                  color: colors.accent,
                }}
              >
                {status.thinkingSteps.length}
              </span>
            )}
            
            {/* Expand arrow */}
            {hasContent && <ChevronIcon expanded={isExpanded} />}
          </button>
          
          {/* Expandable content area */}
          <div 
            className={`overflow-hidden transition-all duration-200 ease-out ${
              isExpanded && hasContent ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'
            }`}
          >
            {/* Completed steps - Each collapsible */}
            {status.thinkingSteps.map((step, index) => (
              <CompletedStep 
                key={step.id} 
                step={step}
                isLast={index === status.thinkingSteps.length - 1 && !hasCurrentThinking}
              />
            ))}
            
            {/* Current streaming thought */}
            {hasCurrentThinking && (
              <CurrentThinking 
                content={status.currentThinking!}
                category={status.displayText || 'Thinking'}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default NicoleActivityStatus;
