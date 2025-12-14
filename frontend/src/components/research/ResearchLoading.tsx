'use client';

/**
 * ResearchLoading - Animated loading skeleton for research panel
 * 
 * Features:
 * - Shimmer animation matching artifact layout
 * - Dynamic status message display
 * - Progress bar indicator
 * - Smooth transitions between states
 */

import { motion } from 'framer-motion';
import { ResearchStatus } from '@/lib/hooks/useResearch';

interface ResearchLoadingProps {
  status: ResearchStatus;
  statusMessage: string;
  progress: number;
}

// Status icons with animations
const StatusIcon = ({ status }: { status: ResearchStatus }) => {
  if (status === 'researching') {
    return (
      <motion.div
        className="research-status-icon searching"
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
      </motion.div>
    );
  }
  
  if (status === 'synthesizing') {
    return (
      <motion.div
        className="research-status-icon synthesizing"
        animate={{ scale: [1, 1.2, 1] }}
        transition={{ duration: 1.5, repeat: Infinity }}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
        </svg>
      </motion.div>
    );
  }
  
  return (
    <motion.div
      className="research-status-icon pending"
      animate={{ opacity: [0.5, 1, 0.5] }}
      transition={{ duration: 1.5, repeat: Infinity }}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
    </motion.div>
  );
};

export function ResearchLoading({ status, statusMessage, progress }: ResearchLoadingProps) {
  return (
    <div className="research-loading">
      {/* Animated background */}
      <div className="research-loading-bg">
        <motion.div
          className="research-loading-orb orb-1"
          animate={{
            x: [0, 100, 0],
            y: [0, -50, 0],
            scale: [1, 1.2, 1],
          }}
          transition={{ duration: 8, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="research-loading-orb orb-2"
          animate={{
            x: [0, -80, 0],
            y: [0, 60, 0],
            scale: [1.2, 1, 1.2],
          }}
          transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>

      {/* Status section */}
      <div className="research-loading-status">
        <StatusIcon status={status} />
        
        <motion.h3
          className="research-loading-title"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          key={status}
        >
          {status === 'pending' && 'Initiating Research'}
          {status === 'researching' && 'Searching Sources'}
          {status === 'synthesizing' && 'Analyzing Results'}
        </motion.h3>
        
        <motion.p
          className="research-loading-message"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          key={statusMessage}
        >
          {statusMessage}
        </motion.p>
      </div>

      {/* Progress bar */}
      <div className="research-loading-progress-container">
        <div className="research-loading-progress-bar">
          <motion.div
            className="research-loading-progress-fill"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
        <span className="research-loading-progress-text">{Math.round(progress)}%</span>
      </div>

      {/* Skeleton content preview */}
      <div className="research-loading-skeleton">
        {/* Hero skeleton */}
        <div className="skeleton-hero">
          <div className="skeleton-shimmer" />
        </div>
        
        {/* Title skeleton */}
        <div className="skeleton-title">
          <div className="skeleton-shimmer" />
        </div>
        
        {/* Meta skeleton */}
        <div className="skeleton-meta">
          <div className="skeleton-meta-item"><div className="skeleton-shimmer" /></div>
          <div className="skeleton-meta-item"><div className="skeleton-shimmer" /></div>
          <div className="skeleton-meta-item"><div className="skeleton-shimmer" /></div>
        </div>
        
        {/* Summary card skeleton */}
        <div className="skeleton-summary">
          <div className="skeleton-shimmer" />
        </div>
        
        {/* Findings skeleton */}
        <div className="skeleton-findings">
          {[1, 2, 3].map((i) => (
            <motion.div
              key={i}
              className="skeleton-finding"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.2 }}
            >
              <div className="skeleton-shimmer" />
            </motion.div>
          ))}
        </div>
      </div>

      {/* Decorative elements */}
      <div className="research-loading-decoration">
        {[...Array(5)].map((_, i) => (
          <motion.div
            key={i}
            className="decoration-dot"
            animate={{
              y: [0, -10, 0],
              opacity: [0.3, 1, 0.3],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              delay: i * 0.2,
            }}
          />
        ))}
      </div>
    </div>
  );
}

export default ResearchLoading;


