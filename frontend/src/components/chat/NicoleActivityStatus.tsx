'use client';

/**
 * NicoleActivityStatus - Simple Activity Indicator
 * 
 * Clean, minimal status display showing what Nicole is doing:
 * - Processing, Thinking, Researching, Loading Skill, Calling Tool
 * - No expansion, no accordions - just flows through states
 * - Nicole avatar below with progress-based spinner
 * - Stops spinning right before response starts
 * 
 * Anthropic-quality: Simple, focused, efficient
 */

import React, { useEffect, useState, useRef, useCallback } from 'react';
import Image from 'next/image';
import type { ActivityStatus } from '@/lib/hooks/alphawave_use_chat';

// Clean, minimal color palette
const colors = {
  bg: '#FFFFFF',
  border: '#E5E7EB',
  text: '#374151',
  textMuted: '#6B7280',
  accent: '#9B8AB8',
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
  // If we have a specific display text, use it
  if (status.displayText) {
    // Clean up common patterns
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
    if (text.toLowerCase().includes('understanding')) return 'Processing request...';
    if (text.toLowerCase().includes('generating') || text.toLowerCase().includes('formulating')) return 'Thinking...';
    
    return text;
  }
  
  // Default based on type
  switch (status.type) {
    case 'thinking':
      return 'Thinking...';
    case 'tool':
      if (status.toolName) {
        const name = status.toolName.toLowerCase();
        if (name.includes('brave') || name.includes('search')) return 'Researching...';
        if (name.includes('memory')) return 'Searching memories...';
        if (name.includes('document')) return 'Reviewing documents...';
        if (name.includes('notion')) return 'Checking Notion...';
        if (name.includes('skill')) return 'Loading skill...';
        if (name.includes('mcp')) return 'Calling MCP tool...';
        return `Using ${status.toolName}...`;
      }
      return 'Using tool...';
    case 'responding':
      return 'Responding...';
    default:
      return 'Processing...';
  }
}

/**
 * Main activity status component
 * Simple status bar + spinning avatar
 */
export function NicoleActivityStatus({ status }: NicoleActivityStatusProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const [shouldSpin, setShouldSpin] = useState(false);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Calculate visibility
  const shouldBeVisible = useCallback(() => {
    if (status.isActive) return true;
    if (status.currentThinking) return true;
    if (status.completedAt) {
      const elapsed = Date.now() - status.completedAt;
      return elapsed < HIDE_DELAY;
    }
    return false;
  }, [status.isActive, status.currentThinking, status.completedAt]);
  
  // Manage visibility and spinner
  useEffect(() => {
    const shouldShow = shouldBeVisible();
    
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
    
    if (shouldShow && !isVisible) {
      // Show and start spinning
      setIsExiting(false);
      setIsVisible(true);
      setShouldSpin(true);
    } else if (!shouldShow && isVisible && !isExiting) {
      // Stop spinning first, then fade out
      setShouldSpin(false);
      
      // Brief pause before hiding
      hideTimerRef.current = setTimeout(() => {
        setIsExiting(true);
        hideTimerRef.current = setTimeout(() => {
          setIsVisible(false);
          setIsExiting(false);
        }, 200);
      }, 100);
    } else if (shouldShow && status.completedAt) {
      // Completed - stop spinning but stay visible briefly
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
    
    // Keep spinning while actively processing
    if (status.isActive && isVisible) {
      setShouldSpin(true);
    }
    
    return () => {
      if (hideTimerRef.current) {
        clearTimeout(hideTimerRef.current);
      }
    };
  }, [shouldBeVisible, isVisible, isExiting, status.isActive, status.completedAt]);
  
  if (!isVisible) {
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
