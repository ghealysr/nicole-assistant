'use client';

/**
 * ResearchPanel - Slide-in panel for research results
 * 
 * Features:
 * - 50% width slide from right
 * - Backdrop with blur
 * - Loading, artifact, and inspiration views
 * - Smooth spring animations
 */

import { useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ResearchResponse, 
  VibeInspirationResponse,
  ResearchStatus,
  ImageFeedback 
} from '@/lib/hooks/useResearch';
import { ResearchLoading } from './ResearchLoading';
import { ResearchArtifact } from './ResearchArtifact';
import { InspirationGallery } from './InspirationGallery';

interface ResearchPanelProps {
  isOpen: boolean;
  onClose: () => void;
  research: ResearchResponse | null;
  vibeInspirations: VibeInspirationResponse | null;
  status: ResearchStatus;
  statusMessage: string;
  progress: number;
  error: string | null;
  onFeedback?: (feedback: ImageFeedback) => void;
  onRetry?: () => void;
}

// Panel animation config
const panelVariants = {
  hidden: { x: '100%', opacity: 0 },
  visible: { 
    x: 0, 
    opacity: 1,
    transition: {
      type: 'spring',
      damping: 25,
      stiffness: 200,
    }
  },
  exit: { 
    x: '100%', 
    opacity: 0,
    transition: {
      type: 'spring',
      damping: 30,
      stiffness: 300,
    }
  },
};

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
};

export function ResearchPanel({
  isOpen,
  onClose,
  research,
  vibeInspirations,
  status,
  statusMessage,
  progress,
  error,
  onFeedback,
  onRetry,
}: ResearchPanelProps) {
  
  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const handleFeedback = useCallback((feedback: ImageFeedback) => {
    onFeedback?.(feedback);
  }, [onFeedback]);

  const isLoading = status === 'pending' || status === 'researching' || status === 'synthesizing';
  const hasResearch = research !== null && status === 'complete';
  const hasInspirations = vibeInspirations !== null && vibeInspirations.inspirations?.length > 0;

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            className="research-panel-backdrop"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.aside
            className="research-panel"
            variants={panelVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            role="dialog"
            aria-modal="true"
            aria-label="Research Results"
          >
            {/* Header */}
            <header className="research-panel-header">
              <div className="research-panel-title-group">
                <div className="research-panel-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <circle cx="11" cy="11" r="8" />
                    <path d="M21 21l-4.35-4.35" />
                  </svg>
                </div>
                <div>
                  <h2 className="research-panel-title">Research</h2>
                  {status !== 'idle' && status !== 'complete' && (
                    <span className="research-panel-status">{statusMessage}</span>
                  )}
                </div>
              </div>
              
              <button
                className="research-panel-close"
                onClick={onClose}
                aria-label="Close research panel"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </header>

            {/* Content */}
            <div className="research-panel-content">
              {/* Loading State */}
              {isLoading && (
                <ResearchLoading
                  status={status}
                  statusMessage={statusMessage}
                  progress={progress}
                />
              )}

              {/* Error State */}
              {status === 'failed' && error && (
                <div className="research-panel-error">
                  <div className="research-error-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="12" />
                      <line x1="12" y1="16" x2="12.01" y2="16" />
                    </svg>
                  </div>
                  <h3>Research Failed</h3>
                  <p>{error}</p>
                  {onRetry && (
                    <button className="research-retry-btn" onClick={onRetry}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                        <polyline points="23 4 23 10 17 10" />
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                      </svg>
                      Try Again
                    </button>
                  )}
                </div>
              )}

              {/* Inspiration Gallery (Vibe mode) */}
              {hasInspirations && !isLoading && (
                <div className="research-panel-inspirations">
                  <div className="inspirations-header">
                    <h3>Design Inspirations</h3>
                    <span className="inspirations-count">
                      {vibeInspirations.inspirations.length} found
                    </span>
                  </div>
                  
                  {vibeInspirations.design_patterns?.length > 0 && (
                    <div className="inspirations-patterns">
                      <h4>Common Patterns</h4>
                      <div className="patterns-tags">
                        {vibeInspirations.design_patterns.map((pattern, i) => (
                          <span key={i} className="pattern-tag">{pattern}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <InspirationGallery
                    images={vibeInspirations.inspirations}
                    onFeedback={handleFeedback}
                  />
                  
                  {vibeInspirations.recommendations?.length > 0 && (
                    <div className="inspirations-recommendations">
                      <h4>Nicole&apos;s Recommendations</h4>
                      <ul>
                        {vibeInspirations.recommendations.map((rec, i) => (
                          <li key={i}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Research Artifact (General mode) */}
              {hasResearch && !hasInspirations && !isLoading && (
                <ResearchArtifact data={research} />
              )}

              {/* Empty State */}
              {status === 'idle' && !hasResearch && !hasInspirations && (
                <div className="research-panel-empty">
                  <div className="research-empty-illustration">
                    <svg viewBox="0 0 100 100" fill="none">
                      <circle cx="50" cy="50" r="40" stroke="currentColor" strokeWidth={2} strokeDasharray="4 4" />
                      <circle cx="50" cy="50" r="25" stroke="currentColor" strokeWidth={2} />
                      <circle cx="50" cy="50" r="10" fill="currentColor" opacity={0.3} />
                      <path d="M75 75L90 90" stroke="currentColor" strokeWidth={3} strokeLinecap="round" />
                    </svg>
                  </div>
                  <h3>No Research Yet</h3>
                  <p>Ask Nicole to research something or search for design inspiration in Vibe mode.</p>
                  <div className="research-examples">
                    <span className="example">&quot;Research wellness website trends&quot;</span>
                    <span className="example">&quot;Find me doula website designs&quot;</span>
                    <span className="example">&quot;Analyze competitor example.com&quot;</span>
                  </div>
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

export default ResearchPanel;

