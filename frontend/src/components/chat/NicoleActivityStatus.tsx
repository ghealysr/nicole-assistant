'use client';

/**
 * NicoleActivityStatus - Real-time thinking display
 * 
 * Optimized implementation with:
 * - Single source of truth for visibility
 * - Smooth enter/exit transitions
 * - Auto-hide after completion with configurable delay
 * - Collapsible completed steps
 * - Efficient re-renders
 * 
 * Styled with Nicole's lavender color palette
 */

import React, { useEffect, useState, useRef, useCallback, memo } from 'react';
import Image from 'next/image';
import type { ActivityStatus, ThinkingContent } from '@/lib/hooks/alphawave_use_chat';

// Nicole's color palette - Light purple theme
const colors = {
  lavender: '#D4C8E8',           // Primary accent (lighter)
  lavenderLight: '#F3F0F8',      // Background (very light)
  lavenderMid: '#E8E0F0',        // Header background (light)
  lavenderDark: '#B8A8D4',       // Borders and accents
  teal: '#7A9B93',               // Completion checkmark
  white: '#FFFFFF',
  textPrimary: '#374151',
  textSecondary: '#6b7280',
  textLight: '#9ca3af',
} as const;

// How long to keep the box visible after completion (ms)
const COMPLETION_DISPLAY_DURATION = 2000;

interface NicoleActivityStatusProps {
  status: ActivityStatus;
}

/**
 * Pulsing dots animation - memoized for performance
 */
const ActivityDots = memo(function ActivityDots() {
  return (
    <div className="flex items-center gap-1 ml-2">
      {[0, 1, 2].map((i) => (
        <span 
          key={i}
          className="w-1.5 h-1.5 rounded-full animate-pulse"
          style={{ 
            backgroundColor: colors.lavender,
            animationDelay: `${i * 150}ms`,
          }}
        />
      ))}
    </div>
  );
});

/**
 * Collapsible thinking step accordion - memoized
 */
