"use client";

/**
 * Nicole's Prompt Suggestions Component
 * 
 * Displays Nicole's warm, intelligent suggestions for improving image generation prompts.
 * Interactive UI with selectable suggestions and quality scoring.
 * 
 * Quality Standard: Anthropic Engineer Level
 */

import React, { useState } from "react";
import Image from "next/image";
import { CheckCircle2, Circle, Sparkles, Star, TrendingUp, Palette, Camera, Zap, X } from "lucide-react";

// ============================================================================
// Types
// ============================================================================

interface PromptSuggestion {
  type: "specificity" | "style" | "technical" | "composition" | "lighting" | "color";
  title: string;
  description: string;
  enhanced_prompt: string;
  reasoning: string;
  priority: number; // 1-5
}

interface PromptAnalysis {
  original_prompt: string;
  analysis_summary: string;
  strengths: string[];
  weaknesses: string[];
  suggestions: PromptSuggestion[];
  overall_quality_score: number; // 1-10
}

interface NicolePromptSuggestionsProps {
  analysis: PromptAnalysis;
  onApplySuggestions: (suggestions: PromptSuggestion[]) => void;
  onClose?: () => void;
}

// ============================================================================
// Helper Functions
// ============================================================================

const getSuggestionIcon = (type: string) => {
  switch (type) {
    case "specificity":
      return <TrendingUp className="w-4 h-4" />;
    case "style":
      return <Palette className="w-4 h-4" />;
    case "technical":
      return <Camera className="w-4 h-4" />;
    case "composition":
      return <Sparkles className="w-4 h-4" />;
    case "lighting":
      return <Zap className="w-4 h-4" />;
    case "color":
      return <Palette className="w-4 h-4" />;
    default:
      return <Sparkles className="w-4 h-4" />;
  }
};

const getSuggestionColor = (type: string): string => {
  const colors = {
    specificity: "blue",
    style: "purple",
    technical: "cyan",
    composition: "green",
    lighting: "amber",
    color: "pink",
  };
  return colors[type as keyof typeof colors] || "purple";
};

const getPriorityBadge = (priority: number) => {
  const config = {
    5: { label: "Critical", color: "red" },
    4: { label: "High", color: "orange" },
    3: { label: "Medium", color: "yellow" },
    2: { label: "Low", color: "blue" },
    1: { label: "Optional", color: "gray" },
  };
  
  const { label, color } = config[priority as keyof typeof config] || config[3];
  
  return (
    <span className={`px-2 py-0.5 bg-${color}-500/20 text-${color}-300 text-xs rounded-full`}>
      {label}
    </span>
  );
};

const getQualityScoreColor = (score: number): string => {
  if (score >= 8) return "green";
  if (score >= 6) return "yellow";
  if (score >= 4) return "orange";
  return "red";
};

// ============================================================================
// Main Component
// ============================================================================

