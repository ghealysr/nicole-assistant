'use client';

/**
 * ResearchPanel - Editorial-quality Research Panel
 * 
 * Design Philosophy:
 * - Narrow panel for search input
 * - Expands to full article width when showing results
 * - Magazine-quality typography and layout
 * - Inspired by New Yorker, Time, Medium
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { 
  ResearchResponse, 
  VibeInspirationResponse,
  ResearchStatus,
  ResearchType,
  ImageFeedback 
} from '@/lib/hooks/useResearch';
import { ResearchArticle } from './ResearchArticle';

interface ResearchHistoryItem {
  request_id: number;
  query: string;
  type: ResearchType;
  created_at: string;
}

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
  history?: ResearchHistoryItem[];
  onFeedback?: (feedback: ImageFeedback) => void;  // Reserved for future inspiration feedback
  onRetry?: () => void;
  onExecuteResearch?: (query: string, type: ResearchType) => void;
  onLoadResearch?: (requestId: number) => void;
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
  history = [],
  // onFeedback - reserved for future inspiration feedback
  onRetry,
  onExecuteResearch,
  onLoadResearch,
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

  // Dynamic width: narrow for search, wide for article reading
  const MIN_WIDTH = 400;
  const MAX_WIDTH = 900;
  const ARTICLE_WIDTH = 720; // Optimal reading width for articles
  
  const isOfflineMode = !authToken;
  const isLoading = status === 'pending' || status === 'researching' || status === 'synthesizing';
  const hasResearch = research !== null && status === 'complete';
  const hasInspirations = vibeInspirations !== null && vibeInspirations.inspirations?.length > 0;
  
  // Auto-expand when showing results
  const effectiveWidth = (hasResearch || hasInspirations) && activeTab === 'results' 
    ? Math.max(dashboardWidth, ARTICLE_WIDTH) 
    : dashboardWidth;
  
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
      className={`mem-dashboard-panel ${isOpen ? 'mem-open' : ''} ${hasResearch && activeTab === 'results' ? 'research-article-mode' : ''}`}
      style={{ '--mem-dashboard-width': `${effectiveWidth}px` } as React.CSSProperties}
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
                <span>Sign in to use AlphaWave Research.</span>
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
              {/* Loading State - Purple Mystical Circle */}
              {isLoading && (
                <div className="mem-widget" style={{ textAlign: 'center', padding: '48px 32px' }}>
                  {/* Mystical Purple Ring */}
                  <div style={{ 
                    position: 'relative', 
                    width: '80px', 
                    height: '80px', 
                    margin: '0 auto 24px'
                  }}>
                    {/* Outer glow ring */}
                    <svg viewBox="0 0 80 80" width="80" height="80" style={{ position: 'absolute', top: 0, left: 0 }}>
                      <defs>
                        <linearGradient id="mysticalGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="#8B5CF6" stopOpacity="1" />
                          <stop offset="50%" stopColor="#A78BFA" stopOpacity="0.8" />
                          <stop offset="100%" stopColor="#C4B5FD" stopOpacity="0.6" />
                        </linearGradient>
                        <filter id="glow">
                          <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                          <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
                        </filter>
                      </defs>
                      <circle 
                        cx="40" cy="40" r="35" 
                        fill="none" 
                        stroke="url(#mysticalGradient)" 
                        strokeWidth="3" 
                        strokeDasharray="120 80" 
                        strokeLinecap="round"
                        filter="url(#glow)"
                      >
                        <animateTransform 
                          attributeName="transform" 
                          type="rotate" 
                          from="0 40 40" 
                          to="360 40 40" 
                          dur="1.5s" 
                          repeatCount="indefinite"
                        />
                      </circle>
                      {/* Inner sparkle ring */}
                      <circle 
                        cx="40" cy="40" r="28" 
                        fill="none" 
                        stroke="#C4B5FD" 
                        strokeWidth="1.5" 
                        strokeDasharray="20 40" 
                        strokeLinecap="round"
                        opacity="0.6"
                      >
                        <animateTransform 
                          attributeName="transform" 
                          type="rotate" 
                          from="360 40 40" 
                          to="0 40 40" 
                          dur="2s" 
                          repeatCount="indefinite"
                        />
                      </circle>
                    </svg>
                    {/* Center icon */}
                    <div style={{ 
                      position: 'absolute', 
                      top: '50%', 
                      left: '50%', 
                      transform: 'translate(-50%, -50%)',
                      color: '#8B5CF6'
                    }}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} width="28" height="28">
                        <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/>
                      </svg>
                    </div>
                  </div>
                  
                  <div style={{ 
                    fontSize: '18px', 
                    fontWeight: 600, 
                    color: '#8B5CF6',
                    marginBottom: '8px'
                  }}>
                    BRB... Researching
                  </div>
                  <div style={{ 
                    fontSize: '13px', 
                    color: 'var(--alphawave-text-secondary)',
                    marginBottom: '16px'
                  }}>
                    {statusMessage}
                  </div>
                  
                  {/* Progress bar */}
                  <div style={{ 
                    background: 'var(--alphawave-surface)', 
                    borderRadius: '8px', 
                    height: '6px', 
                    overflow: 'hidden',
                    maxWidth: '200px',
                    margin: '0 auto'
                  }}>
                    <div style={{ 
                      background: 'linear-gradient(90deg, #8B5CF6, #A78BFA)', 
                      height: '100%', 
                      width: `${progress}%`, 
                      transition: 'width 0.3s ease',
                      borderRadius: '8px'
                    }} />
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
                      AlphaWave Research uses real-time web search to gather information, 
                      then <strong>Nicole</strong> synthesizes findings into actionable insights.
                    </p>
                    <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <span className="mem-widget-badge mem-badge-success">Real-time Search</span>
                      <span className="mem-widget-badge mem-badge-info">AI Synthesis</span>
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

              {/* Research Results - Editorial Article Format */}
              {hasResearch && research && (
                <ResearchArticle data={research} />
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
                            // eslint-disable-next-line @next/next/no-img-element
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
              {history.length === 0 ? (
                <div className="skills-empty">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M12 6v6l4 2"/>
                  </svg>
                  <p>No research history yet. Start researching!</p>
                </div>
              ) : (
                <div className="mem-widget">
                  <div className="mem-widget-header">
                    <span className="mem-widget-title">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 6v6l4 2"/>
                      </svg>
                      Recent Research
                    </span>
                    <span className="mem-widget-badge">{history.length}</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {history.map((item) => {
                      const typeInfo = RESEARCH_TYPES.find(t => t.value === item.type);
                      const date = new Date(item.created_at);
                      const formattedDate = date.toLocaleDateString('en-US', { 
                        month: 'short', 
                        day: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit'
                      });
                      
                      return (
                        <button
                          key={item.request_id}
                          onClick={() => onLoadResearch?.(item.request_id)}
                          style={{
                            display: 'flex',
                            alignItems: 'flex-start',
                            gap: '12px',
                            padding: '12px',
                            background: 'var(--alphawave-surface)',
                            border: '1px solid transparent',
                            borderRadius: '8px',
                            textAlign: 'left',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'var(--alphawave-surface-hover, #f0f0f0)';
                            e.currentTarget.style.borderColor = 'var(--alphawave-primary)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'var(--alphawave-surface)';
                            e.currentTarget.style.borderColor = 'transparent';
                          }}
                        >
                          <span style={{ fontSize: '20px' }}>{typeInfo?.icon || '📚'}</span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ 
                              fontWeight: 500, 
                              color: 'var(--alphawave-text)',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap'
                            }}>
                              {item.query.length > 60 ? item.query.slice(0, 60) + '...' : item.query}
                            </div>
                            <div style={{ 
                              fontSize: '12px', 
                              color: 'var(--alphawave-text-secondary)',
                              marginTop: '4px'
                            }}>
                              {typeInfo?.label || 'Research'} • {formattedDate}
                            </div>
                          </div>
                          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} width={16} height={16} style={{ color: 'var(--alphawave-text-secondary)', flexShrink: 0 }}>
                            <path d="M9 18l6-6-6-6"/>
                          </svg>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
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
