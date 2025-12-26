/**
 * Muse Moodboard Selector
 * 
 * Displays 4 moodboard options for user selection.
 * Each moodboard shows colors, typography, and overall aesthetic direction.
 * 
 * Features:
 * - Impression tracking for A/B testing analytics
 * - Time-on-view tracking for selection decisions
 * - AI-generated preview image display
 */

'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Check, 
  Palette, 
  Type, 
  Sparkles,
  ArrowRight,
  RefreshCw,
  Eye
} from 'lucide-react';
import type { MoodBoard } from '@/lib/muse/api';
import { museApi } from '@/lib/muse/api';

interface MoodboardSelectorProps {
  moodboards: MoodBoard[];
  sessionId: number;
  onSelect: (moodboard: MoodBoard) => void;
  onRequestMore: () => void;
  isLoading?: boolean;
}

/**
 * MoodboardSelector component with A/B testing analytics.
 * 
 * Tracks:
 * - Impressions: When each moodboard is first displayed
 * - View time: How long user spends before selecting
 */
export function MoodboardSelector({ 
  moodboards, 
  sessionId,
  onSelect, 
  onRequestMore,
  isLoading = false 
}: MoodboardSelectorProps) {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [previewId, setPreviewId] = useState<number | null>(null);
  
  // Track view time for analytics
  const viewStartTime = useRef<number>(Date.now());
  const trackedImpressions = useRef<Set<number>>(new Set());

  const selectedMoodboard = moodboards.find(m => m.id === selectedId);
  
  // Track impressions when moodboards are displayed
  useEffect(() => {
    const trackImpressions = async () => {
      for (const moodboard of moodboards) {
        if (!trackedImpressions.current.has(moodboard.id)) {
          trackedImpressions.current.add(moodboard.id);
          try {
            await museApi.trackMoodboardImpression(sessionId, moodboard.id);
          } catch (error) {
            console.warn('[MoodboardSelector] Failed to track impression:', error);
          }
        }
      }
    };
    
    if (moodboards.length > 0 && sessionId) {
      trackImpressions();
    }
  }, [moodboards, sessionId]);
  
  // Handle selection with time tracking
  const handleSelect = useCallback((moodboard: MoodBoard) => {
    const timeViewingSeconds = Math.round((Date.now() - viewStartTime.current) / 1000);
    
    // Pass the viewing time to the parent for analytics
    onSelect({
      ...moodboard,
      // Attach time data for the parent to use
      _analytics: {
        timeViewingSeconds,
        impressionCount: moodboards.length
      }
    } as MoodBoard & { _analytics: { timeViewingSeconds: number; impressionCount: number } });
  }, [onSelect, moodboards.length]);

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-800/50 bg-gray-900/50 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Choose Your Direction</h2>
            <p className="text-sm text-gray-400">Select a moodboard to define your design system</p>
          </div>
          <button
            onClick={onRequestMore}
            disabled={isLoading}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm
                     text-gray-400 hover:text-gray-300 hover:bg-gray-800/50
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Generate More
          </button>
        </div>
      </div>

      {/* Moodboard Grid */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-2 gap-4">
          {moodboards.map((moodboard, index) => (
            <motion.div
              key={moodboard.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              onClick={() => setSelectedId(moodboard.id)}
              onMouseEnter={() => setPreviewId(moodboard.id)}
              onMouseLeave={() => setPreviewId(null)}
              className={`
                relative group cursor-pointer rounded-2xl overflow-hidden
                border-2 transition-all duration-300
                ${selectedId === moodboard.id 
                  ? 'border-purple-500 shadow-lg shadow-purple-500/20' 
                  : 'border-gray-800 hover:border-gray-700'
                }
              `}
            >
              {/* Preview Image */}
              <div className="aspect-video bg-gray-800 relative overflow-hidden">
                {moodboard.preview_image_b64 ? (
                  <img
                    src={`data:image/png;base64,${moodboard.preview_image_b64}`}
                    alt={moodboard.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-gray-800 to-gray-900">
                    <Sparkles className="w-8 h-8 text-gray-600" />
                  </div>
                )}
                
                {/* Hover Overlay */}
                <div className={`
                  absolute inset-0 bg-black/60 flex items-center justify-center
                  transition-opacity duration-200
                  ${previewId === moodboard.id ? 'opacity-100' : 'opacity-0'}
                `}>
                  <Eye className="w-6 h-6 text-white" />
                </div>

                {/* Selection Check */}
                <AnimatePresence>
                  {selectedId === moodboard.id && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      exit={{ scale: 0 }}
                      className="absolute top-3 right-3 w-8 h-8 rounded-full bg-purple-500 
                               flex items-center justify-center shadow-lg"
                    >
                      <Check className="w-5 h-5 text-white" />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Content */}
              <div className="p-4 bg-gray-900/80 backdrop-blur-sm">
                <h3 className="font-semibold text-white mb-1">{moodboard.name}</h3>
                <p className="text-sm text-gray-400 line-clamp-2 mb-3">
                  {moodboard.description}
                </p>

                {/* Color Swatches */}
                <div className="flex items-center gap-2 mb-3">
                  <Palette className="w-4 h-4 text-gray-500" />
                  <div className="flex gap-1">
                    {moodboard.colors.slice(0, 5).map((color, i) => (
                      <div
                        key={i}
                        className="w-5 h-5 rounded-md border border-gray-700"
                        style={{ backgroundColor: color.hex }}
                        title={color.name}
                      />
                    ))}
                    {moodboard.colors.length > 5 && (
                      <div className="w-5 h-5 rounded-md bg-gray-800 flex items-center justify-center text-xs text-gray-500">
                        +{moodboard.colors.length - 5}
                      </div>
                    )}
                  </div>
                </div>

                {/* Typography */}
                <div className="flex items-center gap-2">
                  <Type className="w-4 h-4 text-gray-500" />
                  <span className="text-sm text-gray-400">
                    {moodboard.typography.heading} / {moodboard.typography.body}
                  </span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Selection Preview & Confirm */}
      <AnimatePresence>
        {selectedMoodboard && (
          <motion.div
            initial={{ y: 100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 100, opacity: 0 }}
            className="px-6 py-4 border-t border-gray-800/50 bg-gray-900/90 backdrop-blur-lg"
          >
            <div className="flex items-center gap-4">
              {/* Preview */}
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl overflow-hidden bg-gray-800">
                    {selectedMoodboard.preview_image_b64 ? (
                      <img
                        src={`data:image/png;base64,${selectedMoodboard.preview_image_b64}`}
                        alt={selectedMoodboard.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Sparkles className="w-5 h-5 text-gray-600" />
                      </div>
                    )}
                  </div>
                  <div>
                    <h4 className="font-medium text-white">{selectedMoodboard.name}</h4>
                    <p className="text-sm text-gray-400">Ready to generate full design system</p>
                  </div>
                </div>
              </div>

              {/* Confirm Button */}
              <motion.button
                onClick={() => handleSelect(selectedMoodboard)}
                disabled={isLoading}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="flex items-center gap-2 px-6 py-3 rounded-xl font-medium
                         bg-gradient-to-r from-purple-500 to-pink-500 text-white
                         shadow-lg shadow-purple-500/25 hover:shadow-xl hover:shadow-purple-500/30
                         disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    Confirm Selection
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

