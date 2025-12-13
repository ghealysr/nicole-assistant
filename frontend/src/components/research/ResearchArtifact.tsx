'use client';

/**
 * ResearchArtifact - Magazine-style research report display
 * 
 * Features:
 * - Executive summary in gradient insight card
 * - Numbered findings with citations
 * - Nicole's synthesis section
 * - Collapsible source citations
 * - Cost and timing metadata
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ResearchResponse } from '@/lib/hooks/useResearch';

interface ResearchArtifactProps {
  data: ResearchResponse;
}

// Format date helper
const formatDate = (dateStr?: string): string => {
  if (!dateStr) return new Date().toLocaleDateString('en-US', { 
    month: 'short', day: 'numeric', year: 'numeric' 
  });
  return new Date(dateStr).toLocaleDateString('en-US', { 
    month: 'short', day: 'numeric', year: 'numeric' 
  });
};

// Estimate read time
const estimateReadTime = (findings: unknown[], recommendations: unknown[]): number => {
  const wordCount = (findings.length * 50) + (recommendations.length * 20) + 100;
  return Math.max(1, Math.ceil(wordCount / 200));
};

// Finding Card Component
const FindingCard = ({ finding, index }: { finding: ResearchResponse['findings'][0]; index: number }) => (
  <motion.div
    className="research-finding"
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ delay: index * 0.1 }}
  >
    <div className="research-finding-number">{index}</div>
    <div className="research-finding-content">
      <p>{finding.content}</p>
      {finding.source_url && (
        <a 
          href={finding.source_url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="research-finding-source"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
          {finding.source_title || 'Source'}
        </a>
      )}
    </div>
  </motion.div>
);

// Citation Component
const Citation = ({ source, index }: { source: ResearchResponse['sources'][0]; index: number }) => (
  <div className="research-citation">
    <span className="research-citation-number">[{index}]</span>
    <a 
      href={source.url} 
      target="_blank" 
      rel="noopener noreferrer"
      className="research-citation-link"
    >
      {source.title || source.url}
    </a>
  </div>
);

export function ResearchArtifact({ data }: ResearchArtifactProps) {
  const [showAllSources, setShowAllSources] = useState(false);
  const readTime = estimateReadTime(data.findings, data.recommendations);
  
  return (
    <article className="research-artifact">
      {/* Header with query as title */}
      <header className="research-artifact-header">
        <motion.div
          className="research-type-badge"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          {data.research_type === 'vibe_inspiration' && '🎨 Design Research'}
          {data.research_type === 'competitor' && '🔍 Competitor Analysis'}
          {data.research_type === 'technical' && '⚙️ Technical Research'}
          {data.research_type === 'general' && '📚 Research Report'}
        </motion.div>
        
        <motion.h1
          className="research-artifact-title"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {data.query}
        </motion.h1>
        
        <div className="research-artifact-meta">
          <span className="meta-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            {formatDate(data.completed_at)}
          </span>
          <span className="meta-separator">•</span>
          <span className="meta-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            {data.sources.length} sources
          </span>
          <span className="meta-separator">•</span>
          <span className="meta-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            {readTime} min read
          </span>
          <span className="meta-separator">•</span>
          <span className="meta-item cost">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <line x1="12" y1="1" x2="12" y2="23" />
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
            ${data.metadata.cost_usd.toFixed(3)}
          </span>
        </div>
      </header>

      {/* Key Insight Card - Executive Summary */}
      <motion.section
        className="research-insight-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <div className="research-insight-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
        </div>
        <div className="research-insight-content">
          <h2 className="research-insight-label">Key Insight</h2>
          <p className="research-insight-text">{data.executive_summary}</p>
        </div>
      </motion.section>

      {/* Findings Section */}
      {data.findings.length > 0 && (
        <section className="research-findings-section">
          <h2 className="research-section-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
            </svg>
            Findings
          </h2>
          <div className="research-findings-list">
            {data.findings.map((finding, index) => (
              <FindingCard key={index} finding={finding} index={index + 1} />
            ))}
          </div>
        </section>
      )}

      {/* Nicole's Synthesis */}
      {data.nicole_synthesis && (
        <motion.section
          className="research-nicole-section"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <div className="research-nicole-header">
            <div className="research-nicole-avatar">
              <svg viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={2} />
                <path d="M8 14s1.5 2 4 2 4-2 4-2" stroke="currentColor" strokeWidth={2} />
                <line x1="9" y1="9" x2="9.01" y2="9" stroke="currentColor" strokeWidth={3} strokeLinecap="round" />
                <line x1="15" y1="9" x2="15.01" y2="9" stroke="currentColor" strokeWidth={3} strokeLinecap="round" />
              </svg>
            </div>
            <h2>Nicole&apos;s Take</h2>
          </div>
          <div className="research-nicole-content">
            <p>{data.nicole_synthesis}</p>
          </div>
        </motion.section>
      )}

      {/* Recommendations */}
      {data.recommendations.length > 0 && (
        <section className="research-recommendations-section">
          <h2 className="research-section-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <polyline points="9 11 12 14 22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
            Recommendations
          </h2>
          <div className="research-recommendations-list">
            {data.recommendations.map((rec, index) => (
              <motion.div
                key={index}
                className="research-recommendation"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 + index * 0.1 }}
              >
                <div className="research-recommendation-check">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={3}>
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </div>
                <p>{rec}</p>
              </motion.div>
            ))}
          </div>
        </section>
      )}

      {/* Sources */}
      {data.sources.length > 0 && (
        <section className="research-sources-section">
          <button
            className="research-sources-toggle"
            onClick={() => setShowAllSources(!showAllSources)}
          >
            <h2 className="research-section-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
              </svg>
              Sources ({data.sources.length})
            </h2>
            <motion.svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              className="sources-chevron"
              animate={{ rotate: showAllSources ? 180 : 0 }}
            >
              <polyline points="6 9 12 15 18 9" />
            </motion.svg>
          </button>
          
          <AnimatePresence>
            {showAllSources && (
              <motion.div
                className="research-sources-list"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
              >
                {data.sources.map((source, index) => (
                  <Citation key={index} source={source} index={index + 1} />
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </section>
      )}

      {/* Metadata footer */}
      <footer className="research-artifact-footer">
        <div className="research-metadata">
          <span>Model: {data.metadata.model}</span>
          <span>•</span>
          <span>Time: {data.metadata.elapsed_seconds.toFixed(1)}s</span>
          {data.metadata.input_tokens && (
            <>
              <span>•</span>
              <span>Tokens: {data.metadata.input_tokens + (data.metadata.output_tokens || 0)}</span>
            </>
          )}
        </div>
      </footer>
    </article>
  );
}

export default ResearchArtifact;

