'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { AlphawaveSkillsTab } from './AlphawaveSkillsTab';
import { useMemoryDashboardData, type Memory, type Document, type MemoryStats } from '@/lib/hooks/useMemoryDashboardData';

interface AlphawaveMemoryDashboardProps {
  isOpen: boolean;
  onClose: () => void;
  authToken?: string;
}

// Default empty stats - used for empty state display (NOT fake data)
const emptyStats: MemoryStats = {
  total: 0,
  active: 0,
  archived: 0,
  avgConfidence: 0,
  highConfidenceCount: 0,
  decayingCount: 0,
  factCount: 0,
  preferenceCount: 0,
  patternCount: 0,
  otherCount: 0,
  seven_day_access_frequency: [0, 0, 0, 0, 0, 0, 0],
  recent_corrections: { total: 0, applied: 0, pending: 0 },
};

/**
 * Nicole V7 Memory Dashboard - Full featured memory system panel.
 * 
 * Backend Integration Points:
 * - GET /memories/stats - Fetch memory statistics
 * - GET /memories - Fetch memories with filters
 * - GET /documents/list - Fetch processed documents
 * - GET /chat/conversations - Fetch chat history
 * - GET /health/system - System health and configuration
 * - GET /dashboard/usage - Usage and cost metrics
 * - GET /dashboard/diagnostics - System diagnostics
 * 
 * QA Notes:
 * - Resizable panel (400px - 800px)
 * - All tabs functional with real backend data
 * - Empty state when not logged in
 * - NO fake/dummy data - all real or empty
 */
