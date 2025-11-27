'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

interface Agent {
  id: string;
  name: string;
  icon: string;
  status: 'idle' | 'working' | 'complete' | 'error';
  progress: number;
  task: string;
}

interface FileItem {
  name: string;
  type: 'folder' | 'html' | 'css' | 'js' | 'json' | 'image' | 'md';
  status?: 'modified' | 'new' | 'error';
  active?: boolean;
  children?: FileItem[];
}

interface WorkflowStep {
  id: number;
  name: string;
  desc: string;
  status: 'pending' | 'active' | 'complete';
}

interface Activity {
  agent: string;
  action: string;
  time: string;
}

interface AlphawaveVibeWorkspaceProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Vibe Coding Dashboard - THE LEGEND
 * A full-featured coding workspace with agents, file tree, preview, and workflow visualization
 */
export function AlphawaveVibeWorkspace({ isOpen, onClose }: AlphawaveVibeWorkspaceProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [projectName, setProjectName] = useState('Untitled Project');
  const [statusText, setStatusText] = useState('Ready');
  const [isWorking, setIsWorking] = useState(false);
  const [currentDevice, setCurrentDevice] = useState<'mobile' | 'tablet' | 'desktop'>('desktop');
  const [currentView, setCurrentView] = useState<'preview' | 'code' | 'split'>('preview');
  const [activityCollapsed, setActivityCollapsed] = useState(false);

  const [files] = useState<FileItem[]>([
    { name: 'src', type: 'folder', children: [
      { name: 'index.html', type: 'html', status: 'modified', active: true },
      { name: 'styles.css', type: 'css' },
      { name: 'app.js', type: 'js', status: 'new' }
    ]},
    { name: 'public', type: 'folder', children: [
      { name: 'logo.svg', type: 'image' },
      { name: 'favicon.ico', type: 'image' }
    ]},
    { name: 'package.json', type: 'json' },
    { name: 'README.md', type: 'md' }
  ]);

  const [agents, setAgents] = useState<Agent[]>([
    { id: 'planning', name: 'Planning', icon: '🎯', status: 'idle', progress: 0, task: 'Awaiting instructions' },
    { id: 'research', name: 'Research', icon: '🔍', status: 'idle', progress: 0, task: 'Awaiting instructions' },
    { id: 'qa', name: 'QA', icon: '🧪', status: 'idle', progress: 0, task: 'Awaiting instructions' },
    { id: 'approver', name: 'Approver', icon: '✅', status: 'idle', progress: 0, task: 'Awaiting instructions' },
    { id: 'lead', name: 'Team Lead', icon: '👑', status: 'idle', progress: 0, task: 'Monitoring workflow' }
  ]);

  const [workflow, setWorkflow] = useState<WorkflowStep[]>([
    { id: 1, name: 'Plan', desc: 'Structure & scope', status: 'pending' },
    { id: 2, name: 'Research', desc: 'Best practices', status: 'pending' },
    { id: 3, name: 'Build', desc: 'Implementation', status: 'pending' },
    { id: 4, name: 'Test', desc: 'Quality checks', status: 'pending' },
    { id: 5, name: 'Ship', desc: 'Deploy & deliver', status: 'pending' }
  ]);

  const [activities, setActivities] = useState<Activity[]>([]);

  // Particle system
  useEffect(() => {
    if (!isOpen || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const particles: Array<{
      x: number;
      y: number;
      size: number;
      speedX: number;
      speedY: number;
      opacity: number;
    }> = [];

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    };

    resize();
    window.addEventListener('resize', resize);

    // Create particles
    for (let i = 0; i < 50; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        size: Math.random() * 2 + 0.5,
        speedX: (Math.random() - 0.5) * 0.3,
        speedY: (Math.random() - 0.5) * 0.3,
        opacity: Math.random() * 0.5 + 0.2
      });
    }

    let animationId: number;
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach(p => {
        p.x += p.speedX;
        p.y += p.speedY;

        if (p.x < 0 || p.x > canvas.width) p.speedX *= -1;
        if (p.y < 0 || p.y > canvas.height) p.speedY *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(184, 168, 212, ${p.opacity})`;
        ctx.fill();
      });

      // Draw connections
      particles.forEach((p1, i) => {
        particles.slice(i + 1).forEach(p2 => {
          const dist = Math.hypot(p1.x - p2.x, p1.y - p2.y);
          if (dist < 100) {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(184, 168, 212, ${0.1 * (1 - dist / 100)})`;
            ctx.stroke();
          }
        });
      });

      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationId);
    };
  }, [isOpen]);

  const updateAgent = useCallback((id: string, updates: Partial<Agent>) => {
    setAgents(prev => prev.map(a => a.id === id ? { ...a, ...updates } : a));
  }, []);

  const updateWorkflow = useCallback((stepId: number, status: WorkflowStep['status']) => {
    setWorkflow(prev => prev.map(s => s.id === stepId ? { ...s, status } : s));
  }, []);

  const addActivity = useCallback((agent: string, action: string) => {
    setActivities(prev => [{ agent, action, time: 'Just now' }, ...prev].slice(0, 10));
  }, []);

  const animateProgress = (agentId: string, target: number, duration: number): Promise<void> => {
    return new Promise(resolve => {
      const start = Date.now();
      const agent = agents.find(a => a.id === agentId);
      const startProgress = agent?.progress || 0;

      const tick = () => {
        const elapsed = Date.now() - start;
        const progress = Math.min(startProgress + (target - startProgress) * (elapsed / duration), target);
        updateAgent(agentId, { progress: Math.round(progress) });

        if (elapsed < duration) {
          requestAnimationFrame(tick);
        } else {
          resolve();
        }
      };
      tick();
    });
  };

  const simulateWork = async () => {
    setIsWorking(true);
    setStatusText('Building...');

    // Planning
    updateAgent('planning', { status: 'working', progress: 0, task: 'Analyzing request...' });
    updateWorkflow(1, 'active');
    addActivity('Planning', 'started analyzing your request');

    await animateProgress('planning', 100, 800);
    updateAgent('planning', { status: 'complete', progress: 100, task: 'Structure defined' });
    updateWorkflow(1, 'complete');
    addActivity('Planning', 'completed site architecture');

    // Research
    updateAgent('research', { status: 'working', progress: 0, task: 'Finding best practices...' });
    updateWorkflow(2, 'active');
    addActivity('Research', 'started researching patterns');

    await animateProgress('research', 100, 1000);
    updateAgent('research', { status: 'complete', progress: 100, task: 'Found 5 references' });
    updateWorkflow(2, 'complete');
    addActivity('Research', 'found design inspiration');

    // Building
    updateWorkflow(3, 'active');
    addActivity('Team Lead', 'coordinating build phase');

    // QA
    updateAgent('qa', { status: 'working', progress: 0, task: 'Testing accessibility...' });
    addActivity('QA', 'started quality checks');

    await animateProgress('qa', 100, 1200);
    updateAgent('qa', { status: 'complete', progress: 100, task: 'All tests passed' });
    updateWorkflow(3, 'complete');
    addActivity('QA', 'verified accessibility standards');

    // Approver
    updateAgent('approver', { status: 'working', progress: 0, task: 'Final review...' });
    updateWorkflow(4, 'active');
    addActivity('Approver', 'started final review');

    await animateProgress('approver', 100, 600);
    updateAgent('approver', { status: 'complete', progress: 100, task: 'Approved ✓' });
    updateWorkflow(4, 'complete');
    addActivity('Approver', 'approved the build');

    // Lead
    updateAgent('lead', { status: 'working', progress: 0, task: 'Preparing delivery...' });
    updateWorkflow(5, 'active');

    await animateProgress('lead', 100, 400);
    updateAgent('lead', { status: 'complete', progress: 100, task: 'Ready to ship' });
    updateWorkflow(5, 'complete');
    addActivity('Team Lead', 'build ready for deployment');

    setIsWorking(false);
    setStatusText('Ready to Deploy');
  };

  const renderFileItem = (item: FileItem, depth: number = 0): React.ReactNode => {
    const isFolder = item.type === 'folder';
    
    return (
      <div key={item.name}>
        <div 
          className={`vibe-file-item ${isFolder ? 'folder' : ''} ${item.active ? 'active' : ''}`}
          style={{ paddingLeft: `${16 + depth * 16}px` }}
        >
          <span className={`vibe-file-icon ${item.type}`}>
            {isFolder ? (
              <svg viewBox="0 0 24 24" fill="none"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            ) : (
              <svg viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            )}
          </span>
          <span className="vibe-file-name">{item.name}</span>
          {item.status && <span className={`vibe-file-status ${item.status}`} />}
        </div>
        {item.children && (
          <div className="vibe-file-children">
            {item.children.map(child => renderFileItem(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <aside className={`vibe-workspace ${isOpen ? 'open' : ''}`}>
      <canvas ref={canvasRef} className="vibe-particle-canvas" />
      
      <div className="vibe-inner">
        {/* Project Bar */}
        <div className="vibe-project-bar">
          <div className="vibe-project-bar-left">
            <div className="vibe-project-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <polygon points="12 2 2 7 12 12 22 7 12 2"/>
                <polyline points="2 17 12 22 22 17"/>
                <polyline points="2 12 12 17 22 12"/>
              </svg>
            </div>
            <div className="vibe-project-info">
              <input
                type="text"
                className="vibe-project-name-input"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                spellCheck={false}
              />
              <div className="vibe-project-status">
                <span className={`vibe-status-dot ${isWorking ? 'working' : ''}`} />
                <span>{statusText}</span>
              </div>
            </div>
          </div>

          <div className="vibe-project-bar-center">
            {(['mobile', 'tablet', 'desktop'] as const).map(device => (
              <button
                key={device}
                className={`vibe-device-btn ${currentDevice === device ? 'active' : ''}`}
                onClick={() => setCurrentDevice(device)}
                title={device}
              >
                {device === 'mobile' && <svg viewBox="0 0 24 24" fill="none"><rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>}
                {device === 'tablet' && <svg viewBox="0 0 24 24" fill="none"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>}
                {device === 'desktop' && <svg viewBox="0 0 24 24" fill="none"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>}
              </button>
            ))}

            <div className="vibe-view-tabs">
              {(['preview', 'code', 'split'] as const).map(view => (
                <button
                  key={view}
                  className={`vibe-view-tab ${currentView === view ? 'active' : ''}`}
                  onClick={() => setCurrentView(view)}
                >
                  {view.charAt(0).toUpperCase() + view.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="vibe-project-bar-right">
            <button className="vibe-build-btn" onClick={simulateWork}>
              <svg viewBox="0 0 24 24" fill="none"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
              <span>Deploy</span>
            </button>
            <button className="vibe-close-btn" onClick={onClose}>
              <svg viewBox="0 0 24 24" fill="none"><path d="M18 6L6 18M6 6l12 12"/></svg>
            </button>
          </div>
        </div>

        {/* Main Workspace */}
        <div className="vibe-workspace-main">
          {/* Files Panel */}
          <div className="vibe-files-panel">
            <div className="vibe-panel-header">
              <span className="vibe-panel-title">Explorer</span>
              <div className="vibe-panel-actions">
                <button className="vibe-panel-action-btn" title="New File">
                  <svg viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
                </button>
                <button className="vibe-panel-action-btn" title="New Folder">
                  <svg viewBox="0 0 24 24" fill="none"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                </button>
              </div>
            </div>

            <div className="vibe-files-tree">
              {files.map(f => renderFileItem(f))}
            </div>

            <div className="vibe-files-footer">
              <button className="vibe-new-file-btn">
                <svg viewBox="0 0 24 24" fill="none"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Add File
              </button>
            </div>
          </div>

          {/* Preview Panel */}
          <div className={`vibe-preview-panel ${currentView === 'code' ? 'hidden' : ''}`}>
            <div className="vibe-preview-container">
              <div className={`vibe-device-frame ${currentDevice}`}>
                <div className="vibe-device-header">
                  <div className="vibe-device-dots">
                    <span className="vibe-device-dot red" />
                    <span className="vibe-device-dot yellow" />
                    <span className="vibe-device-dot green" />
                  </div>
                  <div className="vibe-device-url">
                    <svg viewBox="0 0 24 24" fill="none"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                    <span>localhost:3000</span>
                  </div>
                </div>
                <div className="vibe-device-content">
                  <div className="vibe-preview-placeholder">
                    <div className="vibe-preview-placeholder-icon">
                      <svg viewBox="0 0 24 24" fill="none"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
                    </div>
                    <h3>Ready to Create</h3>
                    <p>Describe what you want to build in the chat. I&apos;ll handle the rest.</p>
                    <div className="vibe-shortcut">
                      <kbd>⌘</kbd> + <kbd>Enter</kbd> to send
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Agents Panel */}
          <div className="vibe-agents-panel">
            <div className="vibe-panel-header">
              <span className="vibe-panel-title">Agents</span>
            </div>

            <div className="vibe-agents-list">
              {agents.map(agent => (
                <div key={agent.id} className={`vibe-agent-card ${agent.status}`}>
                  <div className="vibe-agent-header">
                    <div className={`vibe-agent-icon ${agent.id}`}>{agent.icon}</div>
                    <div className="vibe-agent-info">
                      <div className="vibe-agent-name">{agent.name}</div>
                      <div className={`vibe-agent-status-text ${agent.status}`}>
                        {agent.status === 'working' && <span className="vibe-spinner" />}
                        {agent.status === 'idle' ? 'Ready' : agent.status === 'working' ? 'Working' : 'Complete'}
                      </div>
                    </div>
                  </div>
                  <div className="vibe-agent-progress">
                    <div className="vibe-agent-progress-bar">
                      <div className={`vibe-agent-progress-fill ${agent.status}`} style={{ width: `${agent.progress}%` }} />
                    </div>
                    <div className="vibe-agent-progress-text">
                      <span>{agent.task}</span>
                      <span>{agent.progress}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Workflow */}
            <div className="vibe-workflow-section">
              <div className="vibe-workflow-title">Pipeline</div>
              <div className="vibe-workflow-visual">
                {workflow.map(step => (
                  <div key={step.id} className={`vibe-workflow-step ${step.status}`}>
                    <div className="vibe-workflow-step-num">
                      {step.status === 'complete' ? '✓' : step.id}
                    </div>
                    <div className="vibe-workflow-step-info">
                      <div className="vibe-workflow-step-name">{step.name}</div>
                      <div className="vibe-workflow-step-desc">{step.desc}</div>
                    </div>
                    {step.status === 'complete' && (
                      <div className="vibe-workflow-step-check">
                        <svg viewBox="0 0 24 24" fill="none"><polyline points="20 6 9 17 4 12"/></svg>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Activity Feed */}
        <div className={`vibe-activity-feed ${activityCollapsed ? 'collapsed' : ''}`}>
          <div className="vibe-activity-header" onClick={() => setActivityCollapsed(!activityCollapsed)}>
            <div className="vibe-activity-title">
              <svg viewBox="0 0 24 24" fill="none"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
              Activity
              <span className="vibe-activity-badge">{activities.length}</span>
            </div>
            <button className="vibe-activity-toggle">
              <svg viewBox="0 0 24 24" fill="none"><path d="M6 9l6 6 6-6"/></svg>
            </button>
          </div>
          <div className="vibe-activity-list">
            {activities.slice(0, 5).map((a, i) => (
              <div key={i} className="vibe-activity-item">
                <span className="vibe-activity-dot" />
                <div className="vibe-activity-content">
                  <div className="vibe-activity-text">
                    <strong>{a.agent}</strong> {a.action}
                  </div>
                  <div className="vibe-activity-time">{a.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}

