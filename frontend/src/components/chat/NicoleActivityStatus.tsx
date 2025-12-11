'use client';

/**
 * NicoleActivityStatus - Real-time thinking display
 * 
 * Shows Nicole's actual thinking process in real-time:
 * - Current thought scrolls as it streams in
 * - Completed steps become collapsible accordions
 * - User can expand any step to re-read the thinking
 * 
 * Styled with Nicole's lavender color palette
 */

import React, { useEffect, useState, useRef } from 'react';
import Image from 'next/image';
import type { ActivityStatus, ThinkingContent } from '@/lib/hooks/alphawave_use_chat';

// Nicole's color palette
const colors = {
  lavender: '#B8A8D4',
  lavenderLight: '#E8E0F0',
  lavenderMid: '#D4C8E8',
  lavenderDark: '#9B8AB8',
  teal: '#BCD1CB',
  white: '#FFFFFF',
  textPrimary: '#374151',
  textSecondary: '#6b7280',
  textLight: '#9ca3af',
};

interface NicoleActivityStatusProps {
  status: ActivityStatus;
}

/**
 * Pulsing dots animation
 */
function ActivityDots() {
  return (
    <div className="activity-dots flex items-center gap-1 ml-2">
      <span 
        className="activity-dot w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: colors.lavender }}
      />
      <span 
        className="activity-dot w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: colors.lavender, animationDelay: '0.15s' }}
      />
      <span 
        className="activity-dot w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: colors.lavender, animationDelay: '0.3s' }}
      />
    </div>
  );
}

/**
 * Collapsible thinking step accordion
 */
function ThinkingStepAccordion({ step }: { step: ThinkingContent }) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  return (
    <div 
      className="thinking-step-accordion rounded-lg overflow-hidden mb-2 last:mb-0"
      style={{ 
        backgroundColor: colors.white,
        border: `1px solid ${colors.lavenderLight}`,
      }}
    >
      {/* Header - Always visible, clickable */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-left transition-colors hover:bg-gray-50"
      >
        <div className="flex items-center gap-2 min-w-0">
          {/* Checkmark */}
          <div 
            className="w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ backgroundColor: colors.lavender }}
          >
            <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
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
          className={`w-4 h-4 flex-shrink-0 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
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
        className={`overflow-hidden transition-all duration-200 ease-out ${isExpanded ? 'max-h-48' : 'max-h-0'}`}
      >
        <div 
          className="px-3 pb-3 pt-1 text-xs overflow-y-auto max-h-40"
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
}

export function NicoleActivityStatus({ status }: NicoleActivityStatusProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll to bottom when new content arrives
  useEffect(() => {
    if (scrollRef.current && status.currentThinking) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [status.currentThinking]);
  
  // Handle visibility transitions
  useEffect(() => {
    const hasContent = status.isActive || status.thinkingSteps.length > 0 || status.currentThinking;
    
    if (hasContent) {
      setIsExiting(false);
      setIsVisible(true);
    } else if (isVisible && !status.isActive && status.thinkingSteps.length === 0) {
      // Only exit if truly done
      setIsExiting(true);
      const timer = setTimeout(() => {
        setIsVisible(false);
        setIsExiting(false);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [status.isActive, status.thinkingSteps.length, status.currentThinking, isVisible]);
  
  // Don't render if not visible and no content
  if (!isVisible && !status.isActive && status.thinkingSteps.length === 0) {
    return null;
  }
  
  const hasThinkingContent = status.thinkingSteps.length > 0 || status.currentThinking;
  
  return (
    <div className="py-4 px-6">
      <div className="max-w-[800px] mx-auto">
        <div 
          className={`
            nicole-activity-status
            rounded-xl overflow-hidden
            ${isExiting ? 'activity-status-exit' : 'activity-status-enter'}
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
            {/* Spinning Nicole Avatar */}
            <div className="w-6 h-6 flex-shrink-0">
              <Image 
                src="/images/nicole-thinking-avatar.png" 
                alt="Nicole thinking" 
                width={24} 
                height={24}
                className="w-6 h-6 animate-spin-slow"
              />
            </div>
            
            {/* Status Text */}
            <div 
              className="flex-1 text-sm font-medium"
              style={{ color: colors.textPrimary }}
            >
              {status.displayText || 'Thinking...'}
            </div>
            
            {/* Pulsing Dots (only when active) */}
            {status.isActive && <ActivityDots />}
          </div>
          
          {/* Content area - scrollable */}
          {hasThinkingContent && (
            <div 
              ref={scrollRef}
              className="p-3 overflow-y-auto"
              style={{ maxHeight: '300px' }}
            >
              {/* Completed steps as accordions */}
              {status.thinkingSteps.map((step) => (
                <ThinkingStepAccordion key={step.id} step={step} />
              ))}
              
              {/* Current thinking - streaming */}
              {status.currentThinking && (
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
                      className="text-xs flex-1"
                      style={{ color: colors.textSecondary }}
                    >
                      {status.currentThinking}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default NicoleActivityStatus;