export function AlphawaveMemoryDashboard({ isOpen, onClose, authToken }: AlphawaveMemoryDashboardProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'memories' | 'documents' | 'history' | 'skills' | 'system'>('overview');
  const [dashboardWidth, setDashboardWidth] = useState(520);
  const [isResizing, setIsResizing] = useState(false);
  const [memoryFilter, setMemoryFilter] = useState<string>('all');
  const [memorySearch, setMemorySearch] = useState('');
  const [documentSearch, setDocumentSearch] = useState('');
  const [historySearch, setHistorySearch] = useState('');
  
  const resizeRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(520);

  const MIN_WIDTH = 400;
  const MAX_WIDTH = 800;
  
  // Fetch dashboard data from backend
  const dashboardData = useMemoryDashboardData(authToken);
  
  // Use real data - fall back to empty stats, NOT fake sample data
  const stats = dashboardData.stats || emptyStats;
  const memories = dashboardData.memories;
  const documents = dashboardData.documents;
  const conversations = dashboardData.conversations;
  const systemHealth = dashboardData.systemHealth;
  const usage = dashboardData.usage;
  const diagnostics = dashboardData.diagnostics;
  const isOfflineMode = !authToken;
  
  // Calculate health badge based on diagnostics or fallback to stats
  const getHealthBadge = (): { label: string; class: string } => {
    // If still loading, show loading state
    if (dashboardData.loading) return { label: 'Loading...', class: 'mem-badge-info' };
    
    // If no auth, show offline
    if (!authToken) return { label: 'Sign In', class: 'mem-badge-warning' };
    
    // Use diagnostics if available
    if (diagnostics?.health?.score !== undefined) {
      const score = diagnostics.health.score;
      if (score >= 90) return { label: 'Excellent', class: 'mem-badge-success' };
      if (score >= 70) return { label: 'Healthy', class: 'mem-badge-success' };
      if (score >= 50) return { label: 'Fair', class: 'mem-badge-warning' };
      return { label: 'Needs Attention', class: 'mem-badge-error' };
    }
    
    // Fallback: use stats to determine health
    if (dashboardData.stats) {
      const avgConf = dashboardData.stats.avgConfidence || 0;
      if (avgConf >= 80) return { label: 'Healthy', class: 'mem-badge-success' };
      if (avgConf >= 50) return { label: 'Fair', class: 'mem-badge-warning' };
      if (avgConf > 0) return { label: 'Needs Attention', class: 'mem-badge-error' };
    }
    
    // If no data at all
    return { label: 'No Data', class: 'mem-badge-info' };
  };
  
  // Calculate actual day names for 7-day chart
  const getDayLabels = (): string[] => {
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const labels: string[] = [];
    const today = new Date();
    for (let i = 6; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      labels.push(i === 0 ? 'Today' : days[d.getDay()]);
    }
    return labels;
  };

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

  // Filter memories based on search and type
  const filteredMemories = memories.filter(m => {
    const matchesFilter = memoryFilter === 'all' || m.type === memoryFilter;
    const matchesSearch = memorySearch === '' || m.content.toLowerCase().includes(memorySearch.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  // Filter documents
  const filteredDocuments = documents.filter(d => 
    documentSearch === '' || (d.name && d.name.toLowerCase().includes(documentSearch.toLowerCase()))
  );

  // Filter history
  const filteredHistory = conversations.filter(h => 
    historySearch === '' || 
    h.title.toLowerCase().includes(historySearch.toLowerCase()) ||
    (h.preview && h.preview.toLowerCase().includes(historySearch.toLowerCase()))
  );

  const getMemoryTypeBadgeClass = (type: Memory['type']) => {
    const classes: Record<Memory['type'], string> = {
      fact: 'mem-type-fact',
      preference: 'mem-type-preference',
      pattern: 'mem-type-pattern',
      correction: 'mem-type-correction',
      relationship: 'mem-type-relationship',
      goal: 'mem-type-goal',
    };
    return classes[type] || 'mem-type-fact';
  };

  const getDocIconClass = (type: Document['type']) => {
    const classes: Record<Document['type'], string> = {
      pdf: 'mem-doc-icon-pdf',
      image: 'mem-doc-icon-image',
      code: 'mem-doc-icon-code',
    };
    return classes[type] || '';
  };

  const getStatusClass = (status: Document['status']) => {
    const classes: Record<Document['status'], string> = {
      processed: 'mem-status-processed',
      processing: 'mem-status-processing',
      pending: 'mem-status-pending',
    };
    return classes[status] || '';
  };

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
            <div className="mem-dash-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/>
              </svg>
            </div>
            <span className="mem-dash-title">Memory System</span>
          </div>
          <button className="mem-dash-close-btn" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="mem-dash-tabs">
          {(['overview', 'memories', 'documents', 'history', 'skills', 'system'] as const).map(tab => (
            <button
              key={tab}
              className={`mem-dash-tab ${activeTab === tab ? 'mem-active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
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
                <strong>Preview Mode</strong>
                <span>Sign in to view your actual memories and documents.</span>
              </div>
            </div>
          )}
          
          {/* Error Banner */}
          {dashboardData.error && (
            <div className="skills-error-banner" style={{ margin: '12px 16px' }}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
              <span>{dashboardData.error}</span>
              <button onClick={() => dashboardData.refresh()}>Retry</button>
            </div>
          )}
          
          {/* Loading State */}
          {dashboardData.loading && authToken && (
            <div style={{ padding: '24px', textAlign: 'center', color: '#a78bfa' }}>
              <div style={{ marginBottom: '8px' }}>Loading dashboard data...</div>
            </div>
          )}
          
          {/* Overview Tab */}
          {activeTab === 'overview' && !dashboardData.loading && (
            <div className="mem-tab-panel">
              {/* Memory Health */}
              <div className="mem-widget">
                <div className="mem-widget-header">
                  <span className="mem-widget-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                      <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                    </svg>
                    Memory Health
                  </span>
                  <span className={`mem-widget-badge ${getHealthBadge().class}`}>{getHealthBadge().label}</span>
                </div>
                <div className="mem-stat-grid">
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-highlight">{stats.total}</div>
                    <div className="mem-stat-label">Total</div>
                  </div>
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-success">{stats.active}</div>
                    <div className="mem-stat-label">Active</div>
                  </div>
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small">{stats.archived}</div>
                    <div className="mem-stat-label">Archived</div>
                  </div>
                </div>
              </div>

              {/* Confidence Distribution */}
              <div className="mem-widget">
                <div className="mem-widget-header">
                  <span className="mem-widget-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                      <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
                    </svg>
                    Confidence Score
                  </span>
                  <span className="mem-widget-badge mem-badge-info">Avg {stats.avgConfidence}%</span>
                </div>
                <div className="mem-progress-bar">
                  <div className="mem-progress-fill mem-progress-success" style={{ width: `${stats.avgConfidence}%` }}></div>
                </div>
                <div className="mem-progress-labels">
                  <span>High Confidence (&gt;80%): {stats.highConfidenceCount}</span>
                  <span>Decaying: {stats.decayingCount}</span>
                </div>
              </div>

              {/* Memory Types */}
              <div className="mem-widget">
                <div className="mem-widget-header">
                  <span className="mem-widget-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                    </svg>
                    Memory Types
                  </span>
                </div>
                <div className="mem-stat-grid mem-stat-grid-2">
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small">{stats.factCount}</div>
                    <div className="mem-stat-label">Facts</div>
                    <div className="mem-stat-sublabel">{stats.total > 0 ? ((stats.factCount / stats.total) * 100).toFixed(1) : 0}%</div>
                  </div>
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small">{stats.preferenceCount}</div>
                    <div className="mem-stat-label">Preferences</div>
                    <div className="mem-stat-sublabel">{stats.total > 0 ? ((stats.preferenceCount / stats.total) * 100).toFixed(1) : 0}%</div>
                  </div>
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small">{stats.patternCount}</div>
                    <div className="mem-stat-label">Patterns</div>
                    <div className="mem-stat-sublabel">{stats.total > 0 ? ((stats.patternCount / stats.total) * 100).toFixed(1) : 0}%</div>
                  </div>
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small">{stats.otherCount}</div>
                    <div className="mem-stat-label">Other</div>
                    <div className="mem-stat-sublabel">{stats.total > 0 ? ((stats.otherCount / stats.total) * 100).toFixed(1) : 0}%</div>
                  </div>
                </div>
              </div>

              {/* 7-Day Access Frequency */}
              <div className="mem-widget">
                <div className="mem-widget-header">
                  <span className="mem-widget-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                      <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
                    </svg>
                    7-Day Access Frequency
                  </span>
                </div>
                <div className="mem-mini-chart">
                  {(() => {
                    const frequencies = stats.seven_day_access_frequency || [0, 0, 0, 0, 0, 0, 0];
                    const maxFreq = Math.max(...frequencies, 1);
                    return frequencies.map((freq, i) => (
                      <div 
                        key={i} 
                        className="mem-chart-bar" 
                        style={{ height: `${(freq / maxFreq) * 100}%` }}
                        title={`${freq} accesses`}
                      />
                    ));
                  })()}
                </div>
                <div className="mem-progress-labels">
                  {getDayLabels().map((day, i) => (
                    <span key={i}>{day}</span>
                  ))}
                </div>
              </div>

              {/* Usage & Costs */}
              {usage && (
                <div className="mem-widget">
                  <div className="mem-widget-header">
                    <span className="mem-widget-title">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                        <line x1="12" y1="1" x2="12" y2="23"/>
                        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                      </svg>
                      Usage &amp; Costs (30 days)
                    </span>
                    <span className={`mem-widget-badge ${usage.projections.trend === 'increasing' ? 'mem-badge-warning' : 'mem-badge-info'}`}>
                      ${usage.costs.total.toFixed(2)}
                    </span>
                  </div>
                  <div className="mem-stat-grid mem-stat-grid-2">
                    <div className="mem-stat-box">
                      <div className="mem-stat-value mem-small">{(usage.tokens.total / 1000).toFixed(1)}K</div>
                      <div className="mem-stat-label">Tokens</div>
                      <div className="mem-stat-sublabel">${usage.costs.claude.toFixed(2)} Claude</div>
                    </div>
                    <div className="mem-stat-box">
                      <div className="mem-stat-value mem-small">{usage.storage.total_formatted}</div>
                      <div className="mem-stat-label">Storage</div>
                      <div className="mem-stat-sublabel">{usage.storage.document_count} docs</div>
                    </div>
                    <div className="mem-stat-box">
                      <div className="mem-stat-value mem-small">${usage.projections.monthly_estimate.toFixed(2)}</div>
                      <div className="mem-stat-label">Est. Monthly</div>
                      <div className="mem-stat-sublabel">{usage.projections.trend}</div>
                    </div>
                    <div className="mem-stat-box">
                      <div className="mem-stat-value mem-small">{usage.requests.claude}</div>
                      <div className="mem-stat-label">API Calls</div>
                      <div className="mem-stat-sublabel">30 day period</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Diagnostics */}
              {diagnostics && (diagnostics.issues.length > 0 || diagnostics.warnings.length > 0) && (
                <div className="mem-widget">
                  <div className="mem-widget-header">
                    <span className="mem-widget-title">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="12" y1="8" x2="12" y2="12"/>
                        <line x1="12" y1="16" x2="12.01" y2="16"/>
                      </svg>
                      Diagnostics
                    </span>
                    <span className={`mem-widget-badge ${diagnostics.issues.length > 0 ? 'mem-badge-error' : 'mem-badge-warning'}`}>
                      {diagnostics.issues.length + diagnostics.warnings.length} items
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {diagnostics.issues.map((issue, i) => (
                      <div key={`issue-${i}`} className="mem-metric-row" style={{ color: 'var(--alphawave-error)' }}>
                        <span>⚠️ {issue.message}</span>
                      </div>
                    ))}
                    {diagnostics.warnings.map((warning, i) => (
                      <div key={`warn-${i}`} className="mem-metric-row" style={{ color: 'var(--alphawave-warning)' }}>
                        <span>💡 {warning.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recent Corrections */}
              <div className="mem-widget">
                <div className="mem-widget-header">
                  <span className="mem-widget-title">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                    Corrections (Last 7 Days)
                  </span>
                  <span className="mem-widget-badge mem-badge-warning">
                    {stats.recent_corrections?.pending || 0} pending
                  </span>
                </div>
                <div className="mem-stat-grid">
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small">{stats.recent_corrections?.total || 0}</div>
                    <div className="mem-stat-label">Total</div>
                  </div>
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small mem-success">{stats.recent_corrections?.applied || 0}</div>
                    <div className="mem-stat-label">Applied</div>
                  </div>
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small mem-warning">{stats.recent_corrections?.pending || 0}</div>
                    <div className="mem-stat-label">Pending</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Memories Tab */}
          {activeTab === 'memories' && !dashboardData.loading && (
            <div className="mem-tab-panel">
              <div className="mem-search-input-wrapper">
                <svg className="mem-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <input 
                  type="text" 
                  className="mem-search-input" 
                  placeholder="Search memories..."
                  value={memorySearch}
                  onChange={(e) => setMemorySearch(e.target.value)}
                />
              </div>

              <div className="mem-filter-pills">
                {['all', 'fact', 'preference', 'pattern', 'correction'].map(filter => (
                  <button
                    key={filter}
                    className={`mem-filter-pill ${memoryFilter === filter ? 'mem-active' : ''}`}
                    onClick={() => setMemoryFilter(filter)}
                  >
                    {filter.charAt(0).toUpperCase() + filter.slice(1)}{filter === 'all' ? '' : 's'}
                  </button>
                ))}
              </div>

              <div className="mem-memory-list">
                {filteredMemories.length > 0 ? (
                  filteredMemories.map(memory => (
                    <div key={memory.id} className="mem-memory-item">
                      <span className={`mem-memory-type-badge ${getMemoryTypeBadgeClass(memory.type)}`}>
                        {memory.type}
                      </span>
                      <div className="mem-memory-content">
                        <div className="mem-memory-text">{memory.content}</div>
                        <div className="mem-memory-meta">
                          <span className="mem-memory-confidence">
                            <div className="mem-confidence-bar">
                              <div className="mem-confidence-fill" style={{ width: `${memory.confidence * 100}%` }}></div>
                            </div>
                            {Math.round(memory.confidence * 100)}%
                          </span>
                          <span>Accessed {memory.accessCount}x</span>
                          <span>{memory.lastAccessed}</span>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="skills-empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <circle cx="12" cy="12" r="10"/>
                      <path d="M12 6v6l4 2"/>
                    </svg>
                    <p>{memorySearch || memoryFilter !== 'all' ? 'No memories match your filters' : 'No memories yet. Ask Nicole to remember something!'}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Documents Tab */}
          {activeTab === 'documents' && !dashboardData.loading && (
            <div className="mem-tab-panel">
              <div className="mem-search-input-wrapper">
                <svg className="mem-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <input 
                  type="text" 
                  className="mem-search-input" 
                  placeholder="Search documents..."
                  value={documentSearch}
                  onChange={(e) => setDocumentSearch(e.target.value)}
                />
              </div>

              <div className="mem-widget" style={{ marginBottom: '16px' }}>
                <div className="mem-stat-grid">
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small mem-highlight">{documents.length}</div>
                    <div className="mem-stat-label">Total Files</div>
                  </div>
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small">{documents.reduce((sum, d) => sum + (d.chunks || 0), 0)}</div>
                    <div className="mem-stat-label">Chunks</div>
                  </div>
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small">{usage?.storage.documents_formatted || '—'}</div>
                    <div className="mem-stat-label">Storage</div>
                  </div>
                </div>
              </div>

              <div className="mem-document-list">
                {filteredDocuments.length > 0 ? filteredDocuments.map(doc => (
                  <div key={doc.id} className="mem-doc-item">
                    <div className={`mem-doc-icon ${getDocIconClass(doc.type)}`}>
                      {doc.type === 'pdf' && (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        </svg>
                      )}
                      {doc.type === 'image' && (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                          <rect x="3" y="3" width="18" height="18" rx="2"/>
                          <circle cx="8.5" cy="8.5" r="1.5"/>
                          <path d="M21 15l-5-5L5 21"/>
                        </svg>
                      )}
                      {doc.type === 'code' && (
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                          <polyline points="16 18 22 12 16 6"/>
                          <polyline points="8 6 2 12 8 18"/>
                        </svg>
                      )}
                    </div>
                    <div className="mem-doc-info">
                      <div className="mem-doc-name">{doc.name}</div>
                      <div className="mem-doc-meta">{doc.size} • {doc.chunks} chunks • {doc.uploaded}</div>
                    </div>
                    <span className={`mem-doc-status ${getStatusClass(doc.status)}`}>
                      {doc.status}
                    </span>
                  </div>
                )) : (
                  <div className="skills-empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <path d="M14 2v6h6"/>
                    </svg>
                    <p>{documentSearch ? 'No documents match your search' : 'No documents uploaded yet'}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* History Tab */}
          {activeTab === 'history' && !dashboardData.loading && (
            <div className="mem-tab-panel">
              <div className="mem-search-input-wrapper">
                <svg className="mem-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <input 
                  type="text" 
                  className="mem-search-input" 
                  placeholder="Search conversations..."
                  value={historySearch}
                  onChange={(e) => setHistorySearch(e.target.value)}
                />
              </div>

              <div className="mem-widget" style={{ marginBottom: '16px' }}>
                <div className="mem-stat-grid mem-stat-grid-4">
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small mem-highlight">{conversations.length}</div>
                    <div className="mem-stat-label">Chats</div>
                  </div>
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small">{conversations.reduce((sum, c) => sum + (c.messages || 0), 0)}</div>
                    <div className="mem-stat-label">Messages</div>
                  </div>
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small">{stats.total}</div>
                    <div className="mem-stat-label">Memories</div>
                  </div>
                  <div className="mem-stat-box">
                    <div className="mem-stat-value mem-small">{diagnostics?.api_health.success_rate.toFixed(0) || '—'}%</div>
                    <div className="mem-stat-label">Success Rate</div>
                  </div>
                </div>
              </div>

              <div className="mem-chat-history-list">
                {filteredHistory.length > 0 ? filteredHistory.map(chat => (
                  <div key={chat.id} className="mem-chat-item">
                    <div className="mem-chat-title">{chat.title}</div>
                    <div className="mem-chat-preview">{chat.preview}</div>
                    <div className="mem-chat-meta">
                      <span>{chat.date} • {chat.messages} messages</span>
                      <span className="mem-chat-memories-created">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-3 h-3">
                          <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/>
                        </svg>
                        {chat.memoriesCreated} memories
                      </span>
                    </div>
                  </div>
                )) : (
                  <div className="skills-empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                    <p>{historySearch ? 'No conversations match your search' : 'No conversations yet. Start chatting with Nicole!'}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Skills Tab */}
          {activeTab === 'skills' && (
            <div className="mem-tab-panel">
              <AlphawaveSkillsTab authToken={authToken} />
            </div>
          )}

          {/* System Tab */}
          {activeTab === 'system' && (
            <div className="mem-tab-panel">
              {systemHealth && systemHealth.system ? (
                <>
                  {/* System Health */}
                  <div className="mem-widget">
                    <div className="mem-widget-header">
                      <span className="mem-widget-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                          <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                        </svg>
                        System Status
                      </span>
                      <span className={`mem-widget-badge ${systemHealth.status === 'healthy' ? 'mem-badge-success' : 'mem-badge-warning'}`}>
                        {systemHealth.status === 'healthy' ? 'All Systems Operational' : 'Degraded'}
                      </span>
                    </div>
                    <div className="mem-metric-row">
                      <span className="mem-metric-label">CPU Usage</span>
                      <span className={`mem-metric-value ${(systemHealth.system?.cpu_percent || 0) < 70 ? 'mem-good' : 'mem-warning'}`}>
                        {systemHealth.system?.cpu_percent ?? '—'}%
                      </span>
                    </div>
                    <div className="mem-metric-row">
                      <span className="mem-metric-label">Memory Usage</span>
                      <span className={`mem-metric-value ${(systemHealth.system?.memory_percent || 0) < 80 ? 'mem-good' : 'mem-warning'}`}>
                        {systemHealth.system?.memory_percent ?? '—'}%
                      </span>
                    </div>
                    <div className="mem-metric-row">
                      <span className="mem-metric-label">Available Memory</span>
                      <span className="mem-metric-value mem-good">{systemHealth.system?.memory_available_gb ?? '—'} GB</span>
                    </div>
                  </div>

                  {/* Database Status */}
                  <div className="mem-widget">
                    <div className="mem-widget-header">
                      <span className="mem-widget-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                          <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
                        </svg>
                        Database
                      </span>
                      <span className={`mem-widget-badge ${systemHealth.databases?.tiger_timescaledb === 'online' ? 'mem-badge-success' : 'mem-badge-error'}`}>
                        {systemHealth.databases?.tiger_timescaledb === 'online' ? 'Connected' : 'Offline'}
                      </span>
                    </div>
                    <div className="mem-metric-row">
                      <span className="mem-metric-label">Tiger TimescaleDB</span>
                      <span className={`mem-metric-value ${systemHealth.databases?.tiger_timescaledb === 'online' ? 'mem-good' : 'mem-error'}`}>
                        ● {systemHealth.databases?.tiger_timescaledb === 'online' ? 'Online' : 'Offline'}
                      </span>
                    </div>
                  </div>

                  {/* Services Status */}
                  <div className="mem-widget">
                    <div className="mem-widget-header">
                      <span className="mem-widget-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                        </svg>
                        Services
                      </span>
                    </div>
                    <div className="mem-metric-row">
                      <span className="mem-metric-label">MCP Gateway</span>
                      <span className={`mem-metric-value ${systemHealth.services?.mcp_gateway === 'online' ? 'mem-good' : 'mem-small'}`}>
                        ● {systemHealth.services?.mcp_gateway === 'online' ? `Online (${systemHealth.services?.mcp_tool_count || 0} tools)` : 'Offline'}
                      </span>
                    </div>
                    <div className="mem-metric-row">
                      <span className="mem-metric-label">Background Jobs</span>
                      <span className={`mem-metric-value ${systemHealth.services?.background_jobs === 'running' ? 'mem-good' : 'mem-error'}`}>
                        ● {systemHealth.services?.background_jobs === 'running' ? `Running (${systemHealth.services?.job_count || 0} jobs)` : 'Stopped'}
                      </span>
                    </div>
                  </div>

                  {/* Configuration */}
                  <div className="mem-widget">
                    <div className="mem-widget-header">
                      <span className="mem-widget-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                          <circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 6v6M5.6 5.6l4.2 4.2m4.2 4.2l4.2 4.2M1 12h6m6 0h6M5.6 18.4l4.2-4.2m4.2-4.2l4.2-4.2"/>
                        </svg>
                        Configuration
                      </span>
                    </div>
                    <div className="mem-metric-row">
                      <span className="mem-metric-label">Claude (Anthropic)</span>
                      <span className={`mem-metric-value ${systemHealth.configuration?.claude ? 'mem-good' : 'mem-error'}`}>
                        {systemHealth.configuration?.claude ? '✓ Configured' : '✗ Missing'}
                      </span>
                    </div>
                    <div className="mem-metric-row">
                      <span className="mem-metric-label">OpenAI Embeddings</span>
                      <span className={`mem-metric-value ${systemHealth.configuration?.openai_embeddings ? 'mem-good' : 'mem-error'}`}>
                        {systemHealth.configuration?.openai_embeddings ? '✓ Configured' : '✗ Missing'}
                      </span>
                    </div>
                    <div className="mem-metric-row">
                      <span className="mem-metric-label">Azure Document Intelligence</span>
                      <span className={`mem-metric-value ${systemHealth.configuration?.azure_document_intelligence ? 'mem-good' : 'mem-small'}`}>
                        {systemHealth.configuration?.azure_document_intelligence ? '✓ Configured' : '✗ Missing'}
                      </span>
                    </div>
                    <div className="mem-metric-row">
                      <span className="mem-metric-label">Google OAuth</span>
                      <span className={`mem-metric-value ${systemHealth.configuration?.google_oauth ? 'mem-good' : 'mem-error'}`}>
                        {systemHealth.configuration?.google_oauth ? '✓ Configured' : '✗ Missing'}
                      </span>
                    </div>
                  </div>
                </>
              ) : (
                <div className="mem-widget">
                  <div className="mem-widget-header">
                    <span className="mem-widget-title">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                        <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
                      </svg>
                      System Status
                    </span>
                    <span className="mem-widget-badge mem-badge-warning">Loading...</span>
                  </div>
                  <div style={{ padding: '20px', textAlign: 'center', color: 'var(--alphawave-text-secondary)' }}>
                    Fetching system health data...
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
                Loaded: {memories.length} memories • {documents.length} docs • {conversations.length} chats
                {dashboardData.loading && ' • Loading...'}
              </>
            ) : (
              'Sign in to sync data'
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}

