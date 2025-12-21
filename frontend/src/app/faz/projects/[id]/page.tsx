'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { WorkspaceLayout } from '@/components/faz/WorkspaceLayout';
import { FileTree } from '@/components/faz/FileTree';
import { CodeViewer } from '@/components/faz/CodeViewer';
import { AgentActivityFeed } from '@/components/faz/AgentActivityFeed';
import { ChatMessages } from '@/components/faz/ChatMessages';
import { ChatInput } from '@/components/faz/ChatInput';
import { fazApi } from '@/lib/faz/api';
import { fazWS } from '@/lib/faz/websocket';
import { useFazStore } from '@/lib/faz/store';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { 
  Loader2, Play, Square, Rocket, ExternalLink, RefreshCw, 
  AlertCircle, X, Smartphone, Tablet, Monitor, Code, Eye, Columns
} from 'lucide-react';
import { ProjectSetupStatus } from '@/components/faz/ProjectSetupStatus';
import { ApprovalPanel } from '@/components/faz/ApprovalPanel';
import { cn } from '@/lib/utils';

export default function ProjectWorkspacePage() {
  const params = useParams();
  const projectId = parseInt(params.id as string);
  
  const { 
    currentProject, setCurrentProject,
    files, setFiles, selectedFile,
    activeTab, setActiveTab,
    previewMode, setPreviewMode,
    setActivities,
    setMessages,
    isLoading, setLoading,
    error, setError, clearError,
    isDeploying, setDeploying, setDeployProgress, deployProgress
  } = useFazStore();

  const [pageLoading, setPageLoading] = React.useState(true);
  const [previewHtml, setPreviewHtml] = React.useState<string | null>(null);

  // Helper to escape HTML
  const escapeHtml = (str: string) => {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  };

  // Generate preview HTML from project files
  const generatePreviewFromFiles = React.useCallback((fileList: { path: string; content: string }[]) => {
    const pageFile = fileList.find(f => f.path.includes('page.tsx') || f.path.includes('index.tsx'));
    const globalsCss = fileList.find(f => f.path.includes('globals.css'));
    
    if (!pageFile) {
      setPreviewHtml(null);
      return;
    }

    const previewDoc = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Preview</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    ${globalsCss?.content || ''}
    body { background: #0a0a0f; color: white; min-height: 100vh; }
  </style>
</head>
<body>
  <div id="preview-root">
    <div class="min-h-screen bg-gradient-to-b from-[#0a0a0f] to-[#1a1a2e] p-8">
      <div class="max-w-4xl mx-auto">
        <div class="text-center mb-8">
          <h1 class="text-4xl font-bold text-white mb-4">Preview Mode</h1>
          <p class="text-gray-400">
            This is a static preview. Full interactivity requires deployment.
          </p>
        </div>
        <div class="bg-[#12121a] rounded-xl p-6 border border-[#1e1e2e]">
          <pre class="text-sm text-[#94a3b8] overflow-auto max-h-[60vh]"><code>${escapeHtml(pageFile.content)}</code></pre>
        </div>
        <div class="mt-6 text-center">
          <p class="text-sm text-[#64748b]">
            ${fileList.length} files generated • Deploy to see live preview
          </p>
        </div>
      </div>
    </div>
  </div>
</body>
</html>`;
    
    setPreviewHtml(previewDoc);
  }, []);

  // Initialize workspace
  React.useEffect(() => {
    if (!projectId) return;

    const init = async () => {
      try {
        // Load project
        const project = await fazApi.getProject(projectId);
        setCurrentProject(project);

        // Load files
        const fileList = await fazApi.getFiles(projectId);
        setFiles(fileList);

        // Load activity history
        const activityList = await fazApi.getActivities(projectId);
        setActivities(activityList);

        // Load chat history
        const chatHistory = await fazApi.getChatHistory(projectId);
        setMessages(chatHistory);

        // Connect WebSocket
        fazWS.connect(projectId);
        
        // Generate preview from files
        generatePreviewFromFiles(fileList);
      } catch (err) {
        console.error('Workspace init failed:', err);
        setError('Failed to load workspace. Please try again.');
      } finally {
        setPageLoading(false);
      }
    };

    init();

    return () => {
      fazWS.disconnect();
    };
  }, [projectId, setCurrentProject, setFiles, setActivities, setMessages, setError, generatePreviewFromFiles]);

  // Handle chat message with optional images
  const handleSendMessage = async (content: string, imageUrls?: string[]) => {
    try {
      // If there are images, include them in the message
      let messageContent = content;
      if (imageUrls && imageUrls.length > 0) {
        messageContent = `${content}\n\n[Attached images: ${imageUrls.join(', ')}]`;
      }
      await fazApi.sendChatMessage(projectId, messageContent);
    } catch (err) {
      console.error('Failed to send message:', err);
      setError('Failed to send message. Please try again.');
    }
  };

  // Run pipeline
  const handleRunPipeline = async () => {
    try {
      setLoading(true);
      clearError();
      await fazApi.runPipeline(projectId);
    } catch (err) {
      console.error('Failed to run pipeline:', err);
      setError('Failed to start pipeline. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Stop pipeline
  const handleStopPipeline = async () => {
    try {
      await fazApi.stopPipeline(projectId);
    } catch (err) {
      console.error('Failed to stop pipeline:', err);
      setError('Failed to stop pipeline.');
    }
  };

  // Deploy project
  const handleDeploy = async () => {
    try {
      setDeploying(true);
      setDeployProgress('Initializing deployment...');
      
      const result = await fazApi.deployProject(projectId);
      
      if (result.success) {
        setDeployProgress('Deployment complete!');
        // Update project with new URLs
        if (result.preview_url || result.production_url) {
          setCurrentProject({
            ...currentProject!,
            preview_url: result.preview_url,
            production_url: result.production_url,
            github_repo: result.github_repo
          });
        }
        // Open preview in new tab
        if (result.preview_url) {
          window.open(result.preview_url, '_blank');
        }
      } else {
        setError(result.message || 'Deployment failed');
      }
    } catch (err) {
      console.error('Deploy failed:', err);
      setError('Deployment failed. Please try again.');
    } finally {
      setDeploying(false);
      setTimeout(() => setDeployProgress(null), 3000);
    }
  };

  // Refresh files
  const handleRefreshFiles = async () => {
    try {
      const fileList = await fazApi.getFiles(projectId);
      setFiles(fileList);
      generatePreviewFromFiles(fileList);
    } catch (err) {
      console.error('Failed to refresh files:', err);
    }
  };

  const getLanguage = (path: string) => {
    if (path.endsWith('.tsx') || path.endsWith('.ts')) return 'typescript';
    if (path.endsWith('.css')) return 'css';
    if (path.endsWith('.json')) return 'json';
    if (path.endsWith('.html')) return 'html';
    return 'plaintext';
  };

  // Loading state
  if (pageLoading) {
    return (
      <div className="h-screen bg-[#0A0A0F] flex items-center justify-center text-[#94A3B8]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 size={32} className="animate-spin text-[#6366F1]" />
          <p>Loading workspace...</p>
        </div>
      </div>
    );
  }

  const selectedFileData = selectedFile ? files.find(f => f.path === selectedFile) : null;
  const selectedContent = selectedFileData?.content || '// Select a file to view';
  const selectedLang = selectedFile ? getLanguage(selectedFile) : 'plaintext';
  const isProcessing = currentProject?.status === 'processing' || isLoading;
  const canDeploy = currentProject?.status === 'approved' || (files.length > 0 && !isProcessing);

  // Toolbar component
  const Toolbar = () => (
    <div className="h-12 bg-[#12121A] border-b border-[#1E1E2E] flex items-center justify-between px-4">
      {/* Left: Project info */}
      <div className="flex items-center gap-4">
        <h1 className="text-sm font-semibold text-[#F1F5F9]">
          {currentProject?.name || 'Untitled Project'}
        </h1>
        <span className={cn(
          "px-2 py-0.5 rounded text-xs font-medium",
          currentProject?.status === 'approved' && "bg-green-500/20 text-green-400",
          currentProject?.status === 'processing' && "bg-yellow-500/20 text-yellow-400",
          currentProject?.status === 'failed' && "bg-red-500/20 text-red-400",
          !['approved', 'processing', 'failed'].includes(currentProject?.status || '') && "bg-[#1E1E2E] text-[#94A3B8]"
        )}>
          {currentProject?.status || 'draft'}
        </span>
      </div>

      {/* Center: View tabs */}
      <div className="flex items-center gap-1 bg-[#0A0A0F] rounded-lg p-1">
        <button
          onClick={() => setActiveTab('code')}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors",
            activeTab === 'code' ? "bg-[#6366F1] text-white" : "text-[#94A3B8] hover:text-white"
          )}
        >
          <Code size={14} />
          Code
        </button>
        <button
          onClick={() => setActiveTab('preview')}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors",
            activeTab === 'preview' ? "bg-[#6366F1] text-white" : "text-[#94A3B8] hover:text-white"
          )}
        >
          <Eye size={14} />
          Preview
        </button>
        <button
          onClick={() => setActiveTab('split')}
          className={cn(
            "flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors",
            activeTab === 'split' ? "bg-[#6366F1] text-white" : "text-[#94A3B8] hover:text-white"
          )}
        >
          <Columns size={14} />
          Split
        </button>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {/* Preview device selector */}
        {activeTab !== 'code' && (
          <div className="flex items-center gap-1 mr-2 border-r border-[#1E1E2E] pr-2">
            <button
              onClick={() => setPreviewMode('mobile')}
              className={cn(
                "p-1.5 rounded transition-colors",
                previewMode === 'mobile' ? "bg-[#6366F1] text-white" : "text-[#64748B] hover:text-white"
              )}
              title="Mobile"
            >
              <Smartphone size={16} />
            </button>
            <button
              onClick={() => setPreviewMode('tablet')}
              className={cn(
                "p-1.5 rounded transition-colors",
                previewMode === 'tablet' ? "bg-[#6366F1] text-white" : "text-[#64748B] hover:text-white"
              )}
              title="Tablet"
            >
              <Tablet size={16} />
            </button>
            <button
              onClick={() => setPreviewMode('desktop')}
              className={cn(
                "p-1.5 rounded transition-colors",
                previewMode === 'desktop' ? "bg-[#6366F1] text-white" : "text-[#64748B] hover:text-white"
              )}
              title="Desktop"
            >
              <Monitor size={16} />
            </button>
          </div>
        )}

        <button
          onClick={handleRefreshFiles}
          className="p-2 text-[#94A3B8] hover:text-white hover:bg-[#1E1E2E] rounded transition-colors"
          title="Refresh files"
        >
          <RefreshCw size={16} />
        </button>

        {isProcessing ? (
          <button
            onClick={handleStopPipeline}
            className="flex items-center gap-2 px-3 py-1.5 bg-red-500/20 text-red-400 hover:bg-red-500/30 rounded text-sm font-medium transition-colors"
          >
            <Square size={14} />
            Stop
          </button>
        ) : (
          <button
            onClick={handleRunPipeline}
            className="flex items-center gap-2 px-3 py-1.5 bg-[#6366F1] text-white hover:bg-[#5558E3] rounded text-sm font-medium transition-colors"
          >
            <Play size={14} />
            Run
          </button>
        )}

        <button
          onClick={handleDeploy}
          disabled={!canDeploy || isDeploying}
          className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium transition-colors",
            canDeploy && !isDeploying
              ? "bg-green-500 text-white hover:bg-green-600"
              : "bg-[#1E1E2E] text-[#64748B] cursor-not-allowed"
          )}
        >
          {isDeploying ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              Deploying...
            </>
          ) : (
            <>
              <Rocket size={14} />
              Deploy
            </>
          )}
        </button>

        {currentProject?.preview_url && (
          <a
            href={currentProject.preview_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 px-2 py-1.5 text-[#94A3B8] hover:text-white transition-colors"
            title="Open preview"
          >
            <ExternalLink size={14} />
          </a>
        )}
      </div>
    </div>
  );

  // Error banner
  const ErrorBanner = () => error ? (
    <div className="bg-red-500/10 border-b border-red-500/20 px-4 py-2 flex items-center justify-between">
      <div className="flex items-center gap-2 text-red-400">
        <AlertCircle size={16} />
        <span className="text-sm">{error}</span>
      </div>
      <button onClick={clearError} className="text-red-400 hover:text-red-300">
        <X size={16} />
      </button>
    </div>
  ) : null;

  // Deploy progress banner
  const DeployBanner = () => deployProgress ? (
    <div className="bg-[#6366F1]/10 border-b border-[#6366F1]/20 px-4 py-2 flex items-center gap-2 text-[#6366F1]">
      <Loader2 size={16} className="animate-spin" />
      <span className="text-sm">{deployProgress}</span>
    </div>
  ) : null;

  // Left Sidebar Content
  const sidebarContent = (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="px-4 py-3 text-xs font-semibold text-[#64748B] uppercase tracking-wider flex items-center justify-between">
          <span>Files</span>
          <span className="text-[#94A3B8]">{files.length}</span>
        </div>
        <FileTree files={files.map(f => f.path)} />
      </div>
      
      {currentProject && (
        <>
          {/* GitHub/Vercel Connection Status */}
          <div className="px-4 py-3 border-t border-[#1E1E2E]">
            <ProjectSetupStatus 
              githubRepo={currentProject.github_repo}
              productionUrl={currentProject.production_url}
              vercelProjectId={currentProject.vercel_project_id}
            />
          </div>
          
          {/* Project Info */}
          <div className="p-4 border-t border-[#1E1E2E] bg-[#12121A]">
            <div className="text-xs text-[#64748B] mb-2">PROJECT INFO</div>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-[#64748B]">Status</span>
                <span className="text-[#F1F5F9] capitalize">{currentProject.status}</span>
              </div>
              {currentProject.current_agent && (
                <div className="flex justify-between">
                  <span className="text-[#64748B]">Agent</span>
                  <span className="text-[#6366F1]">{currentProject.current_agent}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-[#64748B]">Files</span>
                <span className="text-[#F1F5F9]">{currentProject.file_count || files.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Tokens</span>
                <span className="text-[#F1F5F9]">{currentProject.total_tokens_used?.toLocaleString() || 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#64748B]">Cost</span>
                <span className="text-[#F1F5F9]">${((currentProject.total_cost_cents || 0) / 100).toFixed(2)}</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );

  // Check if we're at an approval gate
  const isAtApprovalGate = currentProject?.awaiting_approval_for?.startsWith('awaiting_');

  // Right Panel Content (Activity + Chat)
  const rightPanelContent = (
    <div className="flex flex-col h-full">
      <div className="flex-1 min-h-0 relative">
        <AgentActivityFeed />
      </div>
      <div className="h-1/2 min-h-[300px] border-t border-[#1E1E2E] flex flex-col bg-[#0A0A0F]">
        <div className="p-3 border-b border-[#1E1E2E]">
          <span className="text-xs font-semibold text-[#F1F5F9]">Chat with Nicole</span>
        </div>
        <ChatMessages />
        
        {/* Approval Panel - shown when at a gate */}
        {isAtApprovalGate && (
          <div className="p-3 border-t border-[#1E1E2E]">
            <ApprovalPanel />
          </div>
        )}
        
        <div className="p-3">
          <ChatInput onSend={handleSendMessage} projectId={projectId} />
        </div>
      </div>
    </div>
  );

  // Preview wrapper with device frame
  const PreviewWithFrame = () => {
    const widthMap = {
      mobile: 'max-w-[375px]',
      tablet: 'max-w-[768px]',
      desktop: 'max-w-full'
    };

    return (
      <div className="h-full flex items-center justify-center bg-[#0A0A0F] p-4">
        <div className={cn("w-full h-full", widthMap[previewMode])}>
          {currentProject?.preview_url ? (
            <iframe
              src={currentProject.preview_url}
              className="w-full h-full rounded-lg border border-[#1E1E2E]"
              title="Live Preview"
            />
          ) : previewHtml ? (
            <iframe
              srcDoc={previewHtml}
              className="w-full h-full rounded-lg border border-[#1E1E2E]"
              title="Preview"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-[#12121A] rounded-lg border border-[#1E1E2E]">
              <div className="text-center">
                <Eye size={48} className="mx-auto text-[#64748B] mb-4" />
                <p className="text-[#94A3B8]">No preview available yet</p>
                <p className="text-sm text-[#64748B] mt-2">Run the pipeline to generate files</p>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="h-screen flex flex-col bg-[#0A0A0F]">
      <Toolbar />
      <ErrorBanner />
      <DeployBanner />
      
      <div className="flex-1 min-h-0">
        <WorkspaceLayout sidebar={sidebarContent} rightPanel={rightPanelContent}>
          <PanelGroup direction="horizontal">
            <Panel defaultSize={50} minSize={20}>
              {activeTab === 'preview' ? (
                <PreviewWithFrame />
              ) : activeTab === 'code' ? (
                <CodeViewer code={selectedContent} language={selectedLang} path={selectedFile || undefined} />
              ) : (
                <CodeViewer code={selectedContent} language={selectedLang} path={selectedFile || undefined} />
              )}
            </Panel>
            
            {activeTab === 'split' && (
              <>
                <PanelResizeHandle className="w-1 bg-[#1E1E2E] hover:bg-[#6366F1] transition-colors" />
                <Panel defaultSize={50} minSize={20}>
                  <PreviewWithFrame />
                </Panel>
              </>
            )}
          </PanelGroup>
        </WorkspaceLayout>
      </div>
    </div>
  );
}