const ThinkingStepAccordion = memo(function ThinkingStepAccordion({ 
  step 
}: { 
  step: ThinkingContent 
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  return (
    <div 
      className="rounded-lg overflow-hidden mb-2 last:mb-0 transition-shadow"
      style={{ 
        backgroundColor: colors.white,
        border: `1px solid ${colors.lavenderLight}`,
      }}
    >
      {/* Header - Always visible, clickable */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-left transition-colors hover:bg-gray-50"
        aria-expanded={isExpanded}
      >
        <div className="flex items-center gap-2 min-w-0">
          {/* Checkmark */}
          <div 
            className="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ backgroundColor: colors.lavender }}
          >
            <svg 
              className="w-2.5 h-2.5 text-white" 
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor" 
              strokeWidth={3}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          
          {/* Title */}
          <span 
            className="text-xs font-medium truncate"
            style={{ color: colors.textPrimary }}
          >
            {step.title}
          </span>
        </div>
        
        {/* Expand/Collapse arrow */}
        <svg 
          className={`w-4 h-4 flex-shrink-0 transition-transform duration-200 ${
            isExpanded ? 'rotate-180' : ''
          }`}
          style={{ color: colors.textSecondary }}
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor" 
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {/* Expandable content */}
      <div 
        className={`overflow-hidden transition-all duration-200 ease-out ${
          isExpanded ? 'max-h-48 opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div 
          className="px-3 pb-3 pt-1 text-xs overflow-y-auto max-h-40 whitespace-pre-wrap"
          style={{ 
            color: colors.textSecondary,
            borderTop: `1px solid ${colors.lavenderLight}`,
          }}
        >
          {step.content}
        </div>
      </div>
    </div>
  );
});

/**
 * Current thinking content - streaming display
 */
const CurrentThinkingDisplay = memo(function CurrentThinkingDisplay({
  content,
}: {
  content: string;
}) {
  return (
    <div 
      className="rounded-lg px-3 py-2"
      style={{ 
        backgroundColor: colors.white,
        border: `1px solid ${colors.lavender}`,
      }}
    >
      <div className="flex items-start gap-2">
        {/* Running indicator */}
        <div 
          className="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5"
          style={{ backgroundColor: colors.lavender }}
        >
          <div className="w-2 h-2 rounded-full bg-white animate-pulse" />
        </div>
        
        {/* Thinking content */}
        <div 
          className="text-xs flex-1 whitespace-pre-wrap"
          style={{ color: colors.textSecondary }}
        >
          {content}
        </div>
      </div>
    </div>
  );
});

/**
 * Main activity status component
 * Uses internal visibility state with smooth transitions
 */
export function NicoleActivityStatus({ status }: NicoleActivityStatusProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Calculate if we should be visible based on activity status
  const shouldBeVisible = useCallback(() => {
    // Always show while active
    if (status.isActive) return true;
    
    // Show while there's current thinking
    if (status.currentThinking) return true;
    
    // If completed recently and has steps, show briefly
    if (status.completedAt && status.thinkingSteps.length > 0) {
      const elapsed = Date.now() - status.completedAt;
      return elapsed < COMPLETION_DISPLAY_DURATION;
    }
    
    return false;
  }, [status.isActive, status.currentThinking, status.completedAt, status.thinkingSteps.length]);
  
  // Manage visibility transitions
  useEffect(() => {
    const shouldShow = shouldBeVisible();
    
    // Clear any existing timer
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
    
    if (shouldShow && !isVisible) {
      // Show immediately
      setIsExiting(false);
      setIsVisible(true);
    } else if (!shouldShow && isVisible && !isExiting) {
      // Start exit animation
      setIsExiting(true);
      
      // Hide after animation completes
      hideTimerRef.current = setTimeout(() => {
        setIsVisible(false);
        setIsExiting(false);
      }, 300); // Match CSS animation duration
    } else if (shouldShow && status.completedAt) {
      // Schedule auto-hide after completion
      const elapsed = Date.now() - status.completedAt;
      const remaining = COMPLETION_DISPLAY_DURATION - elapsed;
      
      if (remaining > 0) {
        hideTimerRef.current = setTimeout(() => {
          setIsExiting(true);
          hideTimerRef.current = setTimeout(() => {
            setIsVisible(false);
            setIsExiting(false);
          }, 300);
        }, remaining);
      }
    }
    
    return () => {
      if (hideTimerRef.current) {
        clearTimeout(hideTimerRef.current);
      }
    };
  }, [shouldBeVisible, isVisible, isExiting, status.completedAt]);
  
  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    if (scrollRef.current && (status.currentThinking || status.thinkingSteps.length > 0)) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [status.currentThinking, status.thinkingSteps.length]);
  
  // Don't render if not visible
  if (!isVisible) {
    return null;
  }
  
  const hasThinkingContent = status.thinkingSteps.length > 0 || status.currentThinking;
  
  return (
    <div className="py-4 px-6">
      <div className="max-w-[800px] mx-auto">
        <div 
          className={`
            rounded-xl overflow-hidden
            transition-all duration-300 ease-out
            ${isExiting ? 'opacity-0 translate-y-2' : 'opacity-100 translate-y-0'}
          `}
          style={{
            backgroundColor: colors.lavenderLight,
            border: `1px solid ${colors.lavenderMid}`,
            boxShadow: '0 4px 16px rgba(184, 168, 212, 0.2)',
          }}
        >
          {/* Header bar */}
          <div 
            className="flex items-center gap-3 px-4 py-3"
            style={{ 
              backgroundColor: colors.lavenderMid,
              borderBottom: hasThinkingContent ? `1px solid ${colors.lavender}` : 'none',
            }}
          >
            {/* Nicole Avatar - spins while active */}
            <div className={`w-6 h-6 flex-shrink-0 ${status.isActive ? 'animate-spin-slow' : ''}`}>
              <Image 
                src="/images/nicole-thinking-avatar.png" 
                alt="Nicole thinking" 
                width={24} 
                height={24}
                className="w-6 h-6 rounded-full"
              />
            </div>
            
            {/* Status Text */}
            <div 
              className="flex-1 text-sm font-medium transition-all duration-200"
              style={{ color: colors.textPrimary }}
            >
              {status.isActive 
                ? (status.displayText || 'Thinking...')
                : (status.thinkingSteps.length > 0 ? 'Completed' : 'Done')
              }
            </div>
            
            {/* Pulsing Dots (only when active) */}
            {status.isActive && <ActivityDots />}
            
            {/* Completion checkmark (when done with steps) */}
            {!status.isActive && status.thinkingSteps.length > 0 && (
              <div 
                className="w-5 h-5 rounded-full flex items-center justify-center"
                style={{ backgroundColor: colors.teal }}
              >
                <svg 
                  className="w-3 h-3 text-white" 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor" 
                  strokeWidth={3}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
            )}
          </div>
          
          {/* Content area - scrollable */}
          {hasThinkingContent && (
            <div 
              ref={scrollRef}
              className="p-3 overflow-y-auto transition-all duration-200"
              style={{ maxHeight: '300px' }}
            >
              {/* Completed steps as accordions */}
              {status.thinkingSteps.map((step) => (
                <ThinkingStepAccordion key={step.id} step={step} />
              ))}
              
              {/* Current thinking - streaming */}
              {status.currentThinking && (
                <CurrentThinkingDisplay content={status.currentThinking} />
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default NicoleActivityStatus;