export const NicolePromptSuggestions: React.FC<NicolePromptSuggestionsProps> = ({
  analysis,
  onApplySuggestions,
  onClose,
}) => {
  const [selectedSuggestions, setSelectedSuggestions] = useState<Set<number>>(new Set());
  
  const toggleSuggestion = (index: number) => {
    const newSelected = new Set(selectedSuggestions);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedSuggestions(newSelected);
  };
  
  const selectAll = () => {
    const allIndices = analysis.suggestions.map((_, idx) => idx);
    setSelectedSuggestions(new Set(allIndices));
  };
  
  const clearAll = () => {
    setSelectedSuggestions(new Set());
  };
  
  const applySelected = () => {
    const selected = analysis.suggestions.filter((_, idx) => selectedSuggestions.has(idx));
    onApplySuggestions(selected);
  };
  
  const qualityColor = getQualityScoreColor(analysis.overall_quality_score);
  
  return (
    <div className="p-6 bg-gradient-to-b from-[#1a1625] to-[#0f0b14] rounded-lg border border-purple-500/20">
      {/* Header with Nicole's Avatar */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-start gap-4">
          <div className="relative w-16 h-16 rounded-full overflow-hidden border-2 border-purple-400/30 flex-shrink-0">
            <Image
              src="/images/nicole-thinking-avatar.png"
              alt="Nicole"
              fill
              className="object-cover"
            />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <h2 className="text-xl font-bold text-white">Nicole&apos;s Suggestions</h2>
              <Sparkles className="w-5 h-5 text-purple-400" />
            </div>
            <p className="text-white/80 text-sm leading-relaxed">{analysis.analysis_summary}</p>
          </div>
        </div>
        
        {onClose && (
          <button
            onClick={onClose}
            className="text-white/60 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>
      
      {/* Quality Score */}
      <div className="mb-6 p-4 bg-white/5 rounded-lg border border-white/10">
        <div className="flex items-center justify-between">
          <span className="text-white/80 text-sm font-medium">Prompt Quality Score</span>
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              {[...Array(10)].map((_, i) => (
                <Star
                  key={i}
                  className={`w-4 h-4 ${
                    i < analysis.overall_quality_score
                      ? `text-${qualityColor}-400 fill-${qualityColor}-400`
                      : "text-white/20"
                  }`}
                />
              ))}
            </div>
            <span className={`text-${qualityColor}-400 font-bold text-lg`}>
              {analysis.overall_quality_score}/10
            </span>
          </div>
        </div>
      </div>
      
      {/* Strengths & Weaknesses */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        {/* Strengths */}
        {analysis.strengths.length > 0 && (
          <div className="p-4 bg-green-500/10 rounded-lg border border-green-500/30">
            <h3 className="text-green-300 font-semibold mb-2 text-sm flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              What&apos;s Already Great
            </h3>
            <ul className="space-y-1 text-xs text-green-200/80">
              {analysis.strengths.map((strength, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-green-400 mt-0.5">•</span>
                  <span>{strength}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {/* Weaknesses */}
        {analysis.weaknesses.length > 0 && (
          <div className="p-4 bg-amber-500/10 rounded-lg border border-amber-500/30">
            <h3 className="text-amber-300 font-semibold mb-2 text-sm flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Room for Improvement
            </h3>
            <ul className="space-y-1 text-xs text-amber-200/80">
              {analysis.weaknesses.map((weakness, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-amber-400 mt-0.5">•</span>
                  <span>{weakness}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      
      {/* Suggestions Section */}
      {analysis.suggestions.length > 0 && (
        <>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-white font-semibold text-sm">
              Select Suggestions to Apply ({selectedSuggestions.size} selected)
            </h3>
            <div className="flex gap-2">
              <button
                onClick={selectAll}
                className="text-xs text-purple-400 hover:text-purple-300 transition-colors"
              >
                Select All
              </button>
              <span className="text-white/30">|</span>
              <button
                onClick={clearAll}
                className="text-xs text-white/60 hover:text-white transition-colors"
              >
                Clear
              </button>
            </div>
          </div>
          
          <div className="space-y-3 mb-6">
            {analysis.suggestions.map((suggestion, idx) => {
              const isSelected = selectedSuggestions.has(idx);
              const color = getSuggestionColor(suggestion.type);
              
              return (
                <button
                  key={idx}
                  onClick={() => toggleSuggestion(idx)}
                  className={`w-full text-left p-4 rounded-lg border transition-all ${
                    isSelected
                      ? `bg-${color}-500/10 border-${color}-500/40`
                      : "bg-white/5 border-white/10 hover:bg-white/10"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {/* Selection Indicator */}
                    <div className="mt-0.5">
                      {isSelected ? (
                        <CheckCircle2 className={`w-5 h-5 text-${color}-400`} />
                      ) : (
                        <Circle className="w-5 h-5 text-white/40" />
                      )}
                    </div>
                    
                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <div className={`text-${color}-400`}>
                          {getSuggestionIcon(suggestion.type)}
                        </div>
                        <h4 className="text-white font-medium text-sm">{suggestion.title}</h4>
                        {getPriorityBadge(suggestion.priority)}
                      </div>
                      
                      <p className="text-white/70 text-xs mb-2 leading-relaxed">
                        {suggestion.description}
                      </p>
                      
                      <div className="p-2 bg-black/30 rounded border border-white/10 mb-2">
                        <p className={`text-${color}-300 text-xs font-mono`}>
                          &ldquo;{suggestion.enhanced_prompt}&rdquo;
                        </p>
                      </div>
                      
                      <p className="text-white/50 text-xs italic">
                        💡 {suggestion.reasoning}
                      </p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
          
          {/* Apply Button */}
          <div className="flex justify-end gap-3">
            <button
              onClick={applySelected}
              disabled={selectedSuggestions.size === 0}
              className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-purple-500/30"
            >
              <Sparkles className="w-5 h-5" />
              Apply {selectedSuggestions.size > 0 ? `${selectedSuggestions.size} ` : ""}Suggestions
            </button>
          </div>
        </>
      )}
      
      {/* No Suggestions (Perfect Prompt) */}
      {analysis.suggestions.length === 0 && (
        <div className="text-center py-8">
          <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 className="w-8 h-8 text-green-400" />
          </div>
          <h3 className="text-white font-semibold mb-2">Your Prompt Looks Great!</h3>
          <p className="text-white/70 text-sm">
            Nicole couldn&apos;t find any meaningful improvements to suggest. You&apos;re all set! 🎉
          </p>
        </div>
      )}
    </div>
  );
};

export default NicolePromptSuggestions;

