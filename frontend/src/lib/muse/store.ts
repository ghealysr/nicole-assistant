/**
 * Muse Design Research - Zustand Store
 * 
 * State management for design research workflow.
 */

import { create } from 'zustand';
import type { 
  SessionDetails, 
  InspirationInput, 
  MoodBoard, 
  StyleGuide,
  MuseEvent 
} from './api';

// ============================================================================
// TYPES
// ============================================================================

export type ResearchPhase = 
  | 'idle'           // No active session
  | 'intake'         // Collecting inputs
  | 'researching'    // Research in progress
  | 'selecting'      // User selecting mood board
  | 'generating'     // Style guide being generated
  | 'reviewing'      // User reviewing style guide
  | 'approved'       // Ready for coding
  | 'coding'         // Handed off to Nicole
  | 'error';         // Error state

export interface ResearchProgress {
  phase: string;
  progress: number;
  message: string;
}

export interface MuseState {
  // Session
  sessionId: number | null;
  session: SessionDetails | null;
  phase: ResearchPhase;
  
  // Inputs
  inspirations: InspirationInput[];
  
  // Mood boards
  moodboards: MoodBoard[];
  selectedMoodboard: MoodBoard | null;
  
  // Style guide
  styleGuide: StyleGuide | null;
  
  // Progress
  isLoading: boolean;
  progress: ResearchProgress | null;
  events: MuseEvent[];
  
  // Error
  error: string | null;
  
  // Actions
  setSession: (session: SessionDetails | null) => void;
  setSessionId: (id: number | null) => void;
  setPhase: (phase: ResearchPhase) => void;
  setInspirations: (inspirations: InspirationInput[]) => void;
  addInspiration: (inspiration: InspirationInput) => void;
  removeInspiration: (id: number) => void;
  setMoodboards: (moodboards: MoodBoard[] | ((prev: MoodBoard[]) => MoodBoard[])) => void;
  updateMoodboard: (moodboardId: number, updates: Partial<MoodBoard>) => void;
  selectMoodboard: (moodboard: MoodBoard) => void;
  setStyleGuide: (styleGuide: StyleGuide | null) => void;
  setLoading: (loading: boolean) => void;
  setProgress: (progress: ResearchProgress | null) => void;
  addEvent: (event: MuseEvent) => void;
  clearEvents: () => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

// ============================================================================
// INITIAL STATE
// ============================================================================

const initialState = {
  sessionId: null,
  session: null,
  phase: 'idle' as ResearchPhase,
  inspirations: [],
  moodboards: [],
  selectedMoodboard: null,
  styleGuide: null,
  isLoading: false,
  progress: null,
  events: [],
  error: null,
};

// ============================================================================
// STORE
// ============================================================================

export const useMuseStore = create<MuseState>((set) => ({
  ...initialState,
  
  setSession: (session) => set(() => {
    // Derive phase from session status
    let phase: ResearchPhase = 'idle';
    if (session) {
      switch (session.status) {
        case 'intake':
          phase = 'intake';
          break;
        case 'analyzing_brief':
        case 'researching':
        case 'analyzing_inspiration':
        case 'generating_moodboards':
          phase = 'researching';
          break;
        case 'awaiting_selection':
          phase = 'selecting';
          break;
        case 'generating_design':
          phase = 'generating';
          break;
        case 'awaiting_approval':
          phase = 'reviewing';
          break;
        case 'approved':
          phase = 'approved';
          break;
        case 'handed_off':
          phase = 'coding';
          break;
        case 'failed':
          phase = 'error';
          break;
        default:
          phase = 'idle';
      }
    }
    return { session, sessionId: session?.session_id ?? null, phase };
  }),
  
  setSessionId: (id) => set({ sessionId: id }),
  
  setPhase: (phase) => set({ phase }),
  
  setInspirations: (inspirations) => set({ inspirations }),
  
  addInspiration: (inspiration) => set((state) => ({
    inspirations: [...state.inspirations, inspiration]
  })),
  
  removeInspiration: (id) => set((state) => ({
    inspirations: state.inspirations.filter(i => i.id !== id)
  })),
  
  setMoodboards: (moodboards) => set((state) => ({
    moodboards: typeof moodboards === 'function' 
      ? moodboards(state.moodboards)
      : moodboards
  })),
  
  updateMoodboard: (moodboardId, updates) => set((state) => ({
    moodboards: state.moodboards.map(mb =>
      mb.id === moodboardId ? { ...mb, ...updates } : mb
    )
  })),
  
  selectMoodboard: (moodboard) => set((state) => ({
    selectedMoodboard: moodboard,
    moodboards: state.moodboards.map(m => ({
      ...m,
      is_selected: m.id === moodboard.id
    }))
  })),
  
  setStyleGuide: (styleGuide) => set({ styleGuide }),
  
  setLoading: (isLoading) => set({ isLoading }),
  
  setProgress: (progress) => set({ progress }),
  
  addEvent: (event) => set((state) => ({
    events: [...state.events, event].slice(-100) // Keep last 100 events
  })),
  
  clearEvents: () => set({ events: [] }),
  
  setError: (error) => set({ error, phase: error ? 'error' : 'idle' }),
  
  reset: () => set(initialState),
}));

// ============================================================================
// HELPER HOOKS
// ============================================================================

export const useMusePhase = () => useMuseStore((state) => state.phase);
export const useMuseSession = () => useMuseStore((state) => state.session);
export const useMuseMoodboards = () => useMuseStore((state) => state.moodboards);
export const useMuseStyleGuide = () => useMuseStore((state) => state.styleGuide);
export const useMuseProgress = () => useMuseStore((state) => state.progress);
export const useMuseLoading = () => useMuseStore((state) => state.isLoading);

