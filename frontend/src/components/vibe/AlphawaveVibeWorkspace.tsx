'use client';

import React, { useState, useRef, useEffect, useCallback, useMemo, Component, ErrorInfo, ReactNode } from 'react';
import { useVibeProjects, useVibeProject, type VibeProject, type ProjectType } from '@/lib/hooks/useVibeProject';
import { openInStackBlitz } from '@/lib/stackblitz';
import { API_URL } from '@/lib/alphawave_config';
import { getStoredToken } from '@/lib/google_auth';

// ============================================================================
// IMAGE LIGHTBOX - For viewing screenshots full-size
// ============================================================================

interface LightboxState {
  isOpen: boolean;
  imageUrl: string;
  description: string;
}

function ImageLightbox({ 
  isOpen, 
  imageUrl, 
  description, 
  onClose 
}: LightboxState & { onClose: () => void }) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleEsc);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEsc);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="vibe-lightbox-overlay" onClick={onClose}>
      <div className="vibe-lightbox-content" onClick={e => e.stopPropagation()}>
        <button className="vibe-lightbox-close" onClick={onClose}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
        <img src={imageUrl} alt={description || 'Screenshot'} className="vibe-lightbox-image" />
        {description && <p className="vibe-lightbox-caption">{description}</p>}
      </div>
    </div>
  );
}

// ============================================================================
// SCREENSHOT THUMBNAIL - Clickable thumbnail that opens lightbox
// ============================================================================

function ScreenshotThumbnail({ 
  url, 
  description,
  onOpen 
}: { 
  url: string; 
  description?: string;
  onOpen: (url: string, desc: string) => void;
}) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);

  if (error) {
    return (
      <div className="vibe-screenshot-error">
        <span>📷</span>
        <span>Screenshot unavailable</span>
      </div>
    );
  }

  return (
    <div 
      className={`vibe-screenshot-thumb ${loaded ? 'loaded' : 'loading'}`}
      onClick={() => onOpen(url, description || '')}
      title={description || 'Click to view full size'}
    >
      {!loaded && <div className="vibe-screenshot-loader">📷</div>}
      <img 
        src={url} 
        alt={description || 'Screenshot'} 
        onLoad={() => setLoaded(true)}
        onError={() => setError(true)}
      />
      <div className="vibe-screenshot-overlay">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
        </svg>
      </div>
    </div>
  );
}

// ============================================================================
// EXTRACT IMAGES - Find image URLs in text
// ============================================================================

function extractImagesFromText(text: string): string[] {
  // Match Cloudinary URLs and other image URLs
  const cloudinaryPattern = /https:\/\/res\.cloudinary\.com\/[^\s\)\"\']+/gi;
  const genericImagePattern = /https?:\/\/[^\s\)\"\']+\.(?:png|jpg|jpeg|gif|webp)(?:\?[^\s\)\"\']*)?/gi;
  
  const cloudinaryMatches = text.match(cloudinaryPattern) || [];
  const imageMatches = text.match(genericImagePattern) || [];
  
  // Dedupe and return using Array.from for TypeScript compatibility
  const allMatches = [...cloudinaryMatches, ...imageMatches];
  return Array.from(new Set(allMatches));
}

// ============================================================================
// SIMPLE MARKDOWN RENDERER - For Nicole's formatted responses
// ============================================================================

