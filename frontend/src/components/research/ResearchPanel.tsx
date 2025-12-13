'use client';

/**
 * ResearchPanel - Memory Dashboard-style Research Panel
 * 
 * Matches the design pattern of AlphawaveMemoryDashboard:
 * - Resizable side panel (400px - 800px)
 * - No backdrop/modal overlay
 * - Tab-based navigation
 * - Widget-based content layout
 * - Slides in from right edge
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { 
  ResearchResponse, 
  VibeInspirationResponse,
  ResearchStatus,
  ResearchType,
  ImageFeedback 
} from '@/lib/hooks/useResearch';

interface ResearchPanelProps {
  isOpen: boolean;
  onClose: () => void;
  authToken?: string;
  research: ResearchResponse | null;
  vibeInspirations: VibeInspirationResponse | null;
  status: ResearchStatus;
  statusMessage: string;
  progress: number;
  error: string | null;
  onFeedback?: (feedback: ImageFeedback) => void;  // Reserved for future inspiration feedback
  onRetry?: () => void;
  onExecuteResearch?: (query: string, type: ResearchType) => void;
}

// Research type options
const RESEARCH_TYPES: { value: ResearchType; label: string; icon: string }[] = [
  { value: 'general', label: 'General', icon: '📚' },
  { value: 'vibe_inspiration', label: 'Inspiration', icon: '🎨' },
  { value: 'competitor', label: 'Competitor', icon: '🔍' },
  { value: 'technical', label: 'Technical', icon: '⚙️' },
];

export function ResearchPanel({
  isOpen,
  onClose,
  authToken,
  research,
  vibeInspirations,
  status,
  statusMessage,
  progress,
  error,
  // onFeedback - reserved for future inspiration feedback
  onRetry,
  onExecuteResearch,
}: ResearchPanelProps) {
  const [activeTab, setActiveTab] = useState<'search' | 'results' | 'history'>('search');
  const [dashboardWidth, setDashboardWidth] = useState(520);
  const [isResizing, setIsResizing] = useState(false);
  const [query, setQuery] = useState('');
  const [researchType, setResearchType] = useState<ResearchType>('general');
  
  const resizeRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(520);
  const inputRef = useRef<HTMLInputElement>(null);

  const MIN_WIDTH = 400;
  const MAX_WIDTH = 800;
  
  const isOfflineMode = !authToken;
  const isLoading = status === 'pending' || status === 'researching' || status === 'synthesizing';
  const hasResearch = research !== null && status === 'complete';
  const hasInspirations = vibeInspirations !== null && vibeInspirations.inspirations?.length > 0;

  // Resize handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    startXRef.current = e.clientX;
    startWidthRef.current = dashboardWidth;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'ew-resize';
  }, [dashboardWidth]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const diff = startXRef.current - e.clientX;
      const newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, startWidthRef.current + diff));
      setDashboardWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  // Auto-switch to results tab when research completes
  useEffect(() => {
    if (hasResearch || hasInspirations) {
      setActiveTab('results');
    }
  }, [hasResearch, hasInspirations]);

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen && activeTab === 'search') {
      setTimeout(() => inputRef.current?.focus(), 300);
    }
  }, [isOpen, activeTab]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && onExecuteResearch) {
      onExecuteResearch(query.trim(), researchType);
    }
  }, [query, researchType, onExecuteResearch]);

  const handleQuickSearch = useCallback((exampleQuery: string) => {
    setQuery(exampleQuery);
    if (onExecuteResearch) {
      onExecuteResearch(exampleQuery, researchType);
    }
  }, [researchType, onExecuteResearch]);

  const selectedType = RESEARCH_TYPES.find(t => t.value === researchType) || RESEARCH_TYPES[0];

  return (
    <aside 
      className={`mem-dashboard-panel ${isOpen ? 'mem-open' : ''}`}
      style={{ '--mem-dashboard-width': `${dashboardWidth}px` } as React.CSSProperties}
    >
      {/* Resize Handle */}
      <div 
        ref={resizeRef}
        className={`mem-resize-handle ${isResizing ? 'mem-dragging' : ''}`}
        onMouseDown={handleMouseDown}
      />

      <div className="mem-dashboard-inner">
        {/* Header */}
        <div className="mem-dash-header">
          <div className="mem-dash-header-left">
            <div className="mem-dash-icon research-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <circle cx="11" cy="11" r="8" />
                <path d="M21 21l-4.35-4.35" />
              </svg>
            </div>
            <span className="mem-dash-title">Deep Research</span>
          </div>
          <button className="mem-dash-close-btn" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="mem-dash-tabs">
          {(['search', 'results', 'history'] as const).map(tab => (
            <button
              key={tab}
              className={`mem-dash-tab ${activeTab === tab ? 'mem-active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab === 'search' && '🔍 Search'}
              {tab === 'results' && `📋 Results ${hasResearch || hasInspirations ? '•' : ''}`}
              {tab === 'history' && '📜 History'}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="mem-dash-content">
          {/* Offline Mode Banner */}
          {isOfflineMode && (
            <div className="skills-offline-banner" style={{ margin: '12px 16px' }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              <div className="skills-offline-text">
                <strong>Sign In Required</strong>
                <span>Sign in to use Gemini Deep Research.</span>
              </div>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="skills-error-banner" style={{ margin: '12px 16px' }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
              <span>{error}</span>
              {onRetry && (
                <button onClick={onRetry} style={{ marginLeft: '12px', padding: '4px 12px', borderRadius: '4px', background: 'rgba(255,255,255,0.1)', border: 'none', color: 'inherit', cursor: 'pointer' }}>
                  Retry
                </button>
              )}
            </div>
          )}

          {/* Search Tab */}
          {activeTab === 'search' && (
            <div className="mem-tab-panel">
              {/* Loading State */}
              {isLoading && (
                <div className="mem-widget" style={{ textAlign: 'center', padding: '32px' }}>
                  <div className="research-loading-spinner" style={{ margin: '0 auto 16px' }}>
                    <svg viewBox="0 0 50 50" width="48" height="48">
                      <circle cx="25" cy="25" r="20" fill="none" stroke="currentColor" strokeWidth="3" strokeDasharray="90 60" strokeLinecap="round">
                        <animateTransform attributeName="transform" type="rotate" from="0 25 25" to="360 25 25" dur="1s" repeatCount="indefinite"/>
                      </circle>
                    </svg>
                  </div>
                  <div style={{ color: 'var(--alphawave-primary)', fontWeight: 500 }}>{statusMessage}</div>
                  <div style={{ marginTop: '12px', background: 'var(--alphawave-surface)', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
                    <div style={{ background: 'var(--alphawave-primary)', height: '100%', width: `${progress}%`, transition: 'width 0.3s ease' }} />
                  </div>
                  <div style={{ marginTop: '8px', fontSize: '12px', color: 'var(--alphawave-text-secondary)' }}>
                    Powered by Gemini 3 Pro + Google Search
                  </div>
                </div>
              )}

              {/* Search Form - Always visible when not loading */}
              {!isLoading && (
                <>
                  <div className="mem-widget">
                    <div className="mem-widget-header">
                      <span className="mem-widget-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                          <circle cx="11" cy="11" r="8" />
                          <path d="M21 21l-4.35-4.35" />
                        </svg>
                        Research Query
                      </span>
                      <span className="mem-widget-badge mem-badge-success">FREE</span>
                    </div>

                    <form onSubmit={handleSubmit}>
                      {/* Type Selector */}
                      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                        {RESEARCH_TYPES.map((type) => (
                          <button
                            key={type.value}
                            type="button"
                            className={`mem-filter-pill ${researchType === type.value ? 'mem-active' : ''}`}
                            onClick={() => setResearchType(type.value)}
                          >
                            {type.icon} {type.label}
                          </button>
                        ))}
                      </div>

                      {/* Search Input */}
                      <div className="mem-search-input-wrapper">
                        <svg className="mem-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                        </svg>
                        <input 
                          ref={inputRef}
                          type="text" 
                          className="mem-search-input" 
                          placeholder="What would you like to research?"
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                          disabled={isLoading || isOfflineMode}
                        />
                      </div>

                      <button
                        type="submit"
                        disabled={!query.trim() || isLoading || isOfflineMode}
                        style={{
                          marginTop: '12px',
                          width: '100%',
                          padding: '12px',
                          borderRadius: '8px',
                          border: 'none',
                          background: query.trim() && !isOfflineMode ? 'var(--alphawave-primary)' : 'var(--alphawave-surface)',
                          color: query.trim() && !isOfflineMode ? '#fff' : 'var(--alphawave-text-secondary)',
                          fontWeight: 600,
                          cursor: query.trim() && !isOfflineMode ? 'pointer' : 'not-allowed',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          gap: '8px',
                        }}
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} width="18" height="18">
                          <circle cx="11" cy="11" r="8" />
                          <path d="M21 21l-4.35-4.35" />
                        </svg>
                        {selectedType.icon} Research with {selectedType.label}
                      </button>
                    </form>
                  </div>

                  {/* Quick Examples */}
                  <div className="mem-widget">
                    <div className="mem-widget-header">
                      <span className="mem-widget-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                        </svg>
                        Quick Start
                      </span>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      <button 
                        className="research-example-btn"
                        onClick={() => handleQuickSearch('Modern wellness website design trends 2024')}
                        disabled={isOfflineMode}
                      >
                        &quot;Modern wellness website design trends 2024&quot;
                      </button>
                      <button 
                        className="research-example-btn"
                        onClick={() => handleQuickSearch('Best practices for doula service websites')}
                        disabled={isOfflineMode}
                      >
                        &quot;Best practices for doula service websites&quot;
                      </button>
                      <button 
                        className="research-example-btn"
                        onClick={() => handleQuickSearch('AI chatbot implementation patterns')}
                        disabled={isOfflineMode}
                      >
                        &quot;AI chatbot implementation patterns&quot;
                      </button>
                    </div>
                  </div>

                  {/* Info Widget */}
                  <div className="mem-widget">
                    <div className="mem-widget-header">
                      <span className="mem-widget-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                          <circle cx="12" cy="12" r="10"/>
                          <path d="M12 16v-4M12 8h.01"/>
                        </svg>
                        About Deep Research
                      </span>
                    </div>
                    <p style={{ fontSize: '13px', color: 'var(--alphawave-text-secondary)', lineHeight: 1.6, margin: 0 }}>
                      Uses <strong>Gemini 3 Pro</strong> with Google Search grounding to perform real-time web research. 
                      Results are synthesized by <strong>Nicole</strong> into actionable insights.
                    </p>
                    <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <span className="mem-widget-badge mem-badge-success">Google Search Grounding FREE</span>
                      <span className="mem-widget-badge mem-badge-info">Until Jan 2026</span>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Results Tab */}
          {activeTab === 'results' && (
            <div className="mem-tab-panel">
              {!hasResearch && !hasInspirations && !isLoading && (
                <div className="skills-empty">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <circle cx="11" cy="11" r="8" />
                    <path d="M21 21l-4.35-4.35" />
                  </svg>
                  <p>No research results yet. Start a search in the Search tab.</p>
                </div>
              )}

              {/* Research Results */}
              {hasResearch && (
                <>
                  {/* Summary Widget */}
                  <div className="mem-widget">
                    <div className="mem-widget-header">
                      <span className="mem-widget-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                          <path d="M14 2v6h6"/>
                        </svg>
                        Executive Summary
                      </span>
                      <span className="mem-widget-badge mem-badge-success">Complete</span>
                    </div>
                    <p style={{ fontSize: '14px', lineHeight: 1.7, color: 'var(--alphawave-text-primary)' }}>
                      {research.executive_summary}
                    </p>
                  </div>

                  {/* Nicole's Synthesis */}
                  {research.nicole_synthesis && (
                    <div className="mem-widget" style={{ borderLeft: '3px solid var(--alphawave-primary)' }}>
                      <div className="mem-widget-header">
                        <span className="mem-widget-title">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                            <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/>
                          </svg>
                          Nicole&apos;s Analysis
                        </span>
                      </div>
                      <p style={{ fontSize: '14px', lineHeight: 1.7, color: 'var(--alphawave-text-primary)', fontStyle: 'italic' }}>
                        {research.nicole_synthesis}
                      </p>
                    </div>
                  )}

                  {/* Key Findings */}
                  {research.findings?.length > 0 && (
                    <div className="mem-widget">
                      <div className="mem-widget-header">
                        <span className="mem-widget-title">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                            <polyline points="9 11 12 14 22 4"/>
                            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
                          </svg>
                          Key Findings
                        </span>
                        <span className="mem-widget-badge mem-badge-info">{research.findings.length}</span>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {research.findings.map((finding, i) => (
                          <div key={i} style={{ padding: '12px', background: 'var(--alphawave-surface)', borderRadius: '8px' }}>
                            <p style={{ margin: 0, fontSize: '13px', lineHeight: 1.6 }}>{finding.content}</p>
                            {finding.source_url && (
                              <a 
                                href={finding.source_url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                style={{ fontSize: '12px', color: 'var(--alphawave-primary)', marginTop: '8px', display: 'inline-block' }}
                              >
                                {finding.source_title || 'Source'} ↗
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Recommendations */}
                  {research.recommendations?.length > 0 && (
                    <div className="mem-widget">
                      <div className="mem-widget-header">
                        <span className="mem-widget-title">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                            <path d="M2 17l10 5 10-5"/>
                            <path d="M2 12l10 5 10-5"/>
                          </svg>
                          Recommendations
                        </span>
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '20px' }}>
                        {research.recommendations.map((rec, i) => (
                          <li key={i} style={{ marginBottom: '8px', fontSize: '13px', lineHeight: 1.6 }}>{rec}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Sources */}
                  {research.sources?.length > 0 && (
                    <div className="mem-widget">
                      <div className="mem-widget-header">
                        <span className="mem-widget-title">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                          </svg>
                          Sources
                        </span>
                        <span className="mem-widget-badge mem-badge-info">{research.sources.length}</span>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {research.sources.map((source, i) => (
                          <a
                            key={i}
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{
                              display: 'block',
                              padding: '8px 12px',
                              background: 'var(--alphawave-surface)',
                              borderRadius: '6px',
                              fontSize: '13px',
                              color: 'var(--alphawave-primary)',
                              textDecoration: 'none',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {source.title || source.url} ↗
                          </a>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Metadata */}
                  {research.metadata && (
                    <div className="mem-widget">
                      <div className="mem-widget-header">
                        <span className="mem-widget-title">
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                            <circle cx="12" cy="12" r="10"/>
                            <path d="M12 6v6l4 2"/>
                          </svg>
                          Research Details
                        </span>
                      </div>
                      <div className="mem-stat-grid mem-stat-grid-2">
                        <div className="mem-stat-box">
                          <div className="mem-stat-value mem-small">{research.metadata.elapsed_seconds?.toFixed(1)}s</div>
                          <div className="mem-stat-label">Duration</div>
                        </div>
                        <div className="mem-stat-box">
                          <div className="mem-stat-value mem-small mem-success">${research.metadata.cost_usd?.toFixed(4)}</div>
                          <div className="mem-stat-label">Cost</div>
                        </div>
                        <div className="mem-stat-box">
                          <div className="mem-stat-value mem-small">{((research.metadata.input_tokens || 0) / 1000).toFixed(1)}K</div>
                          <div className="mem-stat-label">Input Tokens</div>
                        </div>
                        <div className="mem-stat-box">
                          <div className="mem-stat-value mem-small">{((research.metadata.output_tokens || 0) / 1000).toFixed(1)}K</div>
                          <div className="mem-stat-label">Output Tokens</div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )}

              {/* Inspiration Results */}
              {hasInspirations && (
                <div className="mem-widget">
                  <div className="mem-widget-header">
                    <span className="mem-widget-title">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                        <rect x="3" y="3" width="18" height="18" rx="2"/>
                        <circle cx="8.5" cy="8.5" r="1.5"/>
                        <path d="M21 15l-5-5L5 21"/>
                      </svg>
                      Design Inspirations
                    </span>
                    <span className="mem-widget-badge mem-badge-success">{vibeInspirations.inspirations.length} found</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
                    {vibeInspirations.inspirations.map((img, i) => (
                      <div key={i} style={{ borderRadius: '8px', overflow: 'hidden', background: 'var(--alphawave-surface)' }}>
                        <div style={{ aspectRatio: '16/9', background: 'var(--alphawave-bg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          {img.url ? (
                            <img src={img.url} alt={img.title || 'Inspiration'} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                          ) : (
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1} width="32" height="32" style={{ opacity: 0.3 }}>
                              <rect x="3" y="3" width="18" height="18" rx="2"/>
                              <circle cx="8.5" cy="8.5" r="1.5"/>
                              <path d="M21 15l-5-5L5 21"/>
                            </svg>
                          )}
                        </div>
                        <div style={{ padding: '8px', fontSize: '12px' }}>
                          <div style={{ fontWeight: 500 }}>{img.title || 'Untitled'}</div>
                          {img.description && <div style={{ color: 'var(--alphawave-text-secondary)', marginTop: '4px' }}>{img.description}</div>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* History Tab */}
          {activeTab === 'history' && (
            <div className="mem-tab-panel">
              <div className="skills-empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 6v6l4 2"/>
                </svg>
                <p>Research history coming soon.</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mem-dash-footer">
          <div className="mem-dash-footer-text">
            {authToken ? (
              <>
                {status === 'idle' && 'Ready to research'}
                {isLoading && statusMessage}
                {status === 'complete' && `Query: "${research?.query || vibeInspirations?.query}"`}
                {status === 'failed' && 'Research failed - try again'}
              </>
            ) : (
              'Sign in to use Deep Research'
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}

export default ResearchPanel;
