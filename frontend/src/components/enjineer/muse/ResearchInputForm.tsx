/**
 * Muse Research Input Form
 * 
 * Collects design brief, inspiration images, and inspiration links
 * before starting the Muse research workflow.
 */

'use client';

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Upload, 
  Link2, 
  Plus, 
  Trash2, 
  Sparkles, 
  ArrowRight,
  Image as ImageIcon,
  ExternalLink,
  FileText,
  Wand2,
  Zap
} from 'lucide-react';
import { useMuseStore, useMusePhase } from '@/lib/muse';
import type { InspirationInput } from '@/lib/muse/api';

interface ResearchInputFormProps {
  onStartResearch: (brief: string, inspirations: InspirationInput[], skipResearch: boolean) => void;
  onSkip: () => void;
  isLoading?: boolean;
}

export function ResearchInputForm({ 
  onStartResearch, 
  onSkip,
  isLoading = false 
}: ResearchInputFormProps) {
  const [brief, setBrief] = useState('');
  const [inspirationUrl, setInspirationUrl] = useState('');
  const [inspirationNote, setInspirationNote] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  
  const { inspirations, addInspiration, removeInspiration, setInspirations } = useMuseStore();

  // Handle image upload
  const handleImageUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    Array.from(files).slice(0, 5 - inspirations.length).forEach((file, index) => {
      const reader = new FileReader();
      reader.onload = (event) => {
        const base64 = (event.target?.result as string)?.split(',')[1];
        if (base64) {
          const newInspiration: InspirationInput = {
            id: Date.now() + index,
            type: 'image',
            data: base64,
            notes: '',
            preview_url: URL.createObjectURL(file),
          };
          addInspiration(newInspiration);
        }
      };
      reader.readAsDataURL(file);
    });
    
    e.target.value = '';
  }, [inspirations.length, addInspiration]);

  // Handle URL addition
  const handleAddUrl = useCallback(() => {
    if (!inspirationUrl.trim()) return;
    
    const newInspiration: InspirationInput = {
      id: Date.now(),
      type: 'url',
      data: inspirationUrl.trim(),
      notes: inspirationNote.trim(),
    };
    addInspiration(newInspiration);
    setInspirationUrl('');
    setInspirationNote('');
  }, [inspirationUrl, inspirationNote, addInspiration]);

  // Handle note update
  const handleUpdateNote = useCallback((id: number, notes: string) => {
    setInspirations(
      inspirations.map(i => i.id === id ? { ...i, notes } : i)
    );
  }, [inspirations, setInspirations]);

  // Handle submit
  const handleSubmit = useCallback(() => {
    if (!brief.trim()) return;
    onStartResearch(brief.trim(), inspirations, false);
  }, [brief, inspirations, onStartResearch]);

  const canSubmit = brief.trim().length > 10;
  const canAddMore = inspirations.length < 5;

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-800/50 bg-gray-900/50 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center">
            <Wand2 className="w-5 h-5 text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Design Research</h2>
            <p className="text-sm text-gray-400">Powered by Muse × Gemini 2.5 Pro</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Brief Input */}
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm font-medium text-gray-300">
            <FileText className="w-4 h-4 text-purple-400" />
            Design Brief
          </label>
          <textarea
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            placeholder="Describe your vision... What style, mood, and aesthetic are you looking for? What is the project purpose and target audience?"
            className="w-full h-36 px-4 py-3 rounded-xl bg-gray-800/50 border border-gray-700/50 
                     text-white placeholder:text-gray-500 resize-none
                     focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50
                     transition-all duration-200"
          />
          <p className="text-xs text-gray-500">
            Be specific about styles, colors, feelings, and references you like.
          </p>
        </div>

        {/* Inspiration Section */}
        <div className="space-y-3">
          <label className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-sm font-medium text-gray-300">
              <Sparkles className="w-4 h-4 text-pink-400" />
              Inspiration ({inspirations.length}/5)
            </span>
            {canAddMore && (
              <span className="text-xs text-gray-500">Images or URLs</span>
            )}
          </label>

          {/* Existing Inspirations */}
          <AnimatePresence>
            {inspirations.map((inspiration) => (
              <motion.div
                key={inspiration.id}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="group relative flex gap-3 p-3 rounded-xl bg-gray-800/30 border border-gray-700/50"
              >
                {/* Preview */}
                <div className="w-20 h-20 flex-shrink-0 rounded-lg overflow-hidden bg-gray-800">
                  {inspiration.type === 'image' && inspiration.preview_url ? (
                    <img 
                      src={inspiration.preview_url} 
                      alt="Inspiration"
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Link2 className="w-6 h-6 text-gray-500" />
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  {inspiration.type === 'url' && (
                    <div className="flex items-center gap-2 mb-2">
                      <a 
                        href={inspiration.data}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-purple-400 hover:text-purple-300 truncate flex items-center gap-1"
                      >
                        {inspiration.data}
                        <ExternalLink className="w-3 h-3 flex-shrink-0" />
                      </a>
                    </div>
                  )}
                  
                  {editingId === inspiration.id ? (
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={inspiration.notes}
                        onChange={(e) => handleUpdateNote(inspiration.id, e.target.value)}
                        placeholder="Add notes about this inspiration..."
                        className="flex-1 px-3 py-1.5 text-sm rounded-lg bg-gray-700/50 border border-gray-600/50 
                                 text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-purple-500/50"
                        autoFocus
                        onBlur={() => setEditingId(null)}
                        onKeyDown={(e) => e.key === 'Enter' && setEditingId(null)}
                      />
                    </div>
                  ) : (
                    <button
                      onClick={() => setEditingId(inspiration.id)}
                      className="text-sm text-gray-400 hover:text-gray-300 text-left"
                    >
                      {inspiration.notes || 'Click to add notes...'}
                    </button>
                  )}
                </div>

                {/* Delete */}
                <button
                  onClick={() => removeInspiration(inspiration.id)}
                  className="absolute top-2 right-2 p-1.5 rounded-lg bg-gray-700/50 text-gray-400 
                           hover:text-red-400 hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Add Inspiration */}
          {canAddMore && (
            <div className="grid grid-cols-2 gap-3">
              {/* Upload Image */}
              <label className="flex flex-col items-center justify-center gap-2 p-4 rounded-xl 
                              border-2 border-dashed border-gray-700/50 bg-gray-800/20
                              hover:border-purple-500/50 hover:bg-purple-500/5
                              cursor-pointer transition-all duration-200">
                <Upload className="w-6 h-6 text-gray-500" />
                <span className="text-sm text-gray-400">Upload Image</span>
                <input
                  type="file"
                  accept="image/*"
                  multiple
                  onChange={handleImageUpload}
                  className="hidden"
                />
              </label>

              {/* Add URL */}
              <div className="flex flex-col gap-2">
                <input
                  type="url"
                  value={inspirationUrl}
                  onChange={(e) => setInspirationUrl(e.target.value)}
                  placeholder="Paste inspiration URL..."
                  className="w-full px-3 py-2 text-sm rounded-lg bg-gray-800/50 border border-gray-700/50 
                           text-white placeholder:text-gray-500 focus:outline-none focus:ring-1 focus:ring-purple-500/50"
                />
                {inspirationUrl && (
                  <motion.button
                    initial={{ opacity: 0, y: -5 }}
                    animate={{ opacity: 1, y: 0 }}
                    onClick={handleAddUrl}
                    className="flex items-center justify-center gap-2 px-3 py-2 rounded-lg 
                             bg-purple-500/20 text-purple-300 text-sm
                             hover:bg-purple-500/30 transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    Add URL
                  </motion.button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="px-6 py-4 border-t border-gray-800/50 bg-gray-900/50 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <button
            onClick={onSkip}
            className="px-4 py-2.5 rounded-xl text-gray-400 hover:text-gray-300 
                     hover:bg-gray-800/50 transition-colors text-sm font-medium"
          >
            Skip Research
          </button>
          
          <div className="flex-1" />
          
          <motion.button
            onClick={handleSubmit}
            disabled={!canSubmit || isLoading}
            whileHover={canSubmit && !isLoading ? { scale: 1.02 } : {}}
            whileTap={canSubmit && !isLoading ? { scale: 0.98 } : {}}
            className={`
              flex items-center gap-2 px-6 py-2.5 rounded-xl font-medium text-sm
              transition-all duration-200
              ${canSubmit && !isLoading
                ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white shadow-lg shadow-purple-500/25 hover:shadow-xl hover:shadow-purple-500/30'
                : 'bg-gray-800 text-gray-500 cursor-not-allowed'
              }
            `}
          >
            {isLoading ? (
              <>
                <Zap className="w-4 h-4 animate-pulse" />
                Starting...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Start Research
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </motion.button>
        </div>
      </div>
    </div>
  );
}