function formatMarkdown(text: string, onImageClick?: (url: string, desc: string) => void): React.ReactNode {
  if (!text) return null;
  
  // Extract any images from the text
  const images = extractImagesFromText(text);
  
  // Remove image URLs from the text for cleaner display
  let cleanedText = text;
  images.forEach(url => {
    cleanedText = cleanedText.replace(url, '').trim();
  });
  // Clean up any leftover markdown image syntax like ![...]()
  cleanedText = cleanedText.replace(/!\[[^\]]*\]\(\s*\)/g, '').trim();
  
  // Split into paragraphs
  const paragraphs = cleanedText.split(/\n\n+/).filter(p => p.trim());
  
  const textContent = paragraphs.map((para, pIdx) => {
    // Check if this is a list
    const lines = para.split('\n');
    const isNumberedList = lines.every(l => /^\d+\.\s/.test(l.trim()) || l.trim() === '');
    const isBulletList = lines.every(l => /^[-*•]\s/.test(l.trim()) || l.trim() === '');
    
    if (isNumberedList && lines.some(l => /^\d+\./.test(l.trim()))) {
      return (
        <ol key={pIdx} className="vibe-md-list">
          {lines.filter(l => l.trim()).map((line, lIdx) => (
            <li key={lIdx}>{formatInline(line.replace(/^\d+\.\s*/, ''))}</li>
          ))}
        </ol>
      );
    }
    
    if (isBulletList && lines.some(l => /^[-*•]/.test(l.trim()))) {
      return (
        <ul key={pIdx} className="vibe-md-list">
          {lines.filter(l => l.trim()).map((line, lIdx) => (
            <li key={lIdx}>{formatInline(line.replace(/^[-*•]\s*/, ''))}</li>
          ))}
        </ul>
      );
    }
    
    // Regular paragraph - handle single line breaks as <br>
    const formattedLines = lines.map((line, lIdx) => (
      <React.Fragment key={lIdx}>
        {lIdx > 0 && <br />}
        {formatInline(line)}
      </React.Fragment>
    ));
    
    return <p key={pIdx} className="vibe-md-para">{formattedLines}</p>;
  });

  // If there are images, render them in a gallery
  if (images.length > 0 && onImageClick) {
    return (
      <>
        {textContent}
        <div className="vibe-message-images">
          {images.map((url, idx) => (
            <ScreenshotThumbnail 
              key={idx} 
              url={url} 
              description={`Screenshot ${idx + 1}`}
              onOpen={onImageClick}
            />
          ))}
        </div>
      </>
    );
  }

  return textContent;
}

function formatInline(text: string): React.ReactNode {
  // Handle **bold** and *italic* and `code`
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;
  
  while (remaining.length > 0) {
    // Bold: **text**
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    // Italic: *text*
    const italicMatch = remaining.match(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/);
    // Code: `text`
    const codeMatch = remaining.match(/`(.+?)`/);
    
    // Find the first match
    const matches = [
      boldMatch && { type: 'bold', match: boldMatch, index: boldMatch.index! },
      italicMatch && { type: 'italic', match: italicMatch, index: italicMatch.index! },
      codeMatch && { type: 'code', match: codeMatch, index: codeMatch.index! },
    ].filter(Boolean).sort((a, b) => a!.index - b!.index);
    
    if (matches.length === 0) {
      parts.push(remaining);
      break;
    }
    
    const first = matches[0]!;
    
    // Add text before match
    if (first.index > 0) {
      parts.push(remaining.slice(0, first.index));
    }
    
    // Add formatted element
    if (first.type === 'bold') {
      parts.push(<strong key={key++}>{first.match![1]}</strong>);
    } else if (first.type === 'italic') {
      parts.push(<em key={key++}>{first.match![1]}</em>);
    } else if (first.type === 'code') {
      parts.push(<code key={key++} className="vibe-md-code">{first.match![1]}</code>);
    }
    
    remaining = remaining.slice(first.index + first.match![0].length);
  }
  
  return parts.length === 1 ? parts[0] : <>{parts}</>;
}

// ============================================================================
// ERROR BOUNDARY - Catches React render errors
// ============================================================================
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class VibeErrorBoundary extends Component<{ children: ReactNode; onReset?: () => void }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode; onReset?: () => void }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[VibeErrorBoundary] Caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="vibe-error-boundary">
          <div className="vibe-error-content">
            <h3>⚠️ Something went wrong</h3>
            <p>The Vibe Dashboard encountered an error.</p>
            <button
              className="vibe-btn-primary"
              onClick={() => {
                this.setState({ hasError: false, error: null });
                this.props.onReset?.();
              }}
            >
              Try Again
            </button>
            <details style={{ marginTop: 12, fontSize: 12, color: '#999' }}>
              <summary>Error Details</summary>
              <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {this.state.error?.message}
              </pre>
            </details>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// ============================================================================
