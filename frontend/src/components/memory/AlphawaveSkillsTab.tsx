'use client';

import { useState, useEffect } from 'react';

/**
 * Nicole V7 Skills Tab - Integrated into Memory Dashboard
 * 
 * PURPOSE:
 *   Provides visibility into Nicole's skill system directly from the Memory Dashboard.
 *   Shows installed skills, their status, and allows health check operations.
 * 
 * FEATURES:
 *   - List all installed skills with status indicators
 *   - Filter by status (ready, needs_configuration, manual, etc.)
 *   - Run health checks on individual skills
 *   - View skill execution history
 *   - Mark skills as ready (admin action)
 * 
 * API ENDPOINTS:
 *   - GET /skills - List all skills
 *   - GET /skills/summary - Get status summary
 *   - POST /skills/{id}/health-check - Run health check
 *   - PUT /skills/{id}/status - Update skill status
 * 
 * Author: Nicole V7 Skills System
 * Date: December 5, 2025
 */

// Types for skill data
interface Skill {
  id: string;
  name: string;
  vendor: string;
  description: string;
  version: string;
  status: string;
  setup_status: string;
  executor: {
    type: string;
    entrypoint: string;
    timeout_seconds: number;
    requires_gpu: boolean;
  };
  capabilities: Array<{
    domain: string;
    description: string;
    tags: string[];
  }>;
  safety: {
    risk_level: string;
    review_status: string;
  };
  last_run_at: string | null;
  last_run_status: string | null;
  last_health_check_at: string | null;
  health_notes: string[];
  source: {
    url: string;
    imported_at: string | null;
  };
}

interface SkillsSummary {
  total: number;
  by_status: Record<string, number>;
  by_executor_type: Record<string, number>;
  ready_count: number;
  needs_attention: Array<{
    skill_id: string;
    name: string;
    status: string;
    executor_type: string;
  }>;
}

// API configuration - hardcoded to avoid Vercel env var caching issues
const API_BASE = 'https://api.nicole.alphawavetech.com';

// Sample data for development
const sampleSkills: Skill[] = [
  {
    id: 'local-example-python-skill',
    name: 'Example Python Skill',
    vendor: 'local',
    description: 'Sample python-based skill for QA',
    version: '1.0.0',
    status: 'installed',
    setup_status: 'needs_verification',
    executor: {
      type: 'python_script',
      entrypoint: 'main.py',
      timeout_seconds: 60,
      requires_gpu: false,
    },
    capabilities: [{ domain: 'testing', description: 'Demonstrates python execution', tags: [] }],
    safety: { risk_level: 'low', review_status: 'unreviewed' },
    last_run_at: '2025-12-03T02:42:00Z',
    last_run_status: 'success',
    last_health_check_at: null,
    health_notes: [],
    source: { url: 'local', imported_at: null },
  },
  {
    id: 'playwright-skill-playwright-browser-automation',
    name: 'Playwright Browser Automation',
    vendor: 'playwright-skill',
    description: 'Browser automation and testing skill',
    version: '0.1.0',
    status: 'installed',
    setup_status: 'manual_only',
    executor: {
      type: 'manual',
      entrypoint: 'README-driven',
      timeout_seconds: 300,
      requires_gpu: false,
    },
    capabilities: [{ domain: 'automation', description: 'Web browser automation', tags: ['browser', 'testing'] }],
    safety: { risk_level: 'medium', review_status: 'unreviewed' },
    last_run_at: null,
    last_run_status: null,
    last_health_check_at: null,
    health_notes: [],
    source: { url: 'https://github.com/lackeyjb/playwright-skill', imported_at: null },
  },
  {
    id: 'ios-simulator-skill',
    name: 'iOS Simulator Skill',
    vendor: 'ios-simulator-skill',
    description: 'Control iOS simulator for testing',
    version: '0.1.0',
    status: 'installed',
    setup_status: 'manual_only',
    executor: {
      type: 'manual',
      entrypoint: 'README-driven',
      timeout_seconds: 300,
      requires_gpu: false,
    },
    capabilities: [{ domain: 'mobile', description: 'iOS simulator control', tags: ['ios', 'simulator', 'mobile'] }],
    safety: { risk_level: 'low', review_status: 'unreviewed' },
    last_run_at: null,
    last_run_status: null,
    last_health_check_at: null,
    health_notes: [],
    source: { url: 'https://github.com/conorluddy/ios-simulator-skill', imported_at: null },
  },
];

const sampleSummary: SkillsSummary = {
  total: 3,
  by_status: { needs_verification: 1, manual_only: 2 },
  by_executor_type: { python_script: 1, manual: 2 },
  ready_count: 0,
  needs_attention: [
    { skill_id: 'local-example-python-skill', name: 'Example Python Skill', status: 'needs_verification', executor_type: 'python_script' },
  ],
};

interface AlphawaveSkillsTabProps {
  authToken?: string;
}

