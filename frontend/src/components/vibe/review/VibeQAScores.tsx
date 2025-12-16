import React from 'react';
import { CheckCircle, AlertTriangle } from 'lucide-react';

export interface QAScores {
  lighthouse: {
    performance: number;
    accessibility: number;
    best_practices: number;
    seo: number;
  };
  accessibility: {
    violations: number;
    warnings: number;
    passes: number;
  };
  all_passing: boolean;
}

interface VibeQAScoresProps {
  scores: QAScores | null;
  loading?: boolean;
}

/**
 * Transforms raw API data to QAScores format
 */
export function transformToQAScores(data: Record<string, unknown> | null): QAScores | null {
  if (!data) return null;
  
  return {
    lighthouse: {
      performance: (data.lighthouse_performance as number) || 0,
      accessibility: (data.lighthouse_accessibility as number) || 0,
      best_practices: (data.lighthouse_best_practices as number) || 0,
      seo: (data.lighthouse_seo as number) || 0,
    },
    accessibility: {
      violations: (data.accessibility_violations as number) || 0,
      warnings: (data.accessibility_warnings as number) || 0,
      passes: (data.accessibility_passes as number) || 0,
    },
    all_passing: (data.all_passing as boolean) || false,
  };
}

function ScoreCircle({ score, label }: { score: number; label: string }) {
  const getColor = (s: number) => {
    if (s >= 90) return 'text-green-500 border-green-500';
    if (s >= 50) return 'text-yellow-500 border-yellow-500';
    return 'text-red-500 border-red-500';
  };

  return (
    <div className="flex flex-col items-center">
      <div className={`w-16 h-16 rounded-full border-4 flex items-center justify-center text-xl font-bold mb-2 ${getColor(score)}`}>
        {score}
      </div>
      <span className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</span>
    </div>
  );
}

export function VibeQAScores({ scores, loading }: VibeQAScoresProps) {
  if (loading) return <div className="p-4 text-center text-gray-500">Loading scores...</div>;
  if (!scores) return null;

  return (
    <div className="vibe-qa-scores bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="flex justify-between items-center mb-6">
        <h3 className="font-bold text-gray-900">Quality Assurance</h3>
        <div className={`px-3 py-1 rounded-full text-sm font-medium flex items-center ${scores.all_passing ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
          {scores.all_passing ? (
            <><CheckCircle size={16} className="mr-1.5" /> Passing</>
          ) : (
            <><AlertTriangle size={16} className="mr-1.5" /> Attention Needed</>
          )}
        </div>
      </div>

      {/* Lighthouse Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
        <ScoreCircle score={scores.lighthouse.performance || 0} label="Performance" />
        <ScoreCircle score={scores.lighthouse.accessibility || 0} label="Accessibility" />
        <ScoreCircle score={scores.lighthouse.best_practices || 0} label="Best Practices" />
        <ScoreCircle score={scores.lighthouse.seo || 0} label="SEO" />
      </div>

      {/* Deep Dive Metrics */}
      <div className="border-t border-gray-100 pt-4">
        <h4 className="text-sm font-semibold text-gray-800 mb-3">Accessibility Details (axe-core)</h4>
        <div className="grid grid-cols-3 gap-4">
          <div className="p-3 bg-red-50 rounded-lg border border-red-100 text-center">
            <span className="block text-2xl font-bold text-red-600">{scores.accessibility.violations}</span>
            <span className="text-xs text-red-800">Violations</span>
          </div>
          <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-100 text-center">
            <span className="block text-2xl font-bold text-yellow-600">{scores.accessibility.warnings}</span>
            <span className="text-xs text-yellow-800">Warnings</span>
          </div>
          <div className="p-3 bg-green-50 rounded-lg border border-green-100 text-center">
            <span className="block text-2xl font-bold text-green-600">{scores.accessibility.passes}</span>
            <span className="text-xs text-green-800">Passes</span>
          </div>
        </div>
      </div>
    </div>
  );
}

