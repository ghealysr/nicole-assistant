/**
 * Muse Style Guide Preview
 * 
 * Full style guide display with colors, typography, spacing, and components.
 * User can approve to send to Nicole for coding.
 */

'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Check, 
  Palette, 
  Type, 
  Ruler,
  Box,
  Layout,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Edit3,
  Code2,
  ChevronDown,
  ChevronRight,
  Download,
  FileCode,
  FileJson,
  Loader2
} from 'lucide-react';
import type { StyleGuide, ExportFormat } from '@/lib/muse/api';
import { museApi } from '@/lib/muse/api';

interface StyleGuidePreviewProps {
  styleGuide: StyleGuide;
  projectId?: number;
  onApprove: () => void;
  onRequestChanges: (feedback: string) => void;
  isLoading?: boolean;
}

type TabId = 'colors' | 'typography' | 'spacing' | 'components';

const EXPORT_OPTIONS: { format: ExportFormat; label: string; icon: React.ReactNode; description: string }[] = [
  { 
    format: 'figma_tokens', 
    label: 'Figma Tokens', 
    icon: <FileJson className="w-4 h-4" />,
    description: 'Design tokens for Figma plugins'
  },
  { 
    format: 'css_variables', 
    label: 'CSS Variables', 
    icon: <FileCode className="w-4 h-4" />,
    description: 'CSS custom properties'
  },
  { 
    format: 'tailwind_config', 
    label: 'Tailwind Config', 
    icon: <FileCode className="w-4 h-4" />,
    description: 'Tailwind CSS configuration'
  },
  { 
    format: 'design_tokens_json', 
    label: 'W3C Design Tokens', 
    icon: <FileJson className="w-4 h-4" />,
    description: 'Standard design tokens format'
  },
];

