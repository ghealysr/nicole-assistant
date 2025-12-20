'use client';

import React, { memo, useEffect, useState, useMemo } from 'react';
import { LotusSphere, type ThinkingState } from './LotusSphere';

/**
 * ThinkingIndicator - Claude-style inline thinking indicator for Nicole
 * 
 * Positioned inline with chat flow, same position where text will appear.
 * Matches Claude.ai's UX:
 * - Appears at start of assistant message area
 * - Inline, not modal/overlay
 * - Small size (32-48px)
 * - Disappears when first token streams
 */

export interface ThinkingIndicatorProps {
  /** Current thinking state */
  state: ThinkingState;
  /** Size in pixels */
  size?: number;
  /** Optional className */
  className?: string;
  /** Whether to show the indicator */
  isVisible?: boolean;
}

export const ThinkingIndicator = memo(function ThinkingIndicator({
  state,
  size = 32,
  className = '',
  isVisible = true,
}: ThinkingIndicatorProps) {
  const [mounted, setMounted] = useState(false);
  const [fadeIn, setFadeIn] = useState(false);
  
  // Fade in on mount
  useEffect(() => {
    setMounted(true);
    const timer = setTimeout(() => setFadeIn(true), 50);
    return () => clearTimeout(timer);
  }, []);
  
  if (!isVisible || !mounted) return null;
  
  return (
    <div 
      className={`inline-flex items-center gap-2 transition-opacity duration-150 ${fadeIn ? 'opacity-100' : 'opacity-0'} ${className}`}
      role="status"
      aria-live="polite"
    >
      <LotusSphere 
        state={state} 
        size={size} 
        isActive={true}
      />
      {/* Optional state label for accessibility */}
      <span className="sr-only">
        {state === 'default' && 'Nicole is preparing a response'}
        {state === 'searching' && 'Nicole is searching'}
        {state === 'thinking' && 'Nicole is thinking'}
        {state === 'processing' && 'Nicole is processing'}
        {state === 'speaking' && 'Nicole is speaking'}
      </span>
    </div>
  );
});

/**
 * Small glowing indicator light - replaces spinning icon in thinking header
 * Simple, minimal indicator for use in collapsed thinking UI
 */
export interface GlowingIndicatorProps {
  /** Whether actively processing */
  isActive: boolean;
  /** Color theme */
  color?: 'purple' | 'green' | 'blue' | 'amber';
  /** Size in pixels */
  size?: number;
  /** Optional className */
  className?: string;
}

export const GlowingIndicator = memo(function GlowingIndicator({
  isActive,
  color = 'purple',
  size = 8,
  className = '',
}: GlowingIndicatorProps) {
  const colorMap = {
    purple: { base: '#9370DB', glow: 'rgba(147, 112, 219, 0.6)' },
    green: { base: '#7A9B93', glow: 'rgba(122, 155, 147, 0.6)' },
    blue: { base: '#6495ED', glow: 'rgba(100, 149, 237, 0.6)' },
    amber: { base: '#FFB347', glow: 'rgba(255, 179, 71, 0.6)' },
  };
  
  const colors = colorMap[color];
  
  return (
    <div
      className={`rounded-full ${className}`}
      style={{
        width: size,
        height: size,
        backgroundColor: colors.base,
        boxShadow: isActive 
          ? `0 0 ${size}px ${colors.glow}, 0 0 ${size * 2}px ${colors.glow}`
          : 'none',
        animation: isActive ? 'glowPulse 1.5s ease-in-out infinite' : 'none',
        opacity: isActive ? 1 : 0.5,
        transition: 'opacity 0.2s, box-shadow 0.2s',
      }}
      aria-hidden="true"
    />
  );
});

/**
 * Hook to manage thinking state based on backend events
 */
export interface UseThinkingStateOptions {
  /** Whether awaiting response (message sent, no content yet) */
  isAwaitingResponse: boolean;
  /** Whether content has started streaming */
  hasStreamedContent: boolean;
  /** Current active tool (if any) */
  activeToolName?: string | null;
  /** Whether tool is currently executing */
  isToolExecuting?: boolean;
  /** Debounce threshold in ms */
  debounceMs?: number;
}

export interface UseThinkingStateResult {
  /** Current thinking state */
  state: ThinkingState;
  /** Whether indicator should be visible */
  showIndicator: boolean;
}

export function useThinkingState({
  isAwaitingResponse,
  hasStreamedContent,
  activeToolName,
  isToolExecuting = false,
  debounceMs = 50,
}: UseThinkingStateOptions): UseThinkingStateResult {
  const [debouncedState, setDebouncedState] = useState<ThinkingState>('default');
  
  // Compute raw state from inputs
  const rawState = useMemo<ThinkingState>(() => {
    if (activeToolName) {
      const lowerTool = activeToolName.toLowerCase();
      if (lowerTool.includes('search') || lowerTool.includes('memory') || lowerTool.includes('brave')) {
        return 'searching';
      }
      return 'processing';
    }
    if (isToolExecuting) {
      return 'processing';
    }
    if (hasStreamedContent) {
      return 'thinking';
    }
    return 'default';
  }, [activeToolName, isToolExecuting, hasStreamedContent]);
  
  // Debounce state changes to prevent flicker
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedState(rawState);
    }, debounceMs);
    return () => clearTimeout(timer);
  }, [rawState, debounceMs]);
  
  // Determine visibility
  const showIndicator = useMemo(() => {
    // Show when:
    // 1. Waiting for response (no content yet)
    // 2. Tool is executing
    // NOT when content is streaming (hide immediately on first token)
    return (isAwaitingResponse && !hasStreamedContent) || isToolExecuting;
  }, [isAwaitingResponse, hasStreamedContent, isToolExecuting]);
  
  return {
    state: debouncedState,
    showIndicator,
  };
}

// CSS for glowing indicator animation
export const thinkingIndicatorStyles = `
  @keyframes glowPulse {
    0%, 100% { 
      opacity: 0.7;
      box-shadow: 0 0 8px rgba(147, 112, 219, 0.4);
    }
    50% { 
      opacity: 1;
      box-shadow: 0 0 12px rgba(147, 112, 219, 0.8), 0 0 24px rgba(147, 112, 219, 0.4);
    }
  }
`;

export default ThinkingIndicator;

