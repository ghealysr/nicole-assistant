/**
 * Muse Research Progress Modal
 * 
 * Displays real-time progress during the Muse research workflow.
 * Shows phases, findings, and current status with animations.
 */

'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  FileSearch, 
  Palette, 
  Type, 
  Layout, 
  Sparkles,
  CheckCircle2,
  Circle,
  Loader2,
  Image,
  Link2,
  Globe,
  BookOpen
} from 'lucide-react';
import { useMuseStore, useMuseProgress } from '@/lib/muse';
import type { MuseEvent } from '@/lib/muse/api';

interface ResearchProgressModalProps {
  onComplete?: () => void;
}

export function ResearchProgressModal({ onComplete }: ResearchProgressModalProps) {
  const { progress, events, phase } = useMuseStore();

  const phases = [
    { id: 'brief_analysis', name: 'Analyzing Brief', icon: FileSearch },
    { id: 'deep_research', name: 'Deep Research', icon: BookOpen },
    { id: 'inspiration_gathering', name: 'Gathering Inspiration', icon: Image },
    { id: 'mood_board_generation', name: 'Generating Moodboards', icon: Palette },
    { id: 'style_guide_generation', name: 'Creating Style Guide', icon: Layout },
    { id: 'style_guide_revision', name: 'Revising Design', icon: Sparkles },
  ];

  const currentPhaseIndex = phases.findIndex(p => p.id === progress?.phase);

  return (
    <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-lg mx-4 rounded-2xl bg-gray-900 border border-gray-800 shadow-2xl overflow-hidden"
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-gray-800 bg-gradient-to-r from-purple-500/10 to-pink-500/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 
                          flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-purple-400 animate-pulse" />
            </div>
            <div>
              <h2 className="font-semibold text-white">Muse is Researching</h2>
              <p className="text-sm text-gray-400">
                {progress?.message || 'Analyzing your design requirements...'}
              </p>
            </div>
          </div>
        </div>

        {/* Phase Progress */}
        <div className="px-6 py-4">
          <div className="space-y-3">
            {phases.map((phaseItem, index) => {
              const isComplete = index < currentPhaseIndex;
              const isCurrent = phaseItem.id === progress?.phase;
              const isPending = index > currentPhaseIndex;
              const Icon = phaseItem.icon;

              return (
                <motion.div
                  key={phaseItem.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`
                    flex items-center gap-3 p-3 rounded-xl
                    ${isCurrent ? 'bg-purple-500/10 border border-purple-500/30' : 'bg-gray-800/30'}
                  `}
                >
                  <div className={`
                    w-8 h-8 rounded-lg flex items-center justify-center
                    ${isComplete ? 'bg-green-500/20 text-green-400' : 
                      isCurrent ? 'bg-purple-500/20 text-purple-400' : 
                      'bg-gray-800 text-gray-500'}
                  `}>
                    {isComplete ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : isCurrent ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Circle className="w-5 h-5" />
                    )}
                  </div>
                  
                  <div className="flex-1">
                    <p className={`text-sm font-medium ${
                      isComplete || isCurrent ? 'text-white' : 'text-gray-500'
                    }`}>
                      {phaseItem.name}
                    </p>
                    {isCurrent && progress && (
                      <div className="mt-2">
                        <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${progress.progress}%` }}
                            className="h-full bg-gradient-to-r from-purple-500 to-pink-500"
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  <Icon className={`w-4 h-4 ${
                    isComplete ? 'text-green-400' : 
                    isCurrent ? 'text-purple-400' : 
                    'text-gray-600'
                  }`} />
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Live Findings Feed */}
        <div className="px-6 pb-4">
          <div className="h-32 overflow-y-auto bg-gray-950/50 rounded-xl border border-gray-800 p-3">
            <AnimatePresence initial={false}>
              {events.slice(-10).map((event, i) => (
                <motion.div
                  key={`${event.type}-${event.timestamp}-${i}`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="flex items-start gap-2 py-1.5 text-sm"
                >
                  <EventIcon type={event.type} />
                  <span className="text-gray-400">{formatEventMessage(event)}</span>
                </motion.div>
              ))}
            </AnimatePresence>
            {events.length === 0 && (
              <p className="text-gray-500 text-sm text-center py-4">
                Waiting for research findings...
              </p>
            )}
          </div>
        </div>

        {/* Powered By */}
        <div className="px-6 py-3 border-t border-gray-800 bg-gray-900/50">
          <p className="text-xs text-gray-500 text-center">
            Powered by Gemini 2.5 Pro × Enjineer Knowledge Base
          </p>
        </div>
      </motion.div>
    </div>
  );
}

function EventIcon({ type }: { type: string }) {
  switch (type) {
    case 'inspiration_found':
      return <Image className="w-4 h-4 text-pink-400 flex-shrink-0" />;
    case 'finding_found':
      return <BookOpen className="w-4 h-4 text-purple-400 flex-shrink-0" />;
    case 'moodboard_generated':
      return <Palette className="w-4 h-4 text-green-400 flex-shrink-0" />;
    case 'phase_complete':
      return <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />;
    default:
      return <Circle className="w-3 h-3 text-gray-500 flex-shrink-0" />;
  }
}

function formatEventMessage(event: MuseEvent): string {
  const data = event.data as Record<string, string | undefined>;
  
  switch (event.type) {
    case 'phase_started':
      return `Starting ${data?.name || 'phase'}...`;
    case 'phase_complete':
      return `Completed ${data?.phase_id || 'phase'}`;
    case 'inspiration_found':
      return data?.type === 'image' 
        ? 'Found relevant image inspiration'
        : `Analyzed ${data?.url || 'reference site'}`;
    case 'finding_found':
      return data?.content || 'New research finding';
    case 'moodboard_generated':
      return `Generated "${data?.name || 'moodboard'}" concept`;
    default:
      return data?.message || 'Processing...';
  }
}