export function StyleGuidePreview({ 
  styleGuide, 
  projectId,
  onApprove, 
  onRequestChanges,
  isLoading = false 
}: StyleGuidePreviewProps) {
  const [activeTab, setActiveTab] = useState<TabId>('colors');
  const [feedbackText, setFeedbackText] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<ExportFormat | null>(null);

  const handleExport = async (format: ExportFormat) => {
    if (!projectId) {
      console.error('No project ID for export');
      return;
    }
    
    setExportingFormat(format);
    try {
      await museApi.downloadStyleGuideExport(projectId, format);
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setExportingFormat(null);
      setShowExportMenu(false);
    }
  };

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'colors', label: 'Colors', icon: <Palette className="w-4 h-4" /> },
    { id: 'typography', label: 'Typography', icon: <Type className="w-4 h-4" /> },
    { id: 'spacing', label: 'Spacing', icon: <Ruler className="w-4 h-4" /> },
    { id: 'components', label: 'Components', icon: <Box className="w-4 h-4" /> },
  ];

  return (
    <div className="flex flex-col h-full bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950">
      {/* Header */}
      <div className="px-6 py-5 border-b border-gray-800/50 bg-gray-900/50 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Your Design System</h2>
            <p className="text-sm text-gray-400">Review and approve your generated style guide</p>
          </div>
          <div className="flex items-center gap-3">
            {/* Export Button */}
            <div className="relative">
              <button
                onClick={() => setShowExportMenu(!showExportMenu)}
                disabled={!projectId}
                className={`
                  flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium
                  transition-all duration-200
                  ${projectId 
                    ? 'text-gray-300 hover:text-white hover:bg-gray-800/50' 
                    : 'text-gray-500 cursor-not-allowed'
                  }
                `}
              >
                <Download className="w-4 h-4" />
                Export
                <ChevronDown className={`w-3 h-3 transition-transform ${showExportMenu ? 'rotate-180' : ''}`} />
              </button>

              {/* Export Dropdown */}
              <AnimatePresence>
                {showExportMenu && projectId && (
                  <motion.div
                    initial={{ opacity: 0, y: -10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: -10, scale: 0.95 }}
                    className="absolute right-0 top-full mt-2 w-64 py-2 rounded-xl 
                             bg-gray-800 border border-gray-700/50 shadow-xl z-50"
                  >
                    <div className="px-3 py-2 border-b border-gray-700/50">
                      <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">
                        Export As
                      </p>
                    </div>
                    {EXPORT_OPTIONS.map((option) => (
                      <button
                        key={option.format}
                        onClick={() => handleExport(option.format)}
                        disabled={exportingFormat === option.format}
                        className="w-full flex items-start gap-3 px-3 py-2.5 text-left
                                 hover:bg-gray-700/50 transition-colors
                                 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gray-700/50 
                                      flex items-center justify-center text-gray-300">
                          {exportingFormat === option.format ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            option.icon
                          )}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-white">{option.label}</p>
                          <p className="text-xs text-gray-500">{option.description}</p>
                        </div>
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            <span className="px-2 py-1 rounded-lg bg-purple-500/20 text-purple-300 text-xs font-medium">
              v{styleGuide.version || 1}
            </span>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mt-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                transition-all duration-200
                ${activeTab === tab.id 
                  ? 'bg-purple-500/20 text-purple-300' 
                  : 'text-gray-400 hover:text-gray-300 hover:bg-gray-800/50'
                }
              `}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <AnimatePresence mode="wait">
          {activeTab === 'colors' && (
            <motion.div
              key="colors"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-6"
            >
              <ColorSection title="Primary Colors" colors={styleGuide.colors?.primary || []} />
              <ColorSection title="Secondary Colors" colors={styleGuide.colors?.secondary || []} />
              <ColorSection title="Accent Colors" colors={styleGuide.colors?.accent || []} />
              <ColorSection title="Neutral Colors" colors={styleGuide.colors?.neutral || []} />
              <ColorSection title="Semantic Colors" colors={styleGuide.colors?.semantic || []} />
            </motion.div>
          )}

          {activeTab === 'typography' && (
            <motion.div
              key="typography"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-6"
            >
              <TypographySection typography={styleGuide.typography} />
            </motion.div>
          )}

          {activeTab === 'spacing' && (
            <motion.div
              key="spacing"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-6"
            >
              <SpacingSection spacing={styleGuide.spacing} />
            </motion.div>
          )}

          {activeTab === 'components' && (
            <motion.div
              key="components"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-6"
            >
              <ComponentsSection components={styleGuide.component_specs || {}} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Actions */}
      <div className="px-6 py-4 border-t border-gray-800/50 bg-gray-900/50 backdrop-blur-sm">
        <AnimatePresence mode="wait">
          {showFeedback ? (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-3"
            >
              <textarea
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                placeholder="Describe what changes you'd like to see..."
                className="w-full h-24 px-4 py-3 rounded-xl bg-gray-800/50 border border-gray-700/50 
                         text-white placeholder:text-gray-500 resize-none
                         focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              />
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setShowFeedback(false)}
                  className="px-4 py-2 rounded-lg text-gray-400 hover:text-gray-300 
                           hover:bg-gray-800/50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    onRequestChanges(feedbackText);
                    setFeedbackText('');
                    setShowFeedback(false);
                  }}
                  disabled={!feedbackText.trim()}
                  className="px-4 py-2 rounded-lg bg-gray-800 text-white 
                           hover:bg-gray-700 disabled:opacity-50 transition-colors"
                >
                  Request Changes
                </button>
              </div>
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-3"
            >
              <button
                onClick={() => setShowFeedback(true)}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-gray-400 
                         hover:text-gray-300 hover:bg-gray-800/50 transition-colors"
              >
                <Edit3 className="w-4 h-4" />
                Request Changes
              </button>
              
              <div className="flex-1" />
              
              <motion.button
                onClick={onApprove}
                disabled={isLoading}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl font-medium
                         bg-gradient-to-r from-green-500 to-emerald-500 text-white
                         shadow-lg shadow-green-500/25 hover:shadow-xl hover:shadow-green-500/30
                         disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    Approve & Send to Nicole
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </motion.button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

interface ColorSectionProps {
  title: string;
  colors: Array<{ name: string; hex: string; oklch?: string }>;
}

function ColorSection({ title, colors }: ColorSectionProps) {
  if (!colors.length) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-gray-300">{title}</h3>
      <div className="grid grid-cols-4 gap-3">
        {colors.map((color, i) => (
          <div key={i} className="group">
            <div 
              className="aspect-square rounded-xl border border-gray-700 mb-2 
                       group-hover:scale-105 transition-transform cursor-pointer"
              style={{ backgroundColor: color.hex }}
              title={color.oklch || color.hex}
            />
            <p className="text-sm font-medium text-white truncate">{color.name}</p>
            <p className="text-xs text-gray-500 font-mono">{color.hex}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

interface TypographySectionProps {
  typography: StyleGuide['typography'];
}

function TypographySection({ typography }: TypographySectionProps) {
  if (!typography) return null;

  const scales = typography.scale || {};
  const families = typography.families || {};

  return (
    <div className="space-y-8">
      {/* Font Families */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-gray-300">Font Families</h3>
        <div className="grid grid-cols-2 gap-4">
          {Object.entries(families).map(([key, value]) => (
            <div key={key} className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50">
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">{key}</p>
              <p className="text-2xl text-white" style={{ fontFamily: value as string }}>
                {value as string}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Type Scale */}
      <div className="space-y-4">
        <h3 className="text-sm font-medium text-gray-300">Type Scale</h3>
        <div className="space-y-3">
          {Object.entries(scales).map(([key, value]) => (
            <div key={key} className="flex items-baseline gap-4 p-3 rounded-xl bg-gray-800/30">
              <span className="text-xs text-gray-500 w-16 font-mono">{key}</span>
              <span 
                className="text-white flex-1"
                style={{ fontSize: value as string }}
              >
                The quick brown fox
              </span>
              <span className="text-xs text-gray-500 font-mono">{value as string}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface SpacingSectionProps {
  spacing: StyleGuide['spacing'];
}

function SpacingSection({ spacing }: SpacingSectionProps) {
  if (!spacing) return null;

  const scale = spacing.scale || {};
  const base = spacing.base || 8;

  return (
    <div className="space-y-6">
      <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/20">
        <p className="text-sm text-purple-300">
          <span className="font-medium">Base unit:</span> {base}px (8-point grid)
        </p>
      </div>

      <div className="space-y-3">
        {Object.entries(scale).map(([key, value]) => (
          <div key={key} className="flex items-center gap-4 p-3 rounded-xl bg-gray-800/30">
            <span className="text-xs text-gray-500 w-12 font-mono">{key}</span>
            <div 
              className="h-4 bg-gradient-to-r from-purple-500 to-pink-500 rounded"
              style={{ width: `${Math.min(Number(value), 200)}px` }}
            />
            <span className="text-xs text-gray-400 font-mono">{value}px</span>
          </div>
        ))}
      </div>
    </div>
  );
}

interface ComponentsSectionProps {
  components: Record<string, unknown>;
}

function ComponentsSection({ components }: ComponentsSectionProps) {
  const [expandedComponent, setExpandedComponent] = useState<string | null>(null);

  if (!Object.keys(components).length) {
    return (
      <div className="text-center py-12 text-gray-400">
        <Box className="w-12 h-12 mx-auto mb-3 opacity-50" />
        <p>No component specifications generated yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {Object.entries(components).map(([name, spec]) => (
        <div 
          key={name}
          className="rounded-xl bg-gray-800/30 border border-gray-700/50 overflow-hidden"
        >
          <button
            onClick={() => setExpandedComponent(expandedComponent === name ? null : name)}
            className="w-full flex items-center gap-3 p-4 text-left hover:bg-gray-800/50 transition-colors"
          >
            {expandedComponent === name ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )}
            <span className="font-medium text-white">{name}</span>
          </button>
          
          <AnimatePresence>
            {expandedComponent === name && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="border-t border-gray-700/50"
              >
                <pre className="p-4 text-sm text-gray-300 overflow-x-auto">
                  {JSON.stringify(spec, null, 2)}
                </pre>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ))}
    </div>
  );
}

