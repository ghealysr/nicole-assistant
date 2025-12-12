'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useVibeProjects, useVibeProject, type VibeProject, type ProjectType, type VibeActivity } from '@/lib/hooks/useVibeProject';

interface FileItem {
  name: string;
  type: 'folder' | 'html' | 'css' | 'js' | 'json' | 'image' | 'md' | 'tsx' | 'ts';
  path?: string;
  status?: 'modified' | 'new' | 'error';
  active?: boolean;
  children?: FileItem[];
}

interface AlphawaveVibeWorkspaceProps {
  isOpen: boolean;
  onClose: () => void;
}

type ViewMode = 'projects' | 'workspace';

/**
 * AlphaWave Vibe Dashboard
 * Full-featured coding workspace with project management, agents, and build pipeline
 */
export function AlphawaveVibeWorkspace({ isOpen, onClose }: AlphawaveVibeWorkspaceProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('projects');
  const [currentDevice, setCurrentDevice] = useState<'mobile' | 'tablet' | 'desktop'>('desktop');
  const [currentView, setCurrentView] = useState<'preview' | 'code' | 'split'>('split');
  const [activityCollapsed, setActivityCollapsed] = useState(false);
  const [activeFilePath, setActiveFilePath] = useState<string | null>(null);
  const [openTabs, setOpenTabs] = useState<string[]>([]);
  
  // Project creation form
  const [showNewProjectForm, setShowNewProjectForm] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectType, setNewProjectType] = useState<ProjectType>('website');
  const [newClientName, setNewClientName] = useState('');
  const [newClientEmail, setNewClientEmail] = useState('');
  
  // Intake chat
  const [intakeMessage, setIntakeMessage] = useState('');
  
  // Local activity state for immediate UI feedback (will be replaced by API activities)
  const [localActivities, setLocalActivities] = useState<Array<{
    agent: string;
    action: string;
    time: string;
  }>>([]);
  
  // Hooks
  const { 
    projects, 
    loading: projectsLoading, 
    error: projectsError,
    fetchProjects, 
    createProject 
  } = useVibeProjects();
  
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  
  const {
    project,
    agents,
    workflow,
    files,
    fileTree,
    intakeHistory,
    activities,
    loading: projectLoading,
    error: projectError,
    operationStates,
    isAnyOperationLoading,
    canRunPipeline,
    canApprove,
    canDeploy,
    totalApiCost,
    fetchProject,
    fetchFiles,
    fetchActivities,
    runIntake,
    runPlanning,
    runBuild,
    runQA,
    runReview,
    approveProject,
    deployProject,
    runPipeline,
    clearIntakeHistory,
    clearError,
  } = useVibeProject(selectedProjectId || undefined);

  // Fetch projects on mount
  useEffect(() => {
    if (isOpen) {
      fetchProjects();
    }
  }, [isOpen, fetchProjects]);

  // Add activity
  const addActivity = useCallback((agent: string, action: string) => {
    setLocalActivities(prev => [
      { agent, action, time: 'Just now' },
      ...prev.slice(0, 9)
    ]);
  }, []);
  
  // Format activity time
  const formatActivityTime = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };
  
  // Combine local and API activities for display
  const combinedActivities = useMemo(() => {
    const apiFormatted = (activities || []).map(a => ({
      agent: a.agent_name || 'System',
      action: a.description,
      time: formatActivityTime(a.created_at),
    }));
    
    // Local activities first (most recent), then API activities
    return [...localActivities, ...apiFormatted].slice(0, 10);
  }, [localActivities, activities]);

  // Create new project
  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;
    
    const newProject = await createProject(
      newProjectName,
      newProjectType,
      newClientName || undefined,
      newClientEmail || undefined
    );
    
    if (newProject) {
      setShowNewProjectForm(false);
      setNewProjectName('');
      setNewClientName('');
      setNewClientEmail('');
      setSelectedProjectId(newProject.project_id);
      setViewMode('workspace');
      addActivity('System', `Created project "${newProject.name}"`);
    }
  };

  // Open project
  const handleOpenProject = (proj: VibeProject) => {
    setSelectedProjectId(proj.project_id);
    setViewMode('workspace');
    clearIntakeHistory();
    addActivity('System', `Opened project "${proj.name}"`);
  };

  // Send intake message
  const handleSendIntake = async () => {
    if (!intakeMessage.trim() || !selectedProjectId) return;
    
    const message = intakeMessage;
    setIntakeMessage('');
    addActivity('Intake', `Processing: "${message.slice(0, 40)}..."`);
    
    const result = await runIntake(selectedProjectId, message);
    
    if (result?.brief) {
      addActivity('Intake', 'Brief extracted - ready for planning');
    }
  };

  // Run build pipeline
  const handleRunPipeline = async () => {
    if (!selectedProjectId || !canRunPipeline) {
      addActivity('Pipeline', project?.status === 'intake' 
        ? 'Complete intake first' 
        : 'Cannot run pipeline in current state');
      return;
    }
    
    addActivity('Pipeline', 'Starting automated build...');
    
    try {
      // Use the combined pipeline runner which handles state properly
      const success = await runPipeline(selectedProjectId);
      
      if (success) {
        addActivity('Pipeline', 'Pipeline completed successfully!');
      } else {
        addActivity('Pipeline', 'Pipeline stopped - check status for details');
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Pipeline failed';
      addActivity('Pipeline', `Error: ${message}`);
    }
  };

  const handleDeploy = async () => {
    if (!selectedProjectId) return;
    addActivity('Deploy', 'Deploying project...');
    const ok = await deployProject(selectedProjectId);
    addActivity('Deploy', ok ? 'Deployment marked complete' : 'Deployment failed');
  };

  // Handle file selection
  const handleFileClick = (filePath: string) => {
    setActiveFilePath(filePath);
    if (!openTabs.includes(filePath)) {
      setOpenTabs(prev => [...prev, filePath]);
    }
  };

  // Auto-select first file after build
  useEffect(() => {
    if (!activeFilePath && files.length > 0) {
      const first = files[0].file_path;
      setActiveFilePath(first);
      setOpenTabs([first]);
    }
  }, [files, activeFilePath]);

  // Get file content
  const getFileContent = useCallback((filePath: string) => {
    return files.find(f => f.file_path === filePath)?.content || '';
  }, [files]);

  // Get file language
  const getFileLanguage = (filePath: string) => {
    const ext = filePath.split('.').pop() || '';
    const langMap: Record<string, string> = {
      tsx: 'typescript',
      ts: 'typescript',
      jsx: 'javascript',
      js: 'javascript',
      css: 'css',
      json: 'json',
      md: 'markdown',
      html: 'html',
    };
    return langMap[ext] || 'text';
  };

  // Convert file tree from API to UI format (memoized)
  const convertFileTreeHelper = useCallback((items: typeof fileTree): FileItem[] => {
    return items.map(item => ({
      name: item.name,
      type: (item.type === 'folder' ? 'folder' : item.type) as FileItem['type'],
      path: item.path,
      children: item.children ? convertFileTreeHelper(item.children) : undefined,
    }));
  }, []);
  
  const convertedFileTree = useMemo(() => 
    convertFileTreeHelper(fileTree), 
    [fileTree, convertFileTreeHelper]
  );

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

  // Render file tree item
  const renderFileItem = (item: FileItem, depth: number = 0): React.ReactNode => {
    const isFolder = item.type === 'folder';
    const isActive = item.path === activeFilePath;
    
    return (
      <div key={item.path || item.name}>
        <div 
          className={`vibe-file-item ${isFolder ? 'folder' : ''} ${isActive ? 'active' : ''}`}
          style={{ paddingLeft: `${16 + depth * 16}px` }}
          onClick={() => !isFolder && item.path && handleFileClick(item.path)}
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

  // Render syntax highlighted code
  const renderSyntaxHighlightedLine = (line: string, language: string): React.ReactNode => {
    if (!line) return <span>&nbsp;</span>;

    if (language === 'typescript' || language === 'javascript') {
      const keywords = ['const', 'let', 'var', 'function', 'async', 'await', 'return', 'if', 'else', 'try', 'catch', 'import', 'export', 'from', 'class', 'new', 'throw', 'interface', 'type'];
      
      return (
        <span>
          {line.split(/(\s+|[{}()[\];,.]|'[^']*'|"[^"]*"|`[^`]*`|\b(?:const|let|var|function|async|await|return|if|else|try|catch|import|export|from|class|new|throw|interface|type|true|false|null|undefined)\b)/g).map((part, i) => {
            if (keywords.includes(part)) {
              return <span key={i} className="code-keyword">{part}</span>;
            }
            if (/^['"`].*['"`]$/.test(part)) {
              return <span key={i} className="code-string">{part}</span>;
            }
            if (/^\d+$/.test(part)) {
              return <span key={i} className="code-number">{part}</span>;
            }
            return <span key={i}>{part}</span>;
          })}
        </span>
      );
    }

    if (language === 'css') {
      if (line.trim().startsWith('/*') || line.trim().startsWith('*')) {
        return <span className="code-comment">{line}</span>;
      }
      if (line.includes(':') && !line.includes('://')) {
        const [prop, ...valueParts] = line.split(':');
        const value = valueParts.join(':');
        return (
          <span>
            <span className="code-attr">{prop}</span>
            <span>:</span>
            <span className="code-value">{value}</span>
          </span>
        );
      }
      return <span>{line}</span>;
    }

    return <span>{line}</span>;
  };

  // Get status badge color
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      intake: 'bg-blue-500',
      planning: 'bg-yellow-500',
      building: 'bg-orange-500',
      qa: 'bg-purple-500',
      review: 'bg-indigo-500',
      approved: 'bg-green-500',
      deployed: 'bg-emerald-500',
      delivered: 'bg-teal-500',
    };
    return colors[status] || 'bg-gray-500';
  };

  // ============================================================================
  // PROJECTS LIST VIEW
  // ============================================================================
  
  const renderProjectsView = () => (
    <div className="vibe-projects-view">
      {(projectsError || projectError) && (
        <div className="vibe-error" style={{ marginBottom: 16 }}>
          {projectsError || projectError}
        </div>
      )}
      <div className="vibe-projects-header">
        <div className="vibe-projects-title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <polygon points="12 2 2 7 12 12 22 7 12 2"/>
            <polyline points="2 17 12 22 22 17"/>
            <polyline points="2 12 12 17 22 12"/>
          </svg>
          <span>AlphaWave Vibe</span>
        </div>
        <button 
          className="vibe-new-project-btn"
          onClick={() => setShowNewProjectForm(true)}
        >
          <svg viewBox="0 0 24 24" fill="none"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          New Project
        </button>
      </div>

      {/* New Project Form */}
      {showNewProjectForm && (
        <div className="vibe-new-project-form">
          <h3>Create New Project</h3>
          
          <div className="vibe-form-group">
            <label>Project Name</label>
            <input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="My Awesome Website"
              autoFocus
            />
          </div>
          
          <div className="vibe-form-group">
            <label>Project Type</label>
            <div className="vibe-type-selector">
              {(['website', 'chatbot', 'assistant', 'integration'] as ProjectType[]).map(type => (
                <button
                  key={type}
                  className={`vibe-type-option ${newProjectType === type ? 'active' : ''}`}
                  onClick={() => setNewProjectType(type)}
                >
                  {type === 'website' && '🌐'}
                  {type === 'chatbot' && '💬'}
                  {type === 'assistant' && '🤖'}
                  {type === 'integration' && '🔗'}
                  <span>{type.charAt(0).toUpperCase() + type.slice(1)}</span>
                </button>
              ))}
            </div>
          </div>
          
          <div className="vibe-form-row">
            <div className="vibe-form-group">
              <label>Client Name (optional)</label>
              <input
                type="text"
                value={newClientName}
                onChange={(e) => setNewClientName(e.target.value)}
                placeholder="Business Name"
              />
            </div>
            <div className="vibe-form-group">
              <label>Client Email (optional)</label>
              <input
                type="email"
                value={newClientEmail}
                onChange={(e) => setNewClientEmail(e.target.value)}
                placeholder="client@example.com"
              />
            </div>
          </div>
          
          <div className="vibe-form-actions">
            <button 
              className="vibe-btn-secondary"
              onClick={() => setShowNewProjectForm(false)}
            >
              Cancel
            </button>
            <button 
              className="vibe-btn-primary"
              onClick={handleCreateProject}
              disabled={!newProjectName.trim()}
            >
              Create Project
            </button>
          </div>
        </div>
      )}

      {/* Projects Grid */}
      <div className="vibe-projects-grid">
        {projectsLoading && (
          <div className="vibe-loading">Loading projects...</div>
        )}
        
        {projectsError && (
          <div className="vibe-error">{projectsError}</div>
        )}
        
        {!projectsLoading && projects.length === 0 && !showNewProjectForm && (
          <div className="vibe-empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
              <polygon points="12 2 2 7 12 12 22 7 12 2"/>
              <polyline points="2 17 12 22 22 17"/>
              <polyline points="2 12 12 17 22 12"/>
            </svg>
            <h3>No Projects Yet</h3>
            <p>Create your first project to get started</p>
            <button 
              className="vibe-btn-primary"
              onClick={() => setShowNewProjectForm(true)}
            >
              Create Project
            </button>
          </div>
        )}
        
        {projects.map(proj => (
          <div 
            key={proj.project_id} 
            className="vibe-project-card"
            onClick={() => handleOpenProject(proj)}
          >
            <div className="vibe-project-card-header">
              <span className="vibe-project-type-icon">
                {proj.project_type === 'website' && '🌐'}
                {proj.project_type === 'chatbot' && '💬'}
                {proj.project_type === 'assistant' && '🤖'}
                {proj.project_type === 'integration' && '🔗'}
              </span>
              <span className={`vibe-project-status-badge ${getStatusColor(proj.status)}`}>
                {proj.status}
              </span>
            </div>
            <h4 className="vibe-project-card-title">{proj.name}</h4>
            {proj.client_name && (
              <p className="vibe-project-card-client">{proj.client_name}</p>
            )}
            <div className="vibe-project-card-footer">
              <span className="vibe-project-card-date">
                {new Date(proj.updated_at).toLocaleDateString()}
              </span>
              {proj.preview_url && (
                <a 
                  href={proj.preview_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="vibe-project-card-link"
                  onClick={(e) => e.stopPropagation()}
                >
                  Preview →
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  // ============================================================================
  // WORKSPACE VIEW
  // ============================================================================
  
  const renderWorkspaceView = () => (
    <>
      {(projectsError || projectError) && (
        <div className="vibe-error" style={{ marginBottom: 12, marginLeft: 16, marginRight: 16 }}>
          {projectsError || projectError}
        </div>
      )}
      {/* Project Bar */}
      <div className="vibe-project-bar">
        <div className="vibe-project-bar-left">
          <button 
            className="vibe-back-btn"
            onClick={() => {
              setViewMode('projects');
              setSelectedProjectId(null);
            }}
          >
            <svg viewBox="0 0 24 24" fill="none"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
          </button>
          <div className="vibe-project-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <polygon points="12 2 2 7 12 12 22 7 12 2"/>
              <polyline points="2 17 12 22 22 17"/>
              <polyline points="2 12 12 17 22 12"/>
            </svg>
          </div>
          <div className="vibe-project-info">
            <div className="vibe-project-name">{project?.name || 'Loading...'}</div>
            <div className="vibe-project-status">
              <span className={`vibe-status-dot ${projectLoading ? 'working' : ''}`} />
              <span>{project?.status || 'Loading'}</span>
              {project?.client_name && <span className="vibe-client-name">• {project.client_name}</span>}
            </div>
            {(project?.preview_url || project?.production_url) && (
              <div className="vibe-project-links">
                {project.preview_url && <a href={project.preview_url} target="_blank" rel="noreferrer">Preview</a>}
                {project.production_url && <a href={project.production_url} target="_blank" rel="noreferrer">Live</a>}
              </div>
            )}
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
          {/* API Cost Display */}
          {totalApiCost > 0 && (
            <span className="vibe-api-cost" title="Estimated API cost for this session">
              ${totalApiCost.toFixed(4)}
            </span>
          )}
          
          {/* Deploy Button */}
          {canDeploy && (
            <button 
              className="vibe-deploy-btn" 
              onClick={handleDeploy}
              disabled={operationStates.deploy.loading}
            >
              {operationStates.deploy.loading ? (
                <span className="vibe-spinner" />
              ) : (
                <svg viewBox="0 0 24 24" fill="none"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
              )}
              <span>{operationStates.deploy.loading ? 'Deploying...' : 'Deploy'}</span>
            </button>
          )}
          
          {/* Pipeline Button */}
          {!canDeploy && project?.status !== 'deployed' && (
            <button 
              className="vibe-build-btn"
              onClick={handleRunPipeline}
              disabled={!canRunPipeline || isAnyOperationLoading}
            >
              {isAnyOperationLoading ? (
                <span className="vibe-spinner" />
              ) : (
                <svg viewBox="0 0 24 24" fill="none"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
              )}
              <span>{isAnyOperationLoading ? 'Working...' : 'Run Pipeline'}</span>
            </button>
          )}
          
          {/* Approve Button */}
          {canApprove && (
            <button 
              className="vibe-approve-btn"
              onClick={() => selectedProjectId && approveProject(selectedProjectId)}
              disabled={operationStates.approve.loading}
            >
              {operationStates.approve.loading ? (
                <span className="vibe-spinner" />
              ) : (
                <svg viewBox="0 0 24 24" fill="none"><polyline points="20 6 9 17 4 12"/></svg>
              )}
              <span>{operationStates.approve.loading ? 'Approving...' : 'Approve'}</span>
            </button>
          )}
          
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
            <button className="vibe-btn-secondary" onClick={() => {
              if (selectedProjectId) {
                fetchProject(selectedProjectId);
                fetchFiles(selectedProjectId);
                fetchActivities(selectedProjectId);
              }
            }}>
              Refresh
            </button>
          </div>

          <div className="vibe-files-tree">
            {convertedFileTree.length > 0 ? (
              convertedFileTree.map(f => renderFileItem(f))
            ) : (
              <div className="vibe-files-empty">
                {project?.status === 'intake' ? (
                  <p>Complete intake to generate files</p>
                ) : project?.status === 'planning' ? (
                  <p>Run planning to start build</p>
                ) : (
                  <p>No files yet</p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Preview Panel - Show Intake Chat or Preview */}
        <div className={`vibe-preview-panel ${currentView === 'code' ? 'hidden' : ''} ${currentView === 'split' ? 'split-view' : ''}`}>
          {project?.status === 'intake' ? (
            // Intake Chat Interface
            <div className="vibe-intake-chat">
              <div className="vibe-intake-header">
                <h3>📋 Project Intake</h3>
                <p>Tell me about the project. I&apos;ll gather requirements and create a brief.</p>
              </div>
              
              <div className="vibe-intake-messages">
                {intakeHistory.map((msg, i) => (
                  <div key={i} className={`vibe-intake-message ${msg.role}`}>
                    <div className="vibe-message-content">{msg.content}</div>
                  </div>
                ))}
                {intakeHistory.length === 0 && (
                  <div className="vibe-intake-starter">
                    <p>Start by describing the project:</p>
                    <ul>
                      <li>What type of business is this for?</li>
                      <li>What services/products do they offer?</li>
                      <li>What&apos;s the main goal of the website?</li>
                    </ul>
                  </div>
                )}
              </div>
              
              <div className="vibe-intake-input-area">
                <textarea
                  value={intakeMessage}
                  onChange={(e) => setIntakeMessage(e.target.value)}
                  placeholder="Describe the project..."
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendIntake();
                    }
                  }}
                />
                <button 
                  onClick={handleSendIntake}
                  disabled={!intakeMessage.trim() || projectLoading}
                >
                  <svg viewBox="0 0 24 24" fill="none"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                </button>
              </div>
            </div>
          ) : (
            // Preview Frame
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
                    <span>{project?.preview_url || 'localhost:3000'}</span>
                  </div>
                </div>
                <div className="vibe-device-content">
                  {project?.preview_url ? (
                    <iframe 
                      src={project.preview_url}
                      title="Preview"
                      className="vibe-preview-iframe"
                    />
                  ) : (
                    <div className="vibe-preview-placeholder">
                      <div className="vibe-preview-placeholder-icon">
                        <svg viewBox="0 0 24 24" fill="none"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>
                      </div>
                      <h3>Preview Available After Build</h3>
                      <p>Complete the build pipeline to see the preview</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Code Panel */}
        <div className={`vibe-code-panel ${currentView === 'preview' ? 'hidden' : ''} ${currentView === 'split' ? 'split-view' : ''}`}>
          {/* File Tabs */}
          <div className="vibe-code-tabs">
            {openTabs.map(tab => (
              <button
                key={tab}
                className={`vibe-code-tab ${activeFilePath === tab ? 'active' : ''}`}
                onClick={() => setActiveFilePath(tab)}
              >
                <span className="vibe-code-tab-name">{tab.split('/').pop()}</span>
                <button 
                  className="vibe-code-tab-close"
                  onClick={(e) => {
                    e.stopPropagation();
                    setOpenTabs(openTabs.filter(t => t !== tab));
                    if (activeFilePath === tab) {
                      setActiveFilePath(openTabs.find(t => t !== tab) || null);
                    }
                  }}
                >
                  <svg viewBox="0 0 24 24" fill="none"><path d="M18 6L6 18M6 6l12 12"/></svg>
                </button>
              </button>
            ))}
          </div>

          {/* Code Editor */}
          <div className="vibe-code-editor">
            {activeFilePath ? (
              <>
                <div className="vibe-code-line-numbers">
                  {getFileContent(activeFilePath).split('\n').map((_, i) => (
                    <div key={i} className="vibe-line-number">{i + 1}</div>
                  ))}
                </div>
                <div className="vibe-code-content">
                  <pre className="vibe-code-pre">
                    <code className={`language-${getFileLanguage(activeFilePath)}`}>
                      {getFileContent(activeFilePath).split('\n').map((line, i) => (
                        <div key={i} className="vibe-code-line">
                          {renderSyntaxHighlightedLine(line, getFileLanguage(activeFilePath))}
                        </div>
                      ))}
                    </code>
                  </pre>
                </div>
              </>
            ) : (
              <div className="vibe-code-empty">
                <p>Select a file to view its contents</p>
              </div>
            )}
          </div>

          {/* Status Bar */}
          <div className="vibe-code-statusbar">
            <div className="vibe-statusbar-left">
              <span className="vibe-statusbar-item">
                <svg viewBox="0 0 24 24" fill="none" className="w-3 h-3"><path d="M12 2L2 7l10 5 10-5-10-5z"/></svg>
                main
              </span>
            </div>
            <div className="vibe-statusbar-right">
              {activeFilePath && (
                <>
                  <span className="vibe-statusbar-item">{getFileLanguage(activeFilePath).toUpperCase()}</span>
                  <span className="vibe-statusbar-item">UTF-8</span>
                  <span className="vibe-statusbar-item">
                    {getFileContent(activeFilePath).split('\n').length} lines
                  </span>
                </>
              )}
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
                      {agent.status === 'idle' ? 'Ready' : agent.status === 'working' ? 'Working' : agent.status === 'complete' ? 'Complete' : 'Error'}
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
            <span className="vibe-activity-badge">{combinedActivities.length}</span>
          </div>
          <button className="vibe-activity-toggle">
            <svg viewBox="0 0 24 24" fill="none"><path d="M6 9l6 6 6-6"/></svg>
          </button>
        </div>
        <div className="vibe-activity-list">
          {combinedActivities.slice(0, 5).map((a, i) => (
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
          {combinedActivities.length === 0 && (
            <div className="vibe-activity-empty">No activity yet</div>
          )}
        </div>
      </div>
    </>
  );

  return (
    <aside className={`vibe-workspace ${isOpen ? 'open' : ''}`}>
      <canvas ref={canvasRef} className="vibe-particle-canvas" />
      
      <div className="vibe-inner">
        {viewMode === 'projects' ? renderProjectsView() : renderWorkspaceView()}
      </div>
    </aside>
  );
}
