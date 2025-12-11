'use client';

/**
 * NicoleActivityStatus - Real-time activity indicator
 * 
 * Shows what Nicole is currently doing during processing:
 * - Thinking, searching, loading tools, analyzing documents, etc.
 * 
 * Features:
 * - Animated spinning avatar
 * - Dynamic status text
 * - Pulsing activity dots
 * - Smooth fade in/out transitions
 * 
 * Styled to match Nicole's lavender/teal color palette
 */

import React, { useEffect, useState } from 'react';
import Image from 'next/image';
import type { ActivityStatus } from '@/lib/hooks/alphawave_use_chat';

// Nicole's color palette
const colors = {
  lavender: '#B8A8D4',
  lavenderLight: '#E8E0F0',
  lavenderDark: '#9B8AB8',
  teal: '#BCD1CB',
  tealDark: '#7A9B93',
  white: '#FFFFFF',
  textPrimary: '#374151',
  textSecondary: '#6b7280',
};

interface NicoleActivityStatusProps {
  status: ActivityStatus;
}

/**
 * Pulsing dots animation component
 */
function ActivityDots() {
  return (
    <div className="activity-dots flex items-center gap-1">
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
 * Tool icon based on activity type
 */
function ActivityIcon({ type, toolName }: { type: string; toolName?: string }) {
  // Determine icon based on tool type
  const getIcon = () => {
    if (toolName) {
      const lowerName = toolName.toLowerCase();
      
      // Web search
      if (lowerName.includes('brave') || lowerName.includes('search') && !lowerName.includes('memory') && !lowerName.includes('document')) {
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
        );
      }
      
      // Memory
      if (lowerName.includes('memory')) {
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M12 2a4 4 0 0 1 4 4v1a3 3 0 0 0 3 3 1 1 0 0 1 1 1v2a1 1 0 0 1-1 1 3 3 0 0 0-3 3v1a4 4 0 0 1-8 0v-1a3 3 0 0 0-3-3 1 1 0 0 1-1-1v-2a1 1 0 0 1 1-1 3 3 0 0 0 3-3V6a4 4 0 0 1 4-4z" />
          </svg>
        );
      }
      
      // Documents
      if (lowerName.includes('document')) {
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
            <path d="M14 2v6h6" />
            <path d="M16 13H8M16 17H8M10 9H8" />
          </svg>
        );
      }
      
      // Notion
      if (lowerName.includes('notion')) {
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.98-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466l1.823 1.447zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.166V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952l1.448.327s0 .84-1.168.84l-3.22.186c-.094-.187 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.454-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.514.28-.887.747-.933l3.224-.186z"/>
          </svg>
        );
      }
      
      // Image generation
      if (lowerName.includes('image') || lowerName.includes('recraft')) {
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <path d="M21 15l-5-5L5 21" />
          </svg>
        );
      }
      
      // Skills
      if (lowerName.includes('skill')) {
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        );
      }
      
      // Think/reasoning
      if (lowerName.includes('think')) {
        return (
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        );
      }
    }
    
    // Default thinking icon
    return (
      <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <circle cx="12" cy="12" r="10" />
        <path d="M12 6v6l4 2" />
      </svg>
    );
  };
  
  return (
    <div 
      className="w-6 h-6 rounded-lg flex items-center justify-center"
      style={{ 
        backgroundColor: colors.lavenderLight,
        color: colors.lavenderDark,
      }}
    >
      {getIcon()}
    </div>
  );
}

export function NicoleActivityStatus({ status }: NicoleActivityStatusProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [displayText, setDisplayText] = useState(status.displayText);
  const [isExiting, setIsExiting] = useState(false);
  
  // Handle visibility transitions
  useEffect(() => {
    if (status.isActive) {
      setIsExiting(false);
      setIsVisible(true);
      setDisplayText(status.displayText);
    } else if (isVisible) {
      // Start exit animation
      setIsExiting(true);
      const timer = setTimeout(() => {
        setIsVisible(false);
        setIsExiting(false);
      }, 200); // Match exit animation duration
      return () => clearTimeout(timer);
    }
  }, [status.isActive, status.displayText, isVisible]);
  
  // Smooth text transitions
  useEffect(() => {
    if (status.isActive && status.displayText !== displayText) {
      setDisplayText(status.displayText);
    }
  }, [status.displayText, status.isActive, displayText]);
  
  if (!isVisible) {
    return null;
  }
  
  return (
    <div className="py-4 px-6">
      <div className="max-w-[800px] mx-auto flex justify-center">
        <div 
          className={`
            nicole-activity-status
            flex items-center gap-3 px-4 py-3 rounded-xl
            ${isExiting ? 'activity-status-exit' : 'activity-status-enter'}
          `}
          style={{
            backgroundColor: colors.white,
            border: `1px solid ${colors.lavender}`,
            boxShadow: '0 2px 12px rgba(184, 168, 212, 0.15)',
            minWidth: '200px',
            maxWidth: '400px',
          }}
        >
          {/* Spinning Nicole Avatar */}
          <div className="w-7 h-7 flex-shrink-0">
            <Image 
              src="/images/nicole-thinking-avatar.png" 
              alt="Nicole thinking" 
              width={28} 
              height={28}
              className="w-7 h-7 animate-spin-slow"
            />
          </div>
          
          {/* Activity Icon (for tool type) */}
          {status.type === 'tool' && (
            <ActivityIcon type={status.type} toolName={status.toolName} />
          )}
          
          {/* Status Text */}
          <div 
            className="flex-1 text-sm font-medium activity-text-transition"
            style={{ color: colors.textPrimary }}
          >
            {displayText}
          </div>
          
          {/* Pulsing Dots */}
          <ActivityDots />
        </div>
      </div>
    </div>
  );
}

export default NicoleActivityStatus;