// TYPES
// ============================================================================
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
  onExpandChange?: (expanded: boolean) => void;
}

type ViewMode = 'projects' | 'workspace';

/**
 * AlphaWave Vibe Dashboard
 * Full-featured coding workspace with project management, agents, and build pipeline
 */
export function AlphawaveVibeWorkspace({ isOpen, onClose, onExpandChange }: AlphawaveVibeWorkspaceProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('projects');
  const [isExpanded, setIsExpanded] = useState(true);  // Full width when open
  
  // Sync expanded state with parent - notify when opening, reset when closing
  useEffect(() => {
    if (isOpen) {
      // Panel is opening - tell parent we're expanded
      onExpandChange?.(isExpanded);
    } else {
      // Panel is closing - tell parent we're not expanded anymore
      onExpandChange?.(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]); // Only react to isOpen changes
  
  // Handle expand toggle
  const handleExpandToggle = useCallback(() => {
    const newExpanded = !isExpanded;
    setIsExpanded(newExpanded);
    onExpandChange?.(newExpanded);
  }, [isExpanded, onExpandChange]);
  const [currentDevice, setCurrentDevice] = useState<'mobile' | 'tablet' | 'desktop'>('desktop');
  const [currentView, setCurrentView] = useState<'preview' | 'code' | 'split'>('split');
  const [activityCollapsed, setActivityCollapsed] = useState(false);
  const [activeFilePath, setActiveFilePath] = useState<string | null>(null);
  const [openTabs, setOpenTabs] = useState<string[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [modelHealth, setModelHealth] = useState<Record<string, unknown>[] | null>(null);
  const [modelHealthError, setModelHealthError] = useState<string | null>(null);
  
  // Lightbox state for screenshot viewing
  const [lightbox, setLightbox] = useState<LightboxState>({ isOpen: false, imageUrl: '', description: '' });
  
  const openLightbox = useCallback((url: string, description: string) => {
    setLightbox({ isOpen: true, imageUrl: url, description });
  }, []);
  
  const closeLightbox = useCallback(() => {
    setLightbox({ isOpen: false, imageUrl: '', description: '' });
  }, []);
  
  // Project creation form
  const [showNewProjectForm, setShowNewProjectForm] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectType, setNewProjectType] = useState<ProjectType>('website');
  const [newClientName, setNewClientName] = useState('');
  const [newClientEmail, setNewClientEmail] = useState('');
  
  // Intake chat
  const [intakeMessage, setIntakeMessage] = useState('');
  
  // Preview HTML state (fetched from backend)
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  
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
    filesLoading,
    filesError,
    activitiesError,
    error: projectError,
    operationStates,
    isAnyOperationLoading,
    canRunPipeline,
    canApprove,
    canDeploy,
    totalApiCost,
    apiBudget,
    remainingApiBudget,
    pipelineError,
    rawBuildPreview,
    // These are available for manual phase execution (not currently used in pipeline)
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    runPlanning,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    runBuild,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    runQA,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    runReview,
    fetchProject,
    fetchFiles,
    fetchActivities,
    runIntake,
    approveProject,
    deployProject,
    runPipeline,
    retryPhase,
    clearPipelineError,
    clearIntakeHistory,
  } = useVibeProject(selectedProjectId || undefined);

  // Fetch projects on mount
  useEffect(() => {
    if (isOpen) {
      fetchProjects();
    }
  }, [isOpen, fetchProjects]);

  // Fetch model health (for single-user insight)
  useEffect(() => {
    if (!isOpen) return;
    const token = getStoredToken();
    if (!token) return;
    const controller = new AbortController();
    fetch(`${API_URL}/vibe/models/health`, {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      signal: controller.signal,
    })
      .then(res => res.json())
      .then(data => {
        if (data?.success && data?.data?.models) {
          setModelHealth(data.data.models);
          setModelHealthError(null);
        } else {
          setModelHealthError(data?.error || 'Unable to load model health');
        }
      })
      .catch(err => {
        if (err.name === 'AbortError') return;
        setModelHealthError('Unable to load model health');
      });
    return () => controller.abort();
  }, [isOpen]);

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
    const apiFormatted = (activities || []).map(a => {
      // Prefer rich content from metadata.full_content or metadata.message
      const meta = (a.metadata || {}) as { full_content?: string; message?: string; message_type?: string };
      const content = meta.full_content || meta.message || a.description;
      const messageType = meta.message_type || (a.activity_type || '').toLowerCase();
      return {
        agent: a.agent_name || 'System',
        action: content,
        time: formatActivityTime(a.created_at),
        messageType,
        meta,
      };
    });
    
    // Local activities first (most recent), then API activities
    return [...localActivities, ...apiFormatted].slice(0, 30);
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
    if (!intakeMessage.trim() || !selectedProjectId) {
      console.log('[handleSendIntake] Blocked - empty message or no project', { intakeMessage, selectedProjectId });
      return;
    }
    
    const message = intakeMessage;
    setIntakeMessage('');
    addActivity('Intake', `Processing: "${message.slice(0, 40)}..."`);
    
    console.log('[handleSendIntake] Sending intake:', { projectId: selectedProjectId, message });
    
    try {
      const result = await runIntake(selectedProjectId, message);
      console.log('[handleSendIntake] Result:', result);
      
      if (result?.brief) {
        addActivity('Intake', 'Brief extracted - ready for planning');
      }
    } catch (err) {
      console.error('[handleSendIntake] Error:', err);
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

  // Fetch preview HTML when files are available
  useEffect(() => {
    if (!project?.project_id || files.length === 0) return;
    
    const fetchPreview = async () => {
      setPreviewLoading(true);
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'https://api.nicole.alphawavetech.com'}/vibe/projects/${project.project_id}/preview`,
          {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`,
              'Content-Type': 'application/json',
            },
          }
        );
        if (response.ok) {
          const data = await response.json();
          if (data.success && data.data?.html) {
            setPreviewHtml(data.data.html);
          }
        }
      } catch (err) {
        console.error('[Preview] Failed to fetch preview:', err);
      } finally {
        setPreviewLoading(false);
      }
    };
    
    fetchPreview();
  }, [project?.project_id, files.length]);

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

  // Convert file tree from API to UI format (recursive helper)
  const convertFileTree = useCallback((items: typeof fileTree): FileItem[] => {
    if (!items || !Array.isArray(items)) return [];

    return items.map(item => ({
      name: item.name || 'Unknown',
      type: (item.type === 'folder' ? 'folder' : item.type || 'text') as FileItem['type'],
      path: item.path,
      children: item.children ? convertFileTree(item.children) : undefined,
    }));
  }, []);

  const convertedFileTree = useMemo(() =>
    convertFileTree(fileTree),
    [fileTree, convertFileTree]
  );

  // Particle system with mounted flag for safety
  useEffect(() => {
    if (!isOpen || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Mounted flag to prevent animation continuing after unmount
    let mounted = true;

    const particles: Array<{
      x: number;
      y: number;
      size: number;
      speedX: number;
      speedY: number;
      opacity: number;
    }> = [];

    const resize = () => {
      if (!mounted) return;
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
      // Check mounted flag before continuing animation
      if (!mounted) return;
      
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
      mounted = false;  // Signal animation to stop
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
  
  const renderProjectsView = () => {
    try {
      return (
        <div className="vibe-projects-view">
      {(projectsError || projectError) && (
        <div className="vibe-error" style={{ marginBottom: 16 }}>
          {typeof (projectsError || projectError) === 'string' 
            ? (projectsError || projectError)
            : 'An error occurred'}
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
        
        {/* Error already displayed at top of view - no duplicate here */}
        
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
    } catch (error) {
      console.error('Error rendering projects view:', error);
      return (
        <div className="vibe-projects-view">
          <div className="vibe-error">
            Failed to load projects view. Please refresh the page.
          </div>
        </div>
      );
    }
  };

  // ============================================================================
  // WORKSPACE VIEW
  // ============================================================================
  
  const renderWorkspaceView = () => {
    try {
      return (
        <>
      {(projectsError || projectError) && (
        <div className="vibe-error" style={{ marginBottom: 12, marginLeft: 16, marginRight: 16 }}>
          {typeof (projectsError || projectError) === 'string' 
            ? (projectsError || projectError)
            : 'An error occurred'}
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
          <div className="vibe-projects-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <polygon points="12 2 2 7 12 12 22 7 12 2"/>
              <polyline points="2 17 12 22 22 17"/>
              <polyline points="2 12 12 17 22 12"/>
            </svg>
            <span>AlphaWave Vibe</span>
          </div>
          {/* Stage indicator - inline with header */}
          <div className="vibe-header-status">
            <span className={`vibe-status-dot ${projectLoading ? 'working' : ''}`} />
            <span className="vibe-status-label">{project?.status || 'Loading'}</span>
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
          {/* API Cost & Budget Display */}
          <span className="vibe-api-cost" title="Estimated API cost for this session">
            Cost: ${totalApiCost.toFixed(4)}
          </span>
          <span className={`vibe-api-budget ${remainingApiBudget <= 0 ? 'over' : ''}`} title="Budget remaining">
            Budget left: ${remainingApiBudget.toFixed(2)} / ${apiBudget.toFixed(2)}
          </span>
          
          {/* StackBlitz Button - Open in full IDE */}
          {files.length > 0 && (
            <button 
              className="vibe-stackblitz-btn"
              onClick={async () => {
                if (project && files.length > 0) {
                  try {
                    // Fetch design tokens from backend
                    const response = await fetch(
                      `${process.env.NEXT_PUBLIC_API_URL || 'https://api.nicole.alphawavetech.com'}/vibe/projects/${project.project_id}/stackblitz`,
                      {
                        headers: {
                          'Authorization': `Bearer ${localStorage.getItem('token')}`,
                          'Content-Type': 'application/json',
                        },
                      }
                    );
                    
                    let design: {
                      primaryColor?: string;
                      secondaryColor?: string;
                      accentColor?: string;
                      headingFont?: string;
                      bodyFont?: string;
                    } = {
                      primaryColor: '#8B9D83',
                      secondaryColor: '#F4E4BC',
                      accentColor: '#D4A574',
                    };
                    
                    if (response.ok) {
                      const data = await response.json();
                      if (data.success && data.data?.design) {
                        design = {
                          primaryColor: data.data.design.primary_color,
                          secondaryColor: data.data.design.secondary_color,
                          accentColor: data.data.design.accent_color,
                          headingFont: data.data.design.heading_font,
                          bodyFont: data.data.design.body_font,
                        };
                      }
                    }
                    
                    await openInStackBlitz(
                      project.name || 'AlphaWave Project',
                      files,
                      design
                    );
                  } catch (err) {
                    console.error('[StackBlitz] Failed to open:', err);
                    // Fallback with default design
                    await openInStackBlitz(
                      project.name || 'AlphaWave Project',
                      files
                    );
                  }
                }
              }}
              title="Open in StackBlitz IDE"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
              </svg>
              <span>StackBlitz</span>
            </button>
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
          
          {/* Retry Button - for stuck projects */}
          {project?.status && ['planning', 'building', 'qa', 'review'].includes(project.status) && !isAnyOperationLoading && (
            <button 
              className="vibe-retry-btn"
              onClick={async () => {
                if (selectedProjectId) {
                  const success = await retryPhase(selectedProjectId);
                  if (success) {
                    // Trigger the pipeline again after retry
                    handleRunPipeline();
                  }
                }
              }}
              title="Retry current phase if stuck"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M1 4v6h6M23 20v-6h-6"/>
                <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
              </svg>
              <span>Retry</span>
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

      {/* Pipeline Error Banner */}
      {pipelineError && (
        <div className="vibe-error-banner">
          <div className="vibe-error-banner-left">
            <span className="vibe-error-icon">⚠️</span>
            <div>
              <div className="vibe-error-title">Pipeline issue in {pipelineError.phase}</div>
              <div className="vibe-error-message">{pipelineError.message}</div>
            </div>
          </div>
          <div className="vibe-error-banner-actions">
            {rawBuildPreview && pipelineError.phase === 'build' && (
              <details className="vibe-error-preview">
                <summary>Raw build preview</summary>
                <pre>{rawBuildPreview}</pre>
              </details>
            )}
            <button className="vibe-btn-secondary" onClick={() => selectedProjectId && retryPhase(selectedProjectId)}>
              Retry Phase
            </button>
            <button className="vibe-btn-secondary" onClick={clearPipelineError}>
              Dismiss
            </button>
          </div>
        </div>
      )}

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
            {filesLoading ? (
              <div className="vibe-files-loading">
                <div className="vibe-spinner-small" />
                <span>Loading files...</span>
              </div>
            ) : filesError ? (
              <div className="vibe-files-error">
                <span className="vibe-error-icon">⚠️</span>
                <span>{typeof filesError === 'string' ? filesError : 'Failed to load files'}</span>
                <button
                  className="vibe-btn-secondary vibe-btn-small"
                  onClick={() => selectedProjectId && fetchFiles(selectedProjectId)}
                >
                  Retry
                </button>
              </div>
            ) : Array.isArray(convertedFileTree) && convertedFileTree.length > 0 ? (
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
                    <div className="vibe-message-content">
                      {msg.role === 'assistant' ? formatMarkdown(msg.content, openLightbox) : msg.content}
                    </div>
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
              {/* Planning Artifacts */}
              {project?.architecture && (
                <div className="vibe-architecture-card">
                  <div className="vibe-architecture-header">
                    <div>
                      <h4>Architecture Plan</h4>
                      <p>{(() => {
                        const arch = project.architecture as Record<string, unknown> | undefined;
                        const pages = arch?.pages;
                        return Array.isArray(pages) ? `${pages.length} pages` : 'Structured spec';
                      })()}</p>
                    </div>
                    {(() => {
                      const arch = project.architecture as Record<string, unknown> | undefined;
                      const designSystem = arch?.design_system as Record<string, unknown> | undefined;
                      const colors = designSystem?.colors as Record<string, string> | undefined;
                      const typography = designSystem?.typography as Record<string, string> | undefined;
                      
                      if (!designSystem) return null;
                      
                      return (
                        <div className="vibe-design-tokens">
                          <span className="vibe-token-title">Design Tokens</span>
                          <div className="vibe-token-row">
                            <span className="vibe-token-swatch" style={{ background: colors?.primary || '#8B5CF6' }} />
                            <span>{colors?.primary || 'Primary'}</span>
                          </div>
                          {typography?.heading_font && (
                            <div className="vibe-token-row">
                              <span className="vibe-token-label">Heading</span>
                              <span>{typography.heading_font}</span>
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                  <pre className="vibe-architecture-json">
                    {JSON.stringify(project.architecture, null, 2).slice(0, 2000)}
                  </pre>
                </div>
              )}

              <div className={`vibe-device-frame ${currentDevice}`}>
                <div className="vibe-device-header">
                  <div className="vibe-device-dots">
                    <span className="vibe-device-dot red" />
                    <span className="vibe-device-dot yellow" />
                    <span className="vibe-device-dot green" />
                  </div>
                  <div className="vibe-device-url">
                    <svg viewBox="0 0 24 24" fill="none"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                    <span>{previewHtml ? `preview.alphawave.ai/${project?.name?.toLowerCase().replace(/\s+/g, '-') || 'project'}` : 'localhost:3000'}</span>
                  </div>
                </div>
                <div className="vibe-device-content">
                  {previewLoading ? (
                    <div className="vibe-preview-placeholder">
                      <div className="vibe-preview-placeholder-icon animate-pulse">
                        <svg viewBox="0 0 24 24" fill="none"><path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/></svg>
                      </div>
                      <h3>Generating Preview...</h3>
                    </div>
                  ) : previewHtml ? (
                    <iframe 
                      srcDoc={previewHtml}
                      title="Preview"
                      className="vibe-preview-iframe"
                      sandbox="allow-scripts allow-same-origin"
                    />
                  ) : files.length > 0 ? (
                    <div className="vibe-preview-placeholder">
                      <div className="vibe-preview-placeholder-icon">
                        <svg viewBox="0 0 24 24" fill="none"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
                      </div>
                      <h3>Loading Preview...</h3>
                      <p>Rendering your generated code</p>
                    </div>
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

          {/* LIVE STATUS - Always visible when working */}
          {isAnyOperationLoading && combinedActivities.length > 0 && (
            <div className="vibe-live-status">
              <div className="vibe-live-status-header">
                <span className="vibe-live-pulse" />
                <span className="vibe-live-label">LIVE</span>
              </div>
              <div className="vibe-live-status-content">
                <div className="vibe-live-agent">{combinedActivities[0]?.agent || 'Working'}</div>
                <div className="vibe-live-action">{combinedActivities[0]?.action || 'Processing...'}</div>
                <div className="vibe-live-time">{combinedActivities[0]?.time || 'Now'}</div>
              </div>
              {combinedActivities.length > 1 && combinedActivities[1] && (
                <div className="vibe-live-previous">
                  <span className="vibe-live-previous-label">Previous:</span>
                  <span className="vibe-live-previous-text">{combinedActivities[1].action}</span>
                </div>
              )}
            </div>
          )}

          <div className="vibe-agents-list">
            {Array.isArray(agents) && agents.map(agent => {
              // Find the latest activity for this agent
              const agentActivity = combinedActivities.find(a => 
                a.agent?.toLowerCase().includes(agent.name?.toLowerCase().split(' ')[0] || '')
              );
              const displayTask = agent.status === 'working' && agentActivity 
                ? agentActivity.action 
                : agent.task;
              
              return (
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
                      <span className="vibe-agent-task-text">{displayTask}</span>
                      <span>{agent.progress}%</span>
                    </div>
                  </div>
                </div>
              );
          })}
        </div>

        {/* Model Health */}
        <div className="vibe-model-health">
          <div className="vibe-model-health-header">
            <span>Model Health</span>
            {modelHealthError && <span className="vibe-model-health-error">{modelHealthError}</span>}
          </div>
          {modelHealth ? (
            modelHealth.map((m, idx) => (
              <div key={idx} className="vibe-model-health-row">
                <span className="vibe-model-name">{m.model}</span>
                <span className={`vibe-model-status ${m.status === 'healthy' ? 'ok' : 'warn'}`}>
                  {m.status || 'unknown'}
                </span>
                {m.cooldown_until && (
                  <span className="vibe-model-cooldown">cooldown until {m.cooldown_until}</span>
                )}
              </div>
            ))
          ) : (
            <div className="vibe-model-health-row">Loading...</div>
          )}
        </div>

        {/* Workflow */}
          <div className="vibe-workflow-section">
            <div className="vibe-workflow-title">Pipeline</div>
            <div className="vibe-workflow-visual">
              {Array.isArray(workflow) && workflow.map(step => (
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

      {/* Agent Chat - Conversation between agents */}
      <div className={`vibe-agent-chat ${activityCollapsed ? 'collapsed' : ''}`}>
        <div className="vibe-chat-header" onClick={() => setActivityCollapsed(!activityCollapsed)}>
          <div className="vibe-chat-title">
            <span className="vibe-chat-icon">💬</span>
            Agent Chat
            {isAnyOperationLoading && <span className="vibe-chat-live">● LIVE</span>}
          </div>
          <button className="vibe-chat-toggle">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d={activityCollapsed ? "M5 15l7-7 7 7" : "M19 9l-7 7-7-7"}/>
            </svg>
          </button>
        </div>
        <div className="vibe-chat-messages">
          {activitiesError ? (
            <div className="vibe-chat-error">
              Failed to load chat. <button onClick={() => selectedProjectId && fetchActivities(selectedProjectId)}>Retry</button>
            </div>
          ) : combinedActivities.length === 0 ? (
            <div className="vibe-chat-empty">
              <div className="vibe-chat-waiting">
                <span className="vibe-chat-dot"></span>
                <span className="vibe-chat-dot"></span>
                <span className="vibe-chat-dot"></span>
              </div>
              <span>Agents are standing by...</span>
            </div>
          ) : (
            combinedActivities.slice(0, 30).map((a, i) => {
              // Get agent avatar color
              const agentColors: Record<string, string> = {
                'Nicole': '#8B5CF6',
                'Design Agent': '#EC4899',
                'Architect Agent': '#3B82F6',
                'Coding Agent': '#10B981',
                'QA Agent': '#F59E0B',
                'Review Agent': '#6366F1',
                'System': '#6B7280',
                'Pipeline': '#6B7280',
                'Orchestrator': '#8B5CF6'
              };
              const color = agentColors[a.agent] || '#8B5CF6';
              
              const meta = (a as { meta?: Record<string, unknown> }).meta || {};
              const tool = meta.tool as string | undefined;

              // Clean up action text - remove bracket markers
              let message = a.action || '';
              message = message.replace(/\[PROMPT\]|\[RESPONSE\]|\[THINKING\]|\[TOOL_CALL\]|\[TOOL_RESULT\]|\[ERROR\]/gi, '').trim();
              
              // Determine message type
              const messageType = a.messageType || '';
              const isThinking = messageType.includes('thinking') || a.action?.includes('💭');
              const isError = messageType.includes('error') || a.action?.includes('❌');
              
              return (
                <div key={i} className={`vibe-chat-bubble ${isThinking ? 'thinking' : ''} ${isError ? 'error' : ''}`}>
                  <div className="vibe-chat-avatar" style={{ background: color }}>
                    {a.agent?.charAt(0) || '?'}
                  </div>
                  <div className="vibe-chat-content">
                    <div className="vibe-chat-name" style={{ color }}>
                      {a.agent}
                      <span className="vibe-chat-time">{a.time}</span>
                      {tool && <span className="vibe-chat-tag">{tool}</span>}
                    </div>
                    <div className="vibe-chat-text">{message}</div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </>
      );
    } catch (error) {
      console.error('Error rendering workspace view:', error);
      return (
        <>
          <div className="vibe-error" style={{ padding: 16 }}>
            Failed to load workspace view. Please refresh the page.
          </div>
        </>
      );
    }
  };

  // Show loading state while fetching initial data
  if (projectsLoading && (!projects || projects.length === 0)) {
    return (
      <aside className={`vibe-workspace ${isOpen ? 'open' : ''} ${isExpanded ? 'expanded' : ''}`}>
        <div className="vibe-loading-screen">
          <div className="vibe-loading-spinner" />
          <p>Loading Vibe Dashboard...</p>
        </div>
      </aside>
    );
  }

  return (
    <VibeErrorBoundary onReset={() => fetchProjects()}>
      <aside className={`vibe-workspace ${isOpen ? 'open' : ''} ${isExpanded ? 'expanded' : ''}`}>
        <canvas ref={canvasRef} className="vibe-particle-canvas" />
        
        {/* Expand/Collapse toggle */}
        <button 
          className="vibe-expand-toggle"
          onClick={handleExpandToggle}
          title={isExpanded ? 'Show main chat' : 'Hide main chat'}
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            {isExpanded ? (
              <path d="M9 18l6-6-6-6" /> 
            ) : (
              <path d="M15 18l-6-6 6-6" />
            )}
          </svg>
        </button>

        <div className="vibe-inner">
          {viewMode === 'projects' ? renderProjectsView() : renderWorkspaceView()}
        </div>
      </aside>
      
      {/* Screenshot Lightbox */}
      <ImageLightbox 
        isOpen={lightbox.isOpen}
        imageUrl={lightbox.imageUrl}
        description={lightbox.description}
        onClose={closeLightbox}
      />
    </VibeErrorBoundary>
  );
}
