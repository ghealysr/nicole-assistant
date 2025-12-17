'use client';

/**
 * NicoleActivityStatus - Activity Indicator with Extended Thinking
 * 
 * Two modes:
 * 1. Extended Thinking: Shows Claude-style collapsible thinking block with streamed content
 * 2. Simple Status: Shows status pill for tool use and other operations
 * 
 * Extended thinking streams fast, response streams normally
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import Image from 'next/image';
import type { ActivityStatus, ToolUse } from '@/lib/hooks/alphawave_use_chat';
import { NicoleThinkingBlock } from './NicoleThinkingBlock';

// Re-export ToolUse for components that need it
export type { ToolUse };

// Color palette
const colors = {
  bg: '#FFFFFF',
  border: '#E5E7EB',
  text: '#374151',
  textMuted: '#6B7280',
  accent: '#9B8AB8',
  accentLight: '#F8F6FB',
} as const;

// Visibility duration after completion (ms)
const HIDE_DELAY = 800;

interface NicoleActivityStatusProps {
  status: ActivityStatus;
}

/**
 * Get display text for current activity
 */
function getActivityLabel(status: ActivityStatus): string {
  if (status.displayText) {
    const text = status.displayText;
    
    // Tool-specific labels
    if (text.toLowerCase().includes('memory')) return 'Searching memories...';
    if (text.toLowerCase().includes('document')) return 'Reviewing documents...';
    if (text.toLowerCase().includes('web') || text.toLowerCase().includes('brave')) return 'Researching...';
    if (text.toLowerCase().includes('notion')) return 'Checking Notion...';
    if (text.toLowerCase().includes('skill')) return 'Loading skill...';
    if (text.toLowerCase().includes('image') || text.toLowerCase().includes('recraft')) return 'Generating image...';
    if (text.toLowerCase().includes('file')) return 'Reading files...';
    if (text.toLowerCase().includes('mcp')) return 'Calling MCP tool...';
    
    return text;
  }
  
  switch (status.type) {
    case 'thinking':
      return 'Thinking...';
    case 'tool':
      return status.toolName ? `Using ${status.toolName}...` : 'Using tool...';
    case 'responding':
      return 'Responding...';
    default:
      return 'Processing...';
  }
}

/**
 * Main activity status component
 */
export function NicoleActivityStatus({ status }: NicoleActivityStatusProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const [shouldSpin, setShouldSpin] = useState(false);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Check if we have extended thinking content
  const hasThinkingContent = status.extendedThinking?.content?.length > 0;
  const isThinkingActive = status.extendedThinking?.isThinking;
  
  // Calculate visibility
  const shouldBeVisible = useCallback(() => {
    // Always show if actively thinking
    if (isThinkingActive) return true;
    if (status.isActive) return true;
    if (hasThinkingContent && !status.extendedThinking?.isComplete) return true;
    if (status.completedAt) {
      const elapsed = Date.now() - status.completedAt;
      return elapsed < HIDE_DELAY;
    }
    return false;
  }, [status.isActive, status.completedAt, hasThinkingContent, isThinkingActive, status.extendedThinking?.isComplete]);
  
  // Manage visibility and spinner
  useEffect(() => {
    const shouldShow = shouldBeVisible();
    
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
    
    if (shouldShow && !isVisible) {
      setIsExiting(false);
      setIsVisible(true);
      setShouldSpin(true);
    } else if (!shouldShow && isVisible && !isExiting) {
      setShouldSpin(false);
      hideTimerRef.current = setTimeout(() => {
        setIsExiting(true);
        hideTimerRef.current = setTimeout(() => {
          setIsVisible(false);
          setIsExiting(false);
        }, 200);
      }, 100);
    } else if (shouldShow && status.completedAt && !hasThinkingContent) {
      setShouldSpin(false);
      const elapsed = Date.now() - status.completedAt;
      const remaining = HIDE_DELAY - elapsed;
      
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
    
    if (status.isActive && isVisible) {
      setShouldSpin(true);
    }
    
    return () => {
      if (hideTimerRef.current) {
        clearTimeout(hideTimerRef.current);
      }
    };
  }, [shouldBeVisible, isVisible, isExiting, status.isActive, status.completedAt, hasThinkingContent]);
  
  // Check if we have tool uses to show
  const hasToolUses = status.toolUses && status.toolUses.length > 0;
  
  // If we have extended thinking content or tool uses, show the ThinkingBlock
  if (hasThinkingContent || isThinkingActive || hasToolUses) {
    return (
      <div 
        className={`
          py-3 px-6
          transition-all duration-200 ease-out
          ${isExiting ? 'opacity-0 translate-y-2' : 'opacity-100 translate-y-0'}
        `}
      >
        <div className="max-w-[800px] mx-auto">
          <NicoleThinkingBlock
            isThinking={status.extendedThinking?.isThinking || false}
            content={status.extendedThinking?.content || ''}
            duration={status.extendedThinking?.duration}
            isComplete={status.extendedThinking?.isComplete || false}
            toolUses={status.toolUses}
          />
        </div>
      </div>
    );
  }
  
  // Memory notification (shows briefly when Nicole remembers something)
  if (status.memoryNotification && !isVisible) {
    return (
      <div className="py-2 px-6 transition-all duration-300 ease-out animate-fade-in">
        <div className="max-w-[800px] mx-auto flex justify-center">
          <div 
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full"
            style={{
              background: 'linear-gradient(135deg, #f0e8ff 0%, #e8f4ff 100%)',
              border: '1px solid #d4c6f5',
              boxShadow: '0 2px 8px rgba(155, 138, 184, 0.2)',
            }}
          >
            <span className="text-sm font-medium text-purple-700">
              {status.memoryNotification}
            </span>
          </div>
        </div>
      </div>
    );
  }
  
  // Simple status pill for non-thinking operations
  if (!isVisible && !status.memoryNotification) {
    return null;
  }
  
  const activityLabel = getActivityLabel(status);
  
  return (
    <div 
      className={`
        py-4 px-6
        transition-all duration-200 ease-out
        ${isExiting ? 'opacity-0 translate-y-2' : 'opacity-100 translate-y-0'}
      `}
    >
      <div className="max-w-[800px] mx-auto flex flex-col items-center gap-3">
        {/* Status Box */}
        <div 
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full"
          style={{
            backgroundColor: colors.bg,
            border: `1px solid ${colors.border}`,
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          }}
        >
          {/* Pulsing dot indicator */}
          <div 
            className={`w-2 h-2 rounded-full ${status.isActive ? 'animate-pulse' : ''}`}
            style={{ backgroundColor: colors.accent }}
          />
          
          {/* Status text */}
          <span 
            className="text-sm font-medium"
            style={{ color: colors.text }}
          >
            {activityLabel}
          </span>
        </div>
        
        {/* Nicole Avatar - spins while processing */}
        <div 
          className={`
            w-10 h-10 rounded-full overflow-hidden
            transition-all duration-300
            ${shouldSpin ? 'animate-spin-slow' : ''}
          `}
          style={{
            boxShadow: shouldSpin 
              ? `0 0 12px ${colors.accent}40` 
              : '0 1px 3px rgba(0,0,0,0.1)',
          }}
        >
          <Image 
            src="/images/nicole-thinking-avatar.png" 
            alt="Nicole" 
            width={40} 
            height={40}
            className="w-full h-full object-cover"
          />
        </div>
      </div>
    </div>
  );
}

export default NicoleActivityStatus;
