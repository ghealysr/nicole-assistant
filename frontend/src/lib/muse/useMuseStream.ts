/**
 * Muse Design Research - SSE Stream Hook
 * 
 * Handles real-time progress updates from the Muse research workflow.
 */

import { useCallback, useRef, useEffect } from 'react';
import { getAuthHeaders } from '@/lib/alphawave_utils';
import { useMuseStore } from './store';
import type { MuseEvent } from './api';

// Use environment variable for API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.nicole.alphawavetech.com';

interface UseMuseStreamOptions {
  projectId: number;
  onMoodboardsReady?: () => void;
  onStyleGuideReady?: () => void;
  onError?: (error: string) => void;
}

export function useMuseStream({ 
  projectId, 
  onMoodboardsReady, 
  onStyleGuideReady,
  onError 
}: UseMuseStreamOptions) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const { 
    setProgress, 
    addEvent, 
    setPhase, 
    setError,
    setMoodboards,
    updateMoodboard,
    setStyleGuide 
  } = useMuseStore();

  const connect = useCallback(async () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const headers = await getAuthHeaders() as Record<string, string> | null;
      const authToken = headers?.Authorization?.replace('Bearer ', '') || '';
      
      const url = `${API_BASE_URL}/muse/projects/${projectId}/stream?token=${encodeURIComponent(authToken)}`;
      
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        console.log('[MuseStream] Connected');
      };

      eventSource.onerror = (error) => {
        console.error('[MuseStream] Connection error:', error);
        setError('Connection to research stream lost. Please refresh.');
        onError?.('Stream connection error');
      };

      // Phase updates
      eventSource.addEventListener('phase_started', (e) => {
        const data = JSON.parse(e.data);
        setProgress({
          phase: data.phase_id,
          progress: 0,
          message: data.name || 'Starting phase...'
        });
        addEvent({ type: 'phase_started', data, timestamp: new Date().toISOString() });
      });

      eventSource.addEventListener('phase_progress', (e) => {
        const data = JSON.parse(e.data);
        setProgress({
          phase: data.phase_id,
          progress: data.progress || 0,
          message: data.message || ''
        });
      });

      eventSource.addEventListener('phase_complete', (e) => {
        const data = JSON.parse(e.data);
        setProgress({
          phase: data.phase_id,
          progress: 100,
          message: 'Complete'
        });
        addEvent({ type: 'phase_complete', data, timestamp: new Date().toISOString() });
      });

      // Inspiration events
      eventSource.addEventListener('inspiration_found', (e) => {
        const data = JSON.parse(e.data);
        addEvent({ type: 'inspiration_found', data, timestamp: new Date().toISOString() });
      });

      eventSource.addEventListener('finding_found', (e) => {
        const data = JSON.parse(e.data);
        addEvent({ type: 'finding_found', data, timestamp: new Date().toISOString() });
      });

      // Mood board events
      eventSource.addEventListener('moodboard_generated', (e) => {
        const data = JSON.parse(e.data);
        addEvent({ type: 'moodboard_generated', data, timestamp: new Date().toISOString() });
      });
      
      // Streaming moodboard generation events
      eventSource.addEventListener('moodboard_streamed', (e) => {
        const data = JSON.parse(e.data);
        setProgress({
          phase: 'generating_moodboards',
          progress: Math.round((data.option_number / data.total) * 80),
          message: `Generated mood board ${data.option_number}/${data.total}: ${data.title || ''}`
        });
        addEvent({ type: 'moodboard_streamed', data, timestamp: new Date().toISOString() });
      });
      
      // Image generation progress for moodboards
      eventSource.addEventListener('moodboard_generating_image', (e) => {
        const data = JSON.parse(e.data);
        setProgress({
          phase: 'generating_moodboards',
          progress: 80 + Math.round((data.progress / data.total) * 20),
          message: `Generating preview image ${data.progress}/${data.total}...`
        });
        addEvent({ type: 'moodboard_generating_image', data, timestamp: new Date().toISOString() });
      });
      
      // Preview image generated for a moodboard
      eventSource.addEventListener('moodboard_preview_generated', (e) => {
        const data = JSON.parse(e.data);
        // Update the moodboard with the generated image using dedicated updater
        updateMoodboard(data.moodboard_id, { preview_image_b64: data.preview_image_b64 });
        setProgress({
          phase: 'generating_moodboards',
          progress: 80 + Math.round((data.progress / data.total) * 20),
          message: `Preview generated for ${data.progress}/${data.total} mood boards`
        });
        addEvent({ type: 'moodboard_preview_generated', data, timestamp: new Date().toISOString() });
      });

      eventSource.addEventListener('moodboards_ready', (e) => {
        const data = JSON.parse(e.data);
        if (data.moodboards) {
          setMoodboards(data.moodboards);
        }
        setPhase('selecting');
        onMoodboardsReady?.();
        addEvent({ type: 'moodboards_ready', data, timestamp: new Date().toISOString() });
      });

      // Style guide events
      eventSource.addEventListener('styleguide_ready', (e) => {
        const data = JSON.parse(e.data);
        if (data.style_guide) {
          setStyleGuide(data.style_guide);
        }
        setPhase('reviewing');
        onStyleGuideReady?.();
        addEvent({ type: 'styleguide_ready', data, timestamp: new Date().toISOString() });
      });

      // Revision events
      eventSource.addEventListener('revision_started', (e) => {
        const data = JSON.parse(e.data);
        setProgress({
          phase: 'style_guide_revision',
          progress: 0,
          message: 'Revising design based on your feedback...'
        });
        addEvent({ type: 'revision_started', data, timestamp: new Date().toISOString() });
      });

      // User action required
      eventSource.addEventListener('awaiting_user_action', (e) => {
        const data = JSON.parse(e.data);
        if (data.action === 'select_mood_board') {
          setPhase('selecting');
          if (data.mood_boards) {
            setMoodboards(data.mood_boards);
          }
        } else if (data.action === 'approve_design') {
          setPhase('reviewing');
        }
        addEvent({ type: 'awaiting_user_action', data, timestamp: new Date().toISOString() });
      });

      // Workflow events
      eventSource.addEventListener('workflow_started', (e) => {
        const data = JSON.parse(e.data);
        setPhase('researching');
        addEvent({ type: 'workflow_started', data, timestamp: new Date().toISOString() });
      });

      eventSource.addEventListener('workflow_complete', (e) => {
        const data = JSON.parse(e.data);
        setPhase('approved');
        addEvent({ type: 'workflow_complete', data, timestamp: new Date().toISOString() });
        eventSource.close();
      });

      eventSource.addEventListener('workflow_failed', (e) => {
        const data = JSON.parse(e.data);
        setError(data.error || 'Research workflow failed');
        onError?.(data.error || 'Workflow failed');
        addEvent({ type: 'workflow_failed', data, timestamp: new Date().toISOString() });
        eventSource.close();
      });

      eventSource.addEventListener('workflow_skipped', (e) => {
        const data = JSON.parse(e.data);
        setPhase('approved'); // Skip directly to approved
        addEvent({ type: 'workflow_skipped', data, timestamp: new Date().toISOString() });
        eventSource.close();
      });

      // Generic complete event from backend polling
      eventSource.addEventListener('complete', (e) => {
        const data = JSON.parse(e.data);
        // Handle different statuses
        if (data.status === 'awaiting_selection') {
          setPhase('selecting');
          onMoodboardsReady?.();
        } else if (data.status === 'awaiting_approval') {
          setPhase('reviewing');
          onStyleGuideReady?.();
        } else if (data.status === 'approved') {
          setPhase('approved');
        }
        addEvent({ type: 'complete', data, timestamp: new Date().toISOString() });
        eventSource.close();
      });

    } catch (error) {
      console.error('[MuseStream] Failed to connect:', error);
      setError('Failed to connect to research stream');
      onError?.('Connection failed');
    }
  }, [projectId, setProgress, addEvent, setPhase, setError, setMoodboards, updateMoodboard, setStyleGuide, onMoodboardsReady, onStyleGuideReady, onError]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return { connect, disconnect };
}

