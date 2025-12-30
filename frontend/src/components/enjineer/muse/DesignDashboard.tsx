/**
 * Muse Design Dashboard
 * 
 * Main orchestration component for the design research workflow.
 * Manages the flow: Input → Research → Moodboards → Style Guide → Approval
 */

'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  useMuseStore, 
  useMusePhase, 
  useMuseStream,
  museApi
} from '@/lib/muse';
import { ResearchInputForm } from './ResearchInputForm';
import { ResearchProgressModal } from './ResearchProgressModal';
import { MoodboardSelector } from './MoodboardSelector';
import { StyleGuidePreview } from './StyleGuidePreview';
import type { InspirationInput, MoodBoard } from '@/lib/muse/api';

interface DesignDashboardProps {
  projectId: number;
  /** Called when design is approved and ready for coding */
  onComplete?: () => void;
  /** Called when user skips research and goes directly to coding */
  onSkip?: () => void;
}

export function DesignDashboard({ 
  projectId, 
  onComplete,
  onSkip 
}: DesignDashboardProps) {
  // Provide stable no-op defaults when used standalone (prevents infinite re-renders)
  const handleComplete = useCallback(() => {
    onComplete?.();
  }, [onComplete]);
  
  const handleSkip = useCallback(() => {
    onSkip?.();
  }, [onSkip]);
  const phase = useMusePhase();
  const { 
    moodboards,
    styleGuide,
    isLoading,
    error,
    setLoading,
    setError,
    setMoodboards,
    setStyleGuide,
    setPhase,
    reset
  } = useMuseStore();
  
  // Track active session ID for analytics and API calls
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);

  // SSE stream for real-time updates
  const { connect: connectStream, disconnect: disconnectStream } = useMuseStream({
    projectId,
    onMoodboardsReady: async () => {
      // Fetch full moodboard data
      try {
        const mbs = await museApi.getMoodBoards(projectId);
        setMoodboards(mbs);
      } catch (err) {
        console.error('Failed to fetch moodboards:', err);
      }
    },
    onStyleGuideReady: async () => {
      // Fetch full style guide data using project-aware method
      try {
        const sg = await museApi.getProjectStyleGuide(projectId);
        if (sg) setStyleGuide(sg);
      } catch (err) {
        console.error('Failed to fetch style guide:', err);
      }
    },
    onError: (err) => {
      setError(err);
      setLoading(false);
    }
  });

  // Check for existing session on mount
  useEffect(() => {
    const checkExistingSession = async () => {
      try {
        const session = await museApi.getSessionByProject(projectId);
        if (session && session.status !== 'failed') {
          // Store session ID for analytics and API calls
          setActiveSessionId(session.session_id);
          
          // Resume session based on current status
          if (session.status === 'awaiting_selection') {
            const mbs = await museApi.getMoodBoards(projectId);
            setMoodboards(mbs);
            setPhase('selecting');
          } else if (session.status === 'awaiting_approval') {
            const sg = await museApi.getProjectStyleGuide(projectId);
            if (sg) setStyleGuide(sg);
            setPhase('reviewing');
          } else if (session.status === 'approved') {
            setPhase('approved');
            handleComplete();
          } else if (['analyzing_brief', 'researching', 'generating_moodboards', 'analyzing_inspiration', 'generating_design', 'revising_design'].includes(session.status)) {
            setPhase('researching');
            connectStream();
          } else {
            // Fallback for any other active status
            setPhase('intake');
          }
        } else {
          // No session or failed session - start fresh
          setPhase('intake');
        }
      } catch {
        // Error checking session - start fresh
        setPhase('intake');
      }
    };

    checkExistingSession();

    return () => {
      disconnectStream();
    };
  }, [projectId, connectStream, disconnectStream, setMoodboards, setStyleGuide, setPhase, handleComplete]);

  // Handle start research
  const handleStartResearch = useCallback(async (
    brief: string, 
    inspirations: InspirationInput[], 
    skipResearch: boolean
  ) => {
    if (skipResearch) {
      handleSkip();
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await museApi.startResearchWithInspirations(projectId, {
        brief,
        inspiration_images_b64: inspirations
          .filter(i => i.type === 'image')
          .map(i => i.data),
        inspiration_links: inspirations
          .filter(i => i.type === 'url')
          .map(i => i.data),
        skip_research: false
      });
      
      // Store session ID for analytics
      if (result.session_id) {
        setActiveSessionId(result.session_id);
      }

      setPhase('researching');
      connectStream();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start research');
    } finally {
      setLoading(false);
    }
  }, [projectId, connectStream, setLoading, setError, setPhase, handleSkip]);

  // Handle moodboard selection
  const handleSelectMoodboard = useCallback(async (moodboard: MoodBoard) => {
    setLoading(true);
    setError(null);

    try {
      await museApi.selectMoodBoard(projectId, { selected_index: moodboards.indexOf(moodboard) });
      setPhase('generating');
      // Stream will notify when style guide is ready
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to select moodboard');
    } finally {
      setLoading(false);
    }
  }, [projectId, moodboards, setLoading, setError, setPhase]);

  // Handle request more moodboards
  const handleRequestMore = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Get the session to call regenerateMoodboards
      const session = await museApi.getSessionByProject(projectId);
      if (!session) {
        throw new Error('No active session found');
      }
      
      // Call the API to regenerate moodboards
      await museApi.regenerateMoodboards(session.session_id, 4);
      
      // Fetch the new moodboards
      const newMoodboards = await museApi.getMoodBoards(projectId);
      setMoodboards(newMoodboards);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate more options');
    } finally {
      setLoading(false);
    }
  }, [projectId, setLoading, setError, setMoodboards]);

  // Handle style guide approval
  const handleApproveStyleGuide = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      await museApi.approveProjectDesign(projectId);
      setPhase('approved');
      handleComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve design');
    } finally {
      setLoading(false);
    }
  }, [projectId, setLoading, setError, setPhase, handleComplete]);

  // Handle request changes to style guide
  const handleRequestChanges = useCallback(async (feedback: string) => {
    setLoading(true);
    setError(null);

    try {
      // Get the session to call requestStyleGuideChanges
      const session = await museApi.getSessionByProject(projectId);
      if (!session) {
        throw new Error('No active session found');
      }
      
      // Show progress modal during revision
      setPhase('researching');
      
      // Call the API to request changes (this triggers regeneration on backend)
      await museApi.requestStyleGuideChanges(session.session_id, feedback);
      
      // Connect to SSE stream for real-time updates during regeneration
      connectStream();
      
      // Note: The stream will emit events and update the style guide when ready
      // The onStyleGuideReady callback will fetch and set the updated style guide
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to request changes');
      setPhase('reviewing'); // Return to review phase on error
    } finally {
      setLoading(false);
    }
  }, [projectId, setLoading, setError, setPhase, connectStream]);

  return (
    <div className="h-full relative">
      {/* Error Banner */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="absolute top-0 left-0 right-0 z-50 p-4 bg-red-500/10 border-b border-red-500/30"
          >
            <p className="text-red-400 text-sm text-center">{error}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Phase Content */}
      <AnimatePresence mode="wait">
        {(phase === 'idle' || phase === 'intake') && (
          <motion.div
            key="input"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="h-full"
          >
            <ResearchInputForm 
              onStartResearch={handleStartResearch}
              onSkip={handleSkip}
              isLoading={isLoading}
            />
          </motion.div>
        )}

        {phase === 'researching' && (
          <ResearchProgressModal />
        )}

        {(phase === 'selecting' || phase === 'generating') && moodboards.length > 0 && (
          <motion.div
            key="moodboards"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="h-full"
          >
            <MoodboardSelector 
              moodboards={moodboards}
              sessionId={activeSessionId ?? 0}
              onSelect={handleSelectMoodboard}
              onRequestMore={handleRequestMore}
              isLoading={isLoading || phase === 'generating'}
            />
          </motion.div>
        )}

        {phase === 'reviewing' && styleGuide && (
          <motion.div
            key="styleguide"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="h-full"
          >
            <StyleGuidePreview 
              styleGuide={styleGuide}
              onApprove={handleApproveStyleGuide}
              onRequestChanges={handleRequestChanges}
              isLoading={isLoading}
            />
          </motion.div>
        )}

        {phase === 'approved' && (
          <motion.div
            key="approved"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="h-full flex items-center justify-center"
          >
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-green-500/20 
                            flex items-center justify-center">
                <svg className="w-10 h-10 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-2xl font-semibold text-white mb-2">Design Approved!</h2>
              <p className="text-gray-400">Nicole is now building your project...</p>
            </div>
          </motion.div>
        )}

        {phase === 'error' && (
          <motion.div
            key="error"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="h-full flex items-center justify-center"
          >
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-red-500/20 
                            flex items-center justify-center">
                <svg className="w-10 h-10 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
              <h2 className="text-2xl font-semibold text-white mb-2">Something went wrong</h2>
              <p className="text-gray-400 mb-6">{error || 'An unexpected error occurred.'}</p>
              <button
                onClick={() => reset()}
                className="px-6 py-2 rounded-xl bg-gray-800 text-white hover:bg-gray-700 transition-colors"
              >
                Start Over
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

