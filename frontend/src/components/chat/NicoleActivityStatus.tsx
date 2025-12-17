'use client';

/**
 * NicoleActivityStatus - Activity Indicator with Extended Thinking
 * 
 * Claude-style thinking experience:
 * 1. Thinking block opens and streams content in real-time
 * 2. When complete, auto-collapses to accordion
 * 3. Response streams after thinking collapses
 * 4. Nicole's avatar spins while ANY streaming is happening
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
  const isStreaming = status.extendedThinking?.isStreaming;
  const hasToolUses = status.toolUses && status.toolUses.length > 0;
  
  // Calculate visibility - show immediately when active
  const shouldBeVisible = useCallback(() => {
    if (status.isActive) return true;
    if (isThinkingActive) return true;
    if (isStreaming) return true;
    if (hasThinkingContent) return true;
    if (hasToolUses) return true;
    return false;
  }, [status.isActive, hasThinkingContent, isThinkingActive, isStreaming, hasToolUses]);
  
  // Manage visibility - show immediately, hide with delay
  useEffect(() => {
    const shouldShow = shouldBeVisible();
    
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
    
    if (shouldShow && !isVisible) {
      // Show immediately
      setIsExiting(false);
      setIsVisible(true);
    } else if (!shouldShow && isVisible && !isExiting) {
      // Delay hiding for smooth transition
      hideTimerRef.current = setTimeout(() => {
        setIsExiting(true);
        hideTimerRef.current = setTimeout(() => {
          setIsVisible(false);
          setIsExiting(false);
        }, 200);
      }, 500);
    }
    
    return () => {
      if (hideTimerRef.current) {
        clearTimeout(hideTimerRef.current);
      }
    };
  }, [shouldBeVisible, isVisible, isExiting]);
  
  // Don't render if nothing to show
  if (!isVisible && !status.isActive) {
    return null;
  }
  
  // Render the thinking block
  return (
    <div 
      className={`
        transition-all duration-300 ease-out
        ${isExiting ? 'opacity-0 translate-y-1' : 'opacity-100 translate-y-0'}
      `}
    >
      <NicoleThinkingBlock
        isThinking={status.extendedThinking?.isThinking || false}
        content={status.extendedThinking?.content || ''}
        duration={status.extendedThinking?.duration}
        isComplete={status.extendedThinking?.isComplete || false}
        toolUses={status.toolUses}
        isStreaming={status.extendedThinking?.isStreaming || status.isActive}
      />
    </div>
  );
}

export default NicoleActivityStatus;
