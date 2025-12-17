'use client';

/**
 * NicoleActivityStatus - Activity Indicator with Extended Thinking
 * 
 * Claude-style thinking experience:
 * 1. Thinking block opens and streams content in real-time
 * 2. When complete, auto-collapses to accordion
 * 3. Response streams after thinking collapses
 * 
 * Styling: Subtle tan background with very light purple stroke
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import type { ActivityStatus, ToolUse } from '@/lib/hooks/alphawave_use_chat';
import { NicoleThinkingBlock } from './NicoleThinkingBlock';

// Re-export ToolUse for components that need it
export type { ToolUse };

interface NicoleActivityStatusProps {
  status: ActivityStatus;
}

/**
 * Main activity status component
 * Now primarily a wrapper for NicoleThinkingBlock with Claude-style behavior
 */
export function NicoleActivityStatus({ status }: NicoleActivityStatusProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Check if we have extended thinking content
  const hasThinkingContent = status.extendedThinking?.content?.length > 0;
  const isThinkingActive = status.extendedThinking?.isThinking;
  const hasToolUses = status.toolUses && status.toolUses.length > 0;
  
  // Calculate visibility
  const shouldBeVisible = useCallback(() => {
    if (isThinkingActive) return true;
    if (hasThinkingContent) return true;
    if (hasToolUses) return true;
    if (status.isActive && status.type !== 'responding') return true;
    return false;
  }, [status.isActive, status.type, hasThinkingContent, isThinkingActive, hasToolUses]);
  
  // Manage visibility
  useEffect(() => {
    const shouldShow = shouldBeVisible();
    
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
    
    if (shouldShow && !isVisible) {
      setIsExiting(false);
      setIsVisible(true);
    } else if (!shouldShow && isVisible && !isExiting) {
      // Delay hiding slightly for smooth transition
      hideTimerRef.current = setTimeout(() => {
        setIsExiting(true);
        hideTimerRef.current = setTimeout(() => {
          setIsVisible(false);
          setIsExiting(false);
        }, 200);
      }, 300);
    }
    
    return () => {
      if (hideTimerRef.current) {
        clearTimeout(hideTimerRef.current);
      }
    };
  }, [shouldBeVisible, isVisible, isExiting]);
  
  // Only render if we have thinking content or tool uses
  if (!isVisible && !hasThinkingContent && !hasToolUses) {
    return null;
  }
  
  // If we have extended thinking content or tool uses, show the ThinkingBlock
  if (hasThinkingContent || isThinkingActive || hasToolUses) {
    return (
      <div 
        className={`
          transition-all duration-200 ease-out
          ${isExiting ? 'opacity-0 translate-y-1' : 'opacity-100 translate-y-0'}
        `}
      >
        <NicoleThinkingBlock
          isThinking={status.extendedThinking?.isThinking || false}
          content={status.extendedThinking?.content || ''}
          duration={status.extendedThinking?.duration}
          isComplete={status.extendedThinking?.isComplete || false}
          toolUses={status.toolUses}
        />
      </div>
    );
  }
  
  // Memory notification (shows briefly when Nicole remembers something)
  if (status.memoryNotification) {
    return (
      <div className="transition-all duration-300 ease-out animate-fade-in">
        <div 
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
          style={{
            background: 'rgba(184, 168, 212, 0.1)',
            border: '1px solid rgba(184, 168, 212, 0.2)',
            color: '#6b7280',
          }}
        >
          <span>💾</span>
          <span>{status.memoryNotification}</span>
        </div>
      </div>
    );
  }
  
  return null;
}

export default NicoleActivityStatus;
