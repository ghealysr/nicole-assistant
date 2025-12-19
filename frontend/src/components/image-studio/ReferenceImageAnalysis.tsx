"use client";

/**
 * Reference Image Analysis Component
 * 
 * Displays Claude Vision analysis of reference images with expandable details.
 * Shows style, composition, colors, mood, and subject analysis.
 * 
 * Quality Standard: Anthropic Engineer Level
 */

import React, { useState } from "react";
import { ChevronDown, ChevronUp, Palette, Layout, Sparkles, Camera, Tag } from "lucide-react";

// ============================================================================
// Types
// ============================================================================

interface ColorPalette {
  dominant_colors: string[];
  color_harmony: string;
  temperature: string;
  saturation_level: string;
}

interface CompositionAnalysis {
  layout_type: string;
  focal_points: string[];
  depth: string;
  perspective: string;
  balance: string;
}

interface StyleAnalysis {
  primary_style: string;
  secondary_styles: string[];
  art_movement?: string;
  medium: string;
  technical_approach: string;
}

interface MoodAnalysis {
  primary_mood: string;
  atmosphere: string;
  energy_level: string;
  emotional_tone: string[];
}

interface SubjectAnalysis {
  main_subjects: string[];
  environment?: string;
  time_of_day?: string;
  season?: string;
  notable_elements: string[];
}

interface VisionAnalysisResult {
  image_id: string;
  style: StyleAnalysis;
  composition: CompositionAnalysis;
  colors: ColorPalette;
  mood: MoodAnalysis;
  subject: SubjectAnalysis;
  prompt_suggestions: string[];
  technical_notes: string[];
}

interface MultiImageAnalysis {
  individual_analyses: VisionAnalysisResult[];
  common_themes: string[];
  unified_style_guidance: string;
  combined_prompt_enhancement: string;
  consistency_notes: string[];
}

interface ReferenceImageAnalysisProps {
  analysis: VisionAnalysisResult | MultiImageAnalysis;
  analysisType: "single" | "multi";
  onApplySuggestion?: (suggestion: string) => void;
}

// ============================================================================
// Color Swatch Component
// ============================================================================

const ColorSwatch: React.FC<{ color: string }> = ({ color }) => {
  return (
    <div className="flex items-center gap-2">
      <div
        className="w-8 h-8 rounded border border-white/20 shadow-sm"
        style={{ backgroundColor: color }}
      />
      <span className="text-xs font-mono text-white/70">{color}</span>
    </div>
  );
};

// ============================================================================
// Collapsible Section Component
// ============================================================================

const CollapsibleSection: React.FC<{
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}> = ({ title, icon, children, defaultOpen = false }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border border-white/10 rounded-lg overflow-hidden bg-white/5">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="font-medium text-white">{title}</span>
        </div>
        {isOpen ? (
          <ChevronUp className="w-4 h-4 text-white/60" />
        ) : (
          <ChevronDown className="w-4 h-4 text-white/60" />
        )}
      </button>
      {isOpen && <div className="px-4 py-3 border-t border-white/10">{children}</div>}
    </div>
  );
};

// ============================================================================
// Single Analysis Component
// ============================================================================

