'use client';

/**
 * ResearchArticle - Template-based research presentation
 * 
 * Automatically selects from 5 editorial templates based on content analysis:
 * 1. Immersive Longform - Mrs. Healy - Kinfolk meets The New Yorker
 * 2. Bento Intelligence Brief - Pasta Fazool - Bloomberg meets dashboard
 * 3. Editorial Scrapbook - Purpchicka - Handmade collage aesthetic
 * 4. Magazine Spread - Nicole - Print editorial for digital
 * 5. Narrative Timeline - nhealy44 - Scrollytelling documentary
 * 
 * Template selection is intelligent (based on content characteristics)
 * with randomization when scores are close for variety.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { ResearchResponse } from '@/lib/hooks/useResearch';
import {
  TemplateId,
  TEMPLATES,
  selectTemplate,
  getRandomTemplate,
} from './templates';
import { ImmersiveLongform } from './templates/ImmersiveLongform';
import { BentoBrief } from './templates/BentoBrief';
import { EditorialScrapbook } from './templates/EditorialScrapbook';
import { MagazineSpread } from './templates/MagazineSpread';
import { NarrativeTimeline } from './templates/NarrativeTimeline';

interface ResearchArticleProps {
  data: ResearchResponse;
  /** Force a specific template instead of auto-selection */
  templateOverride?: TemplateId;
  /** Show template selector UI */
  showTemplateSelector?: boolean;
}

// Track last used template for variety
let lastUsedTemplate: TemplateId | undefined;

export function ResearchArticle({ 
  data, 
  templateOverride,
  showTemplateSelector = false,
}: ResearchArticleProps) {
  // Memoize template selection to prevent recalculation on every render
  const autoSelectedTemplate = useMemo(() => {
    const selected = selectTemplate(data, lastUsedTemplate);
    lastUsedTemplate = selected;
    return selected;
  }, [data]);

  const [currentTemplate, setCurrentTemplate] = useState<TemplateId>(
    templateOverride || autoSelectedTemplate
  );

  // Update when override changes
  useEffect(() => {
    if (templateOverride) {
      setCurrentTemplate(templateOverride);
    }
  }, [templateOverride]);

  // Randomize template (for shuffle button)
  const randomizeTemplate = useCallback(() => {
    const newTemplate = getRandomTemplate(currentTemplate);
    setCurrentTemplate(newTemplate);
  }, [currentTemplate]);

  // Get current template info
  const templateInfo = TEMPLATES[currentTemplate];

  // Render the selected template
  const renderTemplate = () => {
    switch (currentTemplate) {
      case 'immersive-longform':
        return <ImmersiveLongform data={data} />;
      case 'bento-brief':
        return <BentoBrief data={data} />;
      case 'editorial-scrapbook':
        return <EditorialScrapbook data={data} />;
      case 'magazine-spread':
        return <MagazineSpread data={data} />;
      case 'narrative-timeline':
        return <NarrativeTimeline data={data} />;
      default:
        return <ImmersiveLongform data={data} />;
    }
  };

  return (
    <div style={{ position: 'relative' }}>
      {/* Template selector UI (optional) */}
      {showTemplateSelector && (
        <div
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 50,
            background: 'rgba(255,255,255,0.95)',
            backdropFilter: 'blur(8px)',
            borderBottom: '1px solid #e5e5e5',
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
          }}
        >
          {/* Current template info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span
              style={{
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                color: '#999',
              }}
            >
              Template:
            </span>
            <span
              style={{
                fontSize: '13px',
                fontWeight: 500,
                color: '#333',
              }}
            >
              {templateInfo.name}
            </span>
            <span
              style={{
                fontSize: '11px',
                color: '#8B5CF6',
                fontStyle: 'italic',
              }}
            >
              by {templateInfo.author}
            </span>
          </div>

          {/* Template buttons */}
          <div style={{ display: 'flex', gap: '8px' }}>
            {/* Shuffle button */}
            <button
              onClick={randomizeTemplate}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 12px',
                background: '#f5f5f5',
                border: '1px solid #e5e5e5',
                borderRadius: '6px',
                fontSize: '12px',
                cursor: 'pointer',
                color: '#666',
              }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="16 3 21 3 21 8" />
                <line x1="4" y1="20" x2="21" y2="3" />
                <polyline points="21 16 21 21 16 21" />
                <line x1="15" y1="15" x2="21" y2="21" />
                <line x1="4" y1="4" x2="9" y2="9" />
              </svg>
              Shuffle
            </button>

            {/* Template dropdown */}
            <select
              value={currentTemplate}
              onChange={(e) => setCurrentTemplate(e.target.value as TemplateId)}
              style={{
                padding: '6px 12px',
                background: '#fff',
                border: '1px solid #e5e5e5',
                borderRadius: '6px',
                fontSize: '12px',
                cursor: 'pointer',
                color: '#333',
              }}
            >
              {Object.entries(TEMPLATES).map(([id, info]) => (
                <option key={id} value={id}>
                  {info.name} — {info.author}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Render the template */}
      <div style={{ borderRadius: '12px', overflow: 'hidden' }}>
        {renderTemplate()}
      </div>
    </div>
  );
}

export default ResearchArticle;
