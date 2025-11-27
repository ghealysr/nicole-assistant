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
  const [activeFile, setActiveFile] = useState('index.html');
  const [openTabs, setOpenTabs] = useState(['index.html', 'styles.css', 'app.js']);

  // Sample code content for different files
  const fileContents: Record<string, { language: string; code: string }> = {
    'index.html': {
      language: 'html',
      code: `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>My Awesome App</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="container">
    <header class="header">
      <h1>Welcome to My App</h1>
      <nav class="nav">
        <a href="#home">Home</a>
        <a href="#about">About</a>
        <a href="#contact">Contact</a>
      </nav>
    </header>
    
    <main class="main-content">
      <section class="hero">
        <h2>Build Something Amazing</h2>
        <p>Start creating with Nicole's Vibe workspace.</p>
        <button class="btn-primary">Get Started</button>
      </section>
    </main>
    
    <footer class="footer">
      <p>&copy; 2024 My App. All rights reserved.</p>
    </footer>
  </div>
  
  <script src="app.js"></script>
</body>
</html>`
    },
    'styles.css': {
      language: 'css',
      code: `/* Reset & Base Styles */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --primary-color: #B8A8D4;
  --secondary-color: #8B5CF6;
  --bg-color: #0C0C0E;
  --text-color: #FAFAFA;
  --muted-color: #A1A1AA;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg-color);
  color: var(--text-color);
  line-height: 1.6;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.nav a {
  color: var(--muted-color);
  text-decoration: none;
  margin-left: 24px;
  transition: color 0.2s;
}

.nav a:hover {
  color: var(--primary-color);
}

.hero {
  text-align: center;
  padding: 120px 0;
}

.hero h2 {
  font-size: 3rem;
  margin-bottom: 16px;
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.btn-primary {
  background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
  color: white;
  border: none;
  padding: 14px 32px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(139, 92, 246, 0.4);
}`
    },
    'app.js': {
      language: 'javascript',
      code: `// Main Application Entry Point
import { initApp } from './lib/init.js';
import { setupEventListeners } from './lib/events.js';

// Configuration
const config = {
  apiUrl: 'https://api.example.com',
  version: '1.0.0',
  debug: true,
};

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
  console.log('🚀 App initializing...');
  
  try {
    initApp(config);
    setupEventListeners();
    
    // Fetch initial data
    fetchUserData();
    
    console.log('✅ App initialized successfully!');
  } catch (error) {
    console.error('❌ Failed to initialize:', error);
  }
});

// Fetch user data from API
async function fetchUserData() {
  const response = await fetch(\`\${config.apiUrl}/user\`);
  const data = await response.json();
  
  if (data.success) {
    updateUI(data.user);
  }
}

// Update the UI with user data
function updateUI(user) {
  const greeting = document.querySelector('.hero h2');
  if (greeting && user.name) {
    greeting.textContent = \`Welcome back, \${user.name}!\`;
  }
}

// Export for testing
export { config, fetchUserData, updateUI };`
    },
    'package.json': {
      language: 'json',
      code: `{
  "name": "my-awesome-app",
  "version": "1.0.0",
  "description": "A modern web application",
  "main": "app.js",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "lint": "eslint src/",
    "test": "vitest"
  },
  "dependencies": {
    "axios": "^1.6.0",
    "lodash": "^4.17.21"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "eslint": "^8.55.0",
    "vitest": "^1.0.0"
  },
  "author": "Nicole AI",
  "license": "MIT"
}`
    },
    'README.md': {
      language: 'markdown',
      code: `# My Awesome App

A modern web application built with Nicole's Vibe workspace.

## Features

- ⚡ Fast and responsive
- 🎨 Beautiful UI with dark mode
- 🔧 Easy to customize
- 📱 Mobile-friendly

## Getting Started

\`\`\`bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
\`\`\`

## License

MIT © 2024`
    }
  };

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

  // Syntax highlighting helper
  const renderSyntaxHighlightedLine = (line: string, language: string): React.ReactNode => {
    if (!line) return <span>&nbsp;</span>;

    // HTML syntax highlighting
    if (language === 'html') {
      return line.split(/(<[^>]+>|&[a-z]+;)/g).map((part, i) => {
        if (part.startsWith('<!')) {
          return <span key={i} className="code-comment">{part}</span>;
        }
        if (part.startsWith('<') && part.endsWith('>')) {
          // Tag with attributes
          const tagMatch = part.match(/^(<\/?)(\w+)(.*?)(\/?>)$/);
          if (tagMatch) {
            const [, open, tagName, attrs, close] = tagMatch;
            return (
              <span key={i}>
                <span className="code-tag">{open}{tagName}</span>
                {attrs && renderAttributes(attrs)}
                <span className="code-tag">{close}</span>
              </span>
            );
          }
          return <span key={i} className="code-tag">{part}</span>;
        }
        return <span key={i}>{part}</span>;
      });
    }

    // CSS syntax highlighting
    if (language === 'css') {
      // Comments
      if (line.trim().startsWith('/*') || line.trim().startsWith('*')) {
        return <span className="code-comment">{line}</span>;
      }
      // Selectors and properties
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
      if (line.includes('{') || line.includes('}')) {
        return <span className="code-keyword">{line}</span>;
      }
      return <span>{line}</span>;
    }

    // JavaScript syntax highlighting
    if (language === 'javascript') {
      // Comments
      if (line.trim().startsWith('//')) {
        return <span className="code-comment">{line}</span>;
      }
      // Keywords
      const keywords = ['const', 'let', 'var', 'function', 'async', 'await', 'return', 'if', 'else', 'try', 'catch', 'import', 'export', 'from', 'class', 'new', 'throw'];
      
      return (
        <span>
          {line.split(/(\s+|[{}()[\];,.]|'[^']*'|"[^"]*"|`[^`]*`|\b(?:const|let|var|function|async|await|return|if|else|try|catch|import|export|from|class|new|throw|true|false|null|undefined)\b)/g).map((part, i) => {
            if (keywords.includes(part)) {
              return <span key={i} className="code-keyword">{part}</span>;
            }
            if (/^['"`].*['"`]$/.test(part)) {
              return <span key={i} className="code-string">{part}</span>;
            }
            if (/^\d+$/.test(part)) {
              return <span key={i} className="code-number">{part}</span>;
            }
            if (/^[a-zA-Z_]\w*(?=\s*\()/.test(part)) {
              return <span key={i} className="code-function">{part}</span>;
            }
            return <span key={i}>{part}</span>;
          })}
        </span>
      );
    }

    // JSON syntax highlighting
    if (language === 'json') {
      return (
        <span>
          {line.split(/("[^"]*")\s*(:)?/g).map((part, i) => {
            if (part && part.startsWith('"') && part.endsWith('"')) {
              // Check if next part is a colon (key) or not (value)
              return <span key={i} className="code-string">{part}</span>;
            }
            if (part === ':') {
              return <span key={i}>{part}</span>;
            }
            if (/^\d+$/.test(part?.trim())) {
              return <span key={i} className="code-number">{part}</span>;
            }
            if (part === 'true' || part === 'false' || part === 'null') {
              return <span key={i} className="code-keyword">{part}</span>;
            }
            return <span key={i}>{part}</span>;
          })}
        </span>
      );
    }

    // Markdown - basic highlighting
    if (language === 'markdown') {
      if (line.startsWith('#')) {
        return <span className="code-keyword">{line}</span>;
      }
      if (line.startsWith('```')) {
        return <span className="code-comment">{line}</span>;
      }
      if (line.startsWith('-') || line.startsWith('*')) {
        return <span><span className="code-keyword">{line[0]}</span>{line.slice(1)}</span>;
      }
      return <span>{line}</span>;
    }

    return <span>{line}</span>;
  };

  // Helper for HTML attributes
  const renderAttributes = (attrs: string): React.ReactNode => {
    return attrs.split(/(\w+="[^"]*"|\w+='[^']*')/g).map((part, i) => {
      const attrMatch = part.match(/^(\w+)(=)("[^"]*"|'[^']*')$/);
      if (attrMatch) {
        const [, name, eq, value] = attrMatch;
        return (
          <span key={i}>
            <span className="code-attr"> {name}</span>
            <span>{eq}</span>
            <span className="code-string">{value}</span>
          </span>
        );
      }
      return <span key={i}>{part}</span>;
    });
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
          <div className={`vibe-preview-panel ${currentView === 'code' ? 'hidden' : ''} ${currentView === 'split' ? 'split-view' : ''}`}>
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

          {/* Code Panel - Traditional IDE Look */}
          <div className={`vibe-code-panel ${currentView === 'preview' ? 'hidden' : ''} ${currentView === 'split' ? 'split-view' : ''}`}>
            {/* File Tabs */}
            <div className="vibe-code-tabs">
              {openTabs.map(tab => {
                const isModified = files.flatMap(f => f.children || [f]).find(f => f.name === tab)?.status === 'modified';
                return (
                  <button
                    key={tab}
                    className={`vibe-code-tab ${activeFile === tab ? 'active' : ''}`}
                    onClick={() => setActiveFile(tab)}
                  >
                    <span className={`vibe-code-tab-icon ${tab.split('.').pop()}`}>
                      {tab.endsWith('.html') && <svg viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>}
                      {tab.endsWith('.css') && <svg viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>}
                      {tab.endsWith('.js') && <svg viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>}
                      {tab.endsWith('.json') && <svg viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>}
                      {tab.endsWith('.md') && <svg viewBox="0 0 24 24" fill="none"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>}
                    </span>
                    <span className="vibe-code-tab-name">{tab}</span>
                    {isModified && <span className="vibe-code-tab-modified" />}
                    <button 
                      className="vibe-code-tab-close"
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenTabs(openTabs.filter(t => t !== tab));
                        if (activeFile === tab && openTabs.length > 1) {
                          setActiveFile(openTabs.find(t => t !== tab) || '');
                        }
                      }}
                    >
                      <svg viewBox="0 0 24 24" fill="none"><path d="M18 6L6 18M6 6l12 12"/></svg>
                    </button>
                  </button>
                );
              })}
            </div>

            {/* Code Editor */}
            <div className="vibe-code-editor">
              {/* Line Numbers */}
              <div className="vibe-code-line-numbers">
                {fileContents[activeFile]?.code.split('\n').map((_, i) => (
                  <div key={i} className="vibe-line-number">{i + 1}</div>
                ))}
              </div>

              {/* Code Content with Syntax Highlighting */}
              <div className="vibe-code-content">
                <pre className="vibe-code-pre">
                  <code className={`language-${fileContents[activeFile]?.language || 'text'}`}>
                    {fileContents[activeFile]?.code.split('\n').map((line, i) => (
                      <div key={i} className={`vibe-code-line ${i === 10 ? 'highlight' : ''}`}>
                        {renderSyntaxHighlightedLine(line, fileContents[activeFile]?.language || 'text')}
                      </div>
                    ))}
                  </code>
                </pre>
              </div>
            </div>

            {/* Status Bar */}
            <div className="vibe-code-statusbar">
              <div className="vibe-statusbar-left">
                <span className="vibe-statusbar-item">
                  <svg viewBox="0 0 24 24" fill="none" className="w-3 h-3"><path d="M12 2L2 7l10 5 10-5-10-5z"/></svg>
                  main
                </span>
                <span className="vibe-statusbar-item">
                  <svg viewBox="0 0 24 24" fill="none" className="w-3 h-3"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
                  Synced
                </span>
              </div>
              <div className="vibe-statusbar-right">
                <span className="vibe-statusbar-item">{fileContents[activeFile]?.language.toUpperCase()}</span>
                <span className="vibe-statusbar-item">UTF-8</span>
                <span className="vibe-statusbar-item">LF</span>
                <span className="vibe-statusbar-item">
                  Ln {fileContents[activeFile]?.code.split('\n').length}, Col 1
                </span>
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

