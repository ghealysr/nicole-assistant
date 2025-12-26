/**
 * Muse Design Research - Library Exports
 */

// API Client
export { museApi } from './api';
export type {
  StartResearchRequest,
  SessionDetails,
  InspirationInput,
  MoodBoard,
  StyleGuide,
  MuseEvent,
} from './api';

// Store
export { useMuseStore, useMusePhase, useMuseSession, useMuseMoodboards, useMuseStyleGuide, useMuseProgress, useMuseLoading } from './store';
export type { MuseState, ResearchPhase, ResearchProgress } from './store';

// Hooks
export { useMuseStream } from './useMuseStream';

