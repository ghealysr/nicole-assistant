import React, { useState, useEffect } from 'react';
import { useVibeProject } from '@/lib/hooks/useVibeProject';
import { VibeQAScores, QAScores, transformToQAScores } from './VibeQAScores';
import { VibeFeedbackInput } from './VibeFeedbackInput';
import { VibeIterationHistory } from './VibeIterationHistory';
import { VibeScreenshots } from './VibeScreenshots';
import { RefreshCw, ExternalLink } from 'lucide-react';

interface VibeGlenReviewProps {
  projectId: number;
}

export function VibeGlenReview({ projectId }: VibeGlenReviewProps) {
  const { project, getIterations, getQAScores } = useVibeProject();
  const [iterations, setIterations] = useState<Array<Record<string, unknown>>>([]);
  const [rawQAData, setRawQAData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  
  // Transform raw data to typed QAScores
  const qaScores: QAScores | null = transformToQAScores(rawQAData);

  // Fetch data
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      const [iterData, qaData] = await Promise.all([
        getIterations(projectId),
        getQAScores(projectId)
      ]);
      setIterations(iterData);
      setRawQAData(qaData);
      setLoading(false);
    };
    loadData();
  }, [projectId, getIterations, getQAScores, refreshKey]);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  const handleLightbox = (url: string, desc: string) => {
    // Dispatch custom event for main layout to handle lightbox
    // Alternatively, lift lightbox state up if this was fully integrated
    const event = new CustomEvent('vibe-lightbox-open', { detail: { url, desc } });
    window.dispatchEvent(event);
  };

  return (
    <div className="vibe-glen-review h-full flex flex-col bg-gray-50 overflow-y-auto">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center sticky top-0 z-10">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Review & QA Control</h2>
          <p className="text-sm text-gray-500">
            Project: {project?.name} • Iteration #{project?.iteration_count || 0}
          </p>
        </div>
        <div className="flex space-x-3">
          <button 
            onClick={handleRefresh}
            className="p-2 text-gray-500 hover:text-gray-900 bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
            title="Refresh Data"
          >
            <RefreshCw size={18} />
          </button>
          {project?.preview_url && (
            <a 
              href={project.preview_url}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-50 flex items-center shadow-sm"
            >
              <ExternalLink size={16} className="mr-2" />
              Open Deployment
            </a>
          )}
        </div>
      </div>

      <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Visuals */}
        <div className="lg:col-span-2 space-y-6">
          {/* Screenshots */}
          <section>
            <h3 className="text-lg font-semibold text-gray-800 mb-3">Device Preview</h3>
            <VibeScreenshots 
              screenshots={{
                mobile: rawQAData?.screenshot_mobile as string | undefined,
                tablet: rawQAData?.screenshot_tablet as string | undefined,
                desktop: rawQAData?.screenshot_desktop as string | undefined
              }}
              onOpenLightbox={handleLightbox}
            />
          </section>

          {/* QA Scores */}
          <section>
            <VibeQAScores scores={qaScores} loading={loading} />
          </section>
        </div>

        {/* Right Column: Feedback Loop */}
        <div className="space-y-6">
          {/* Feedback Input */}
          <section>
            <VibeFeedbackInput projectId={projectId} onSubmitted={handleRefresh} />
          </section>

          {/* History */}
          <section>
            <VibeIterationHistory 
              iterations={iterations} 
              currentIteration={project?.iteration_count || 0} 
            />
          </section>
        </div>
      </div>
    </div>
  );
}