const SingleAnalysisView: React.FC<{
  analysis: VisionAnalysisResult;
  onApplySuggestion?: (suggestion: string) => void;
}> = ({ analysis, onApplySuggestion }) => {
  return (
    <div className="space-y-3">
      {/* Style Analysis */}
      <CollapsibleSection
        title="Style Analysis"
        icon={<Sparkles className="w-4 h-4 text-purple-400" />}
        defaultOpen
      >
        <div className="space-y-2 text-sm">
          <div>
            <span className="text-white/60">Primary Style: </span>
            <span className="text-white font-medium">{analysis.style.primary_style}</span>
          </div>
          <div>
            <span className="text-white/60">Medium: </span>
            <span className="text-white">{analysis.style.medium}</span>
          </div>
          <div>
            <span className="text-white/60">Technical Approach: </span>
            <span className="text-white">{analysis.style.technical_approach}</span>
          </div>
          {analysis.style.secondary_styles.length > 0 && (
            <div>
              <span className="text-white/60">Secondary Styles: </span>
              <div className="flex flex-wrap gap-1 mt-1">
                {analysis.style.secondary_styles.map((style, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-purple-500/20 text-purple-200 rounded text-xs"
                  >
                    {style}
                  </span>
                ))}
              </div>
            </div>
          )}
          {analysis.style.art_movement && (
            <div>
              <span className="text-white/60">Art Movement: </span>
              <span className="text-white">{analysis.style.art_movement}</span>
            </div>
          )}
        </div>
      </CollapsibleSection>

      {/* Color Palette */}
      <CollapsibleSection
        title="Color Palette"
        icon={<Palette className="w-4 h-4 text-pink-400" />}
        defaultOpen
      >
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {analysis.colors.dominant_colors.map((color, idx) => (
              <ColorSwatch key={idx} color={color} />
            ))}
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-white/60">Harmony: </span>
              <span className="text-white">{analysis.colors.color_harmony}</span>
            </div>
            <div>
              <span className="text-white/60">Temperature: </span>
              <span className="text-white">{analysis.colors.temperature}</span>
            </div>
            <div>
              <span className="text-white/60">Saturation: </span>
              <span className="text-white">{analysis.colors.saturation_level}</span>
            </div>
          </div>
        </div>
      </CollapsibleSection>

      {/* Composition */}
      <CollapsibleSection title="Composition" icon={<Layout className="w-4 h-4 text-blue-400" />}>
        <div className="space-y-2 text-sm">
          <div>
            <span className="text-white/60">Layout: </span>
            <span className="text-white">{analysis.composition.layout_type}</span>
          </div>
          <div>
            <span className="text-white/60">Perspective: </span>
            <span className="text-white">{analysis.composition.perspective}</span>
          </div>
          <div>
            <span className="text-white/60">Depth: </span>
            <span className="text-white">{analysis.composition.depth}</span>
          </div>
          <div>
            <span className="text-white/60">Balance: </span>
            <span className="text-white">{analysis.composition.balance}</span>
          </div>
          {analysis.composition.focal_points.length > 0 && (
            <div>
              <span className="text-white/60 block mb-1">Focal Points:</span>
              <ul className="list-disc list-inside space-y-1 text-white/80">
                {analysis.composition.focal_points.map((point, idx) => (
                  <li key={idx}>{point}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </CollapsibleSection>

      {/* Mood & Atmosphere */}
      <CollapsibleSection title="Mood & Atmosphere" icon={<Sparkles className="w-4 h-4 text-amber-400" />}>
        <div className="space-y-2 text-sm">
          <div>
            <span className="text-white/60">Primary Mood: </span>
            <span className="text-white font-medium">{analysis.mood.primary_mood}</span>
          </div>
          <div>
            <span className="text-white/60">Atmosphere: </span>
            <span className="text-white">{analysis.mood.atmosphere}</span>
          </div>
          <div>
            <span className="text-white/60">Energy Level: </span>
            <span className="text-white">{analysis.mood.energy_level}</span>
          </div>
          {analysis.mood.emotional_tone.length > 0 && (
            <div>
              <span className="text-white/60 block mb-1">Emotional Tone:</span>
              <div className="flex flex-wrap gap-1">
                {analysis.mood.emotional_tone.map((tone, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-amber-500/20 text-amber-200 rounded text-xs"
                  >
                    {tone}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </CollapsibleSection>

      {/* Subject Matter */}
      <CollapsibleSection title="Subject Matter" icon={<Camera className="w-4 h-4 text-green-400" />}>
        <div className="space-y-2 text-sm">
          {analysis.subject.main_subjects.length > 0 && (
            <div>
              <span className="text-white/60 block mb-1">Main Subjects:</span>
              <div className="flex flex-wrap gap-1">
                {analysis.subject.main_subjects.map((subject, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-green-500/20 text-green-200 rounded text-xs"
                  >
                    {subject}
                  </span>
                ))}
              </div>
            </div>
          )}
          {analysis.subject.environment && (
            <div>
              <span className="text-white/60">Environment: </span>
              <span className="text-white">{analysis.subject.environment}</span>
            </div>
          )}
          {analysis.subject.time_of_day && (
            <div>
              <span className="text-white/60">Time of Day: </span>
              <span className="text-white">{analysis.subject.time_of_day}</span>
            </div>
          )}
          {analysis.subject.season && (
            <div>
              <span className="text-white/60">Season: </span>
              <span className="text-white">{analysis.subject.season}</span>
            </div>
          )}
          {analysis.subject.notable_elements.length > 0 && (
            <div>
              <span className="text-white/60 block mb-1">Notable Elements:</span>
              <ul className="list-disc list-inside space-y-1 text-white/80">
                {analysis.subject.notable_elements.map((element, idx) => (
                  <li key={idx}>{element}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </CollapsibleSection>

      {/* Prompt Suggestions */}
      {analysis.prompt_suggestions.length > 0 && (
        <CollapsibleSection title="Prompt Suggestions" icon={<Tag className="w-4 h-4 text-cyan-400" />}>
          <div className="space-y-2">
            {analysis.prompt_suggestions.map((suggestion, idx) => (
              <button
                key={idx}
                onClick={() => onApplySuggestion?.(suggestion)}
                className="w-full text-left p-3 bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/30 rounded-lg text-sm text-white transition-colors group"
              >
                <span className="block group-hover:text-cyan-200">{suggestion}</span>
                <span className="text-xs text-cyan-400/60 block mt-1">Click to add to prompt</span>
              </button>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Technical Notes */}
      {analysis.technical_notes.length > 0 && (
        <CollapsibleSection title="Technical Notes" icon={<Camera className="w-4 h-4 text-gray-400" />}>
          <ul className="space-y-2 text-sm text-white/80">
            {analysis.technical_notes.map((note, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-gray-400 mt-1">•</span>
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </CollapsibleSection>
      )}
    </div>
  );
};

// ============================================================================
// Multi Analysis Component
// ============================================================================

const MultiAnalysisView: React.FC<{
  analysis: MultiImageAnalysis;
  onApplySuggestion?: (suggestion: string) => void;
}> = ({ analysis, onApplySuggestion }) => {
  const [selectedImageIndex, setSelectedImageIndex] = useState<number | null>(null);

  return (
    <div className="space-y-4">
      {/* Unified Guidance */}
      <div className="p-4 bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/30 rounded-lg">
        <h3 className="text-white font-semibold mb-2 flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-purple-400" />
          Unified Style Guidance
        </h3>
        <p className="text-white/80 text-sm leading-relaxed">{analysis.unified_style_guidance}</p>
      </div>

      {/* Combined Enhancement */}
      <div className="p-4 bg-cyan-500/10 border border-cyan-500/30 rounded-lg">
        <h3 className="text-white font-semibold mb-2 flex items-center gap-2">
          <Tag className="w-4 h-4 text-cyan-400" />
          Combined Prompt Enhancement
        </h3>
        <p className="text-white/80 text-sm leading-relaxed mb-3">
          {analysis.combined_prompt_enhancement}
        </p>
        <button
          onClick={() => onApplySuggestion?.(analysis.combined_prompt_enhancement)}
          className="px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/40 rounded-lg text-cyan-200 text-sm transition-colors"
        >
          Apply to Prompt
        </button>
      </div>

      {/* Common Themes */}
      {analysis.common_themes.length > 0 && (
        <div>
          <h3 className="text-white font-semibold mb-2 flex items-center gap-2">
            <Layout className="w-4 h-4 text-blue-400" />
            Common Themes
          </h3>
          <div className="flex flex-wrap gap-2">
            {analysis.common_themes.map((theme, idx) => (
              <span key={idx} className="px-3 py-1 bg-blue-500/20 text-blue-200 rounded-full text-sm">
                {theme}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Consistency Notes */}
      {analysis.consistency_notes.length > 0 && (
        <div>
          <h3 className="text-white font-semibold mb-2">Consistency Notes</h3>
          <ul className="space-y-2 text-sm text-white/80">
            {analysis.consistency_notes.map((note, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-purple-400 mt-1">•</span>
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Individual Analyses */}
      <div>
        <h3 className="text-white font-semibold mb-3">Individual Image Analyses</h3>
        <div className="space-y-2">
          {analysis.individual_analyses.map((imgAnalysis, idx) => (
            <div key={imgAnalysis.image_id} className="border border-white/10 rounded-lg overflow-hidden">
              <button
                onClick={() => setSelectedImageIndex(selectedImageIndex === idx ? null : idx)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-gradient-to-br from-purple-500/30 to-pink-500/30 rounded flex items-center justify-center">
                    <span className="text-white font-semibold">{idx + 1}</span>
                  </div>
                  <div className="text-left">
                    <div className="text-white font-medium">{imgAnalysis.image_id}</div>
                    <div className="text-white/60 text-xs">{imgAnalysis.style.primary_style}</div>
                  </div>
                </div>
                {selectedImageIndex === idx ? (
                  <ChevronUp className="w-4 h-4 text-white/60" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-white/60" />
                )}
              </button>
              {selectedImageIndex === idx && (
                <div className="px-4 py-4 border-t border-white/10">
                  <SingleAnalysisView analysis={imgAnalysis} onApplySuggestion={onApplySuggestion} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// Main Component
// ============================================================================

export const ReferenceImageAnalysis: React.FC<ReferenceImageAnalysisProps> = ({
  analysis,
  analysisType,
  onApplySuggestion,
}) => {
  return (
    <div className="p-4 bg-gradient-to-b from-[#1a1625] to-[#0f0b14] rounded-lg border border-purple-500/20">
      <div className="mb-4">
        <h2 className="text-xl font-bold text-white flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-purple-400" />
          Claude Vision Analysis
        </h2>
        <p className="text-white/60 text-sm mt-1">
          {analysisType === "single"
            ? "Detailed analysis of your reference image"
            : `Analysis of ${
                "individual_analyses" in analysis ? analysis.individual_analyses.length : 0
              } reference images`}
        </p>
      </div>

      {analysisType === "single" ? (
        <SingleAnalysisView
          analysis={analysis as VisionAnalysisResult}
          onApplySuggestion={onApplySuggestion}
        />
      ) : (
        <MultiAnalysisView
          analysis={analysis as MultiImageAnalysis}
          onApplySuggestion={onApplySuggestion}
        />
      )}
    </div>
  );
};

export default ReferenceImageAnalysis;