export function AlphawaveSkillsTab({ authToken }: AlphawaveSkillsTabProps) {
  const [skills, setSkills] = useState<Skill[]>(authToken ? [] : sampleSkills);
  const [summary, setSummary] = useState<SkillsSummary>(authToken ? {
    total: 0,
    by_status: {},
    by_executor_type: {},
    ready_count: 0,
    needs_attention: [],
  } : sampleSummary);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [loading, setLoading] = useState(false);
  const [healthCheckLoading, setHealthCheckLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch skills data
  const fetchSkills = async () => {
    if (!authToken) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/skills/`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        setSkills(data.skills || []);
      }
      
      // Fetch summary
      const summaryResponse = await fetch(`${API_BASE}/skills/summary`, {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
      });
      
      if (summaryResponse.ok) {
        const summaryData = await summaryResponse.json();
        setSummary(summaryData);
      }
    } catch (err) {
      console.error('Failed to fetch skills:', err);
      setError('Failed to load skills data');
    } finally {
      setLoading(false);
    }
  };

  // Run health check on a skill
  const runHealthCheck = async (skillId: string) => {
    if (!authToken) return;
    
    setHealthCheckLoading(skillId);
    
    try {
      const response = await fetch(`${API_BASE}/skills/${skillId}/health-check`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ run_tests: false, auto_install_deps: false }),
      });
      
      if (response.ok) {
        const result = await response.json();
        // Refresh skills list after health check
        await fetchSkills();
        alert(`Health check ${result.passed ? 'passed' : 'failed'}: ${result.notes?.join(', ') || 'No notes'}`);
      } else {
        throw new Error('Health check failed');
      }
    } catch (err) {
      console.error('Health check error:', err);
      alert('Health check failed. Check console for details.');
    } finally {
      setHealthCheckLoading(null);
    }
  };

  // Mark skill as ready
  const markReady = async (skillId: string) => {
    if (!authToken) return;
    
    try {
      const response = await fetch(`${API_BASE}/skills/${skillId}/status`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ setup_status: 'ready', notes: 'Manually marked ready via dashboard' }),
      });
      
      if (response.ok) {
        await fetchSkills();
      }
    } catch (err) {
      console.error('Failed to mark ready:', err);
    }
  };

  // Initial load
  useEffect(() => {
    const loadSkills = async () => {
      if (!authToken) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`${API_BASE}/skills/`, {
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        });
        
        if (response.ok) {
          const data = await response.json();
          setSkills(data.skills || []);
        }
        
        // Fetch summary
        const summaryResponse = await fetch(`${API_BASE}/skills/summary`, {
          headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json',
          },
        });
        
        if (summaryResponse.ok) {
          const summaryData = await summaryResponse.json();
          setSummary(summaryData);
        }
      } catch (err) {
        console.error('Failed to fetch skills:', err);
        setError('Failed to load skills data');
      } finally {
        setLoading(false);
      }
    };
    
    loadSkills();
  }, [authToken]);

  // Filter skills
  const filteredSkills = skills.filter(skill => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'executable') {
      return !['manual', 'manual_only'].includes(skill.setup_status) && skill.executor.type !== 'manual';
    }
    return skill.setup_status === statusFilter;
  });

  // Get status badge class
  const getStatusBadgeClass = (status: string): string => {
    switch (status) {
      case 'ready':
        return 'skill-status-ready';
      case 'needs_verification':
        return 'skill-status-verification';
      case 'needs_configuration':
        return 'skill-status-config';
      case 'manual_only':
        return 'skill-status-manual';
      case 'failed':
        return 'skill-status-failed';
      default:
        return 'skill-status-unknown';
    }
  };

  // Get executor type icon
  const getExecutorIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'python':
      case 'python_script':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="skill-exec-icon">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
            <path d="M9 9h6v6H9z"/>
          </svg>
        );
      case 'node':
      case 'node_script':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="skill-exec-icon">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        );
      case 'manual':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="skill-exec-icon">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
        );
      default:
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="skill-exec-icon">
            <path d="M4 17l6-6-6-6"/>
            <line x1="12" y1="19" x2="20" y2="19"/>
          </svg>
        );
    }
  };

  // If no auth token, show graceful fallback with sample data
  const isOfflineMode = !authToken;

  return (
    <div className="skills-tab">
      {/* Offline Mode Banner */}
      {isOfflineMode && (
        <div className="skills-offline-banner">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <div className="skills-offline-text">
            <strong>Preview Mode</strong>
            <span>Showing sample data. Sign in to view your actual skills.</span>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="skills-error-banner">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <span>{error}</span>
          <button onClick={() => setError(null)}>Dismiss</button>
        </div>
      )}

      {/* Summary Widget */}
      <div className="mem-widget">
        <div className="mem-widget-header">
          <span className="mem-widget-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
            </svg>
            Skills Status
          </span>
          <span className={`mem-widget-badge ${summary.ready_count > 0 ? 'mem-badge-success' : 'mem-badge-warning'}`}>
            {summary.ready_count} Ready
          </span>
        </div>
        <div className="mem-stat-grid">
          <div className="mem-stat-box">
            <div className="mem-stat-value mem-highlight">{summary.total}</div>
            <div className="mem-stat-label">Total</div>
          </div>
          <div className="mem-stat-box">
            <div className="mem-stat-value mem-success">{summary.ready_count}</div>
            <div className="mem-stat-label">Ready</div>
          </div>
          <div className="mem-stat-box">
            <div className="mem-stat-value mem-warning">{summary.needs_attention.length}</div>
            <div className="mem-stat-label">Need Attention</div>
          </div>
        </div>
      </div>

      {/* Filter Pills */}
      <div className="mem-filter-pills">
        {['all', 'ready', 'needs_verification', 'executable', 'manual_only'].map(filter => (
          <button
            key={filter}
            className={`mem-filter-pill ${statusFilter === filter ? 'mem-active' : ''}`}
            onClick={() => setStatusFilter(filter)}
          >
            {filter === 'all' ? 'All' : 
             filter === 'needs_verification' ? 'Needs Check' :
             filter === 'executable' ? 'Executable' :
             filter === 'manual_only' ? 'Manual' :
             filter.charAt(0).toUpperCase() + filter.slice(1)}
          </button>
        ))}
      </div>

      {/* Skills List */}
      <div className="skills-list">
        {filteredSkills.map(skill => (
          <div 
            key={skill.id} 
            className={`skill-item ${selectedSkill === skill.id ? 'skill-selected' : ''}`}
            onClick={() => setSelectedSkill(selectedSkill === skill.id ? null : skill.id)}
          >
            <div className="skill-item-header">
              <div className="skill-item-left">
                {getExecutorIcon(skill.executor.type)}
                <div className="skill-item-info">
                  <div className="skill-name">{skill.name}</div>
                  <div className="skill-vendor">{skill.vendor} • v{skill.version}</div>
                </div>
              </div>
              <span className={`skill-status-badge ${getStatusBadgeClass(skill.setup_status)}`}>
                {skill.setup_status.replace('_', ' ')}
              </span>
            </div>
            
            <div className="skill-description">{skill.description}</div>
            
            {/* Expanded details */}
            {selectedSkill === skill.id && (
              <div className="skill-details">
                <div className="skill-detail-row">
                  <span className="skill-detail-label">Executor:</span>
                  <span className="skill-detail-value">{skill.executor.type}</span>
                </div>
                <div className="skill-detail-row">
                  <span className="skill-detail-label">Entrypoint:</span>
                  <span className="skill-detail-value">{skill.executor.entrypoint}</span>
                </div>
                {skill.last_run_at && (
                  <div className="skill-detail-row">
                    <span className="skill-detail-label">Last Run:</span>
                    <span className={`skill-detail-value ${skill.last_run_status === 'success' ? 'skill-success' : 'skill-failed'}`}>
                      {skill.last_run_status} • {new Date(skill.last_run_at).toLocaleDateString()}
                    </span>
                  </div>
                )}
                {skill.health_notes.length > 0 && (
                  <div className="skill-health-notes">
                    <span className="skill-detail-label">Notes:</span>
                    <ul>
                      {skill.health_notes.slice(0, 3).map((note, idx) => (
                        <li key={idx}>{note}</li>
                      ))}
                    </ul>
                  </div>
                )}
                
                {/* Action buttons */}
                <div className="skill-actions">
                  {skill.executor.type !== 'manual' && skill.setup_status !== 'ready' && (
                    <>
                      <button 
                        className="skill-action-btn skill-btn-check"
                        onClick={(e) => { e.stopPropagation(); runHealthCheck(skill.id); }}
                        disabled={healthCheckLoading === skill.id}
                      >
                        {healthCheckLoading === skill.id ? (
                          <span className="skill-btn-loading">Checking...</span>
                        ) : (
                          <>
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                              <polyline points="22 4 12 14.01 9 11.01"/>
                            </svg>
                            Health Check
                          </>
                        )}
                      </button>
                      <button 
                        className="skill-action-btn skill-btn-ready"
                        onClick={(e) => { e.stopPropagation(); markReady(skill.id); }}
                      >
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                          <path d="M9 12l2 2 4-4"/>
                          <circle cx="12" cy="12" r="10"/>
                        </svg>
                        Mark Ready
                      </button>
                    </>
                  )}
                  {skill.source.url && skill.source.url !== 'local' && (
                    <a 
                      href={skill.source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="skill-action-btn skill-btn-source"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                        <polyline points="15 3 21 3 21 9"/>
                        <line x1="10" y1="14" x2="21" y2="3"/>
                      </svg>
                      Source
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
        
        {filteredSkills.length === 0 && (
          <div className="skills-empty">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <circle cx="12" cy="12" r="10"/>
              <line x1="8" y1="12" x2="16" y2="12"/>
            </svg>
            <p>No skills match the current filter</p>
          </div>
        )}
      </div>

      {/* Refresh Button */}
      <div className="skills-footer">
        <button 
          className="skill-refresh-btn"
          onClick={() => fetchSkills()}
          disabled={loading}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className={loading ? 'skill-spinning' : ''}>
            <path d="M23 4v6h-6"/>
            <path d="M1 20v-6h6"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          {loading ? 'Refreshing...' : 'Refresh Skills'}
        </button>
      </div>
    </div>
  );
}

export default AlphawaveSkillsTab;

