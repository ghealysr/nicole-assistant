'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { WorkspaceLayout } from '@/components/faz/WorkspaceLayout';
import { FileTree } from '@/components/faz/FileTree';
import { CodeViewer } from '@/components/faz/CodeViewer';
import { PreviewPane } from '@/components/faz/PreviewPane';
import { AgentActivityFeed } from '@/components/faz/AgentActivityFeed';
import { ChatMessages } from '@/components/faz/ChatMessages';
import { ChatInput } from '@/components/faz/ChatInput';
import { fazApi } from '@/lib/faz/api';
import { fazWS } from '@/lib/faz/websocket';
import { useFazStore } from '@/lib/faz/store';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { Loader2 } from 'lucide-react';

export default function ProjectWorkspacePage() {
  const params = useParams();
  const projectId = parseInt(params.id as string);
  
  const { 
    currentProject, setCurrentProject,
    files, setFiles, selectedFile, fileMetadata,
    activeTab,
    activities, setActivities,
    setMessages
  } = useFazStore();

  const [loading, setLoading] = React.useState(true);

  // Initialize
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
      } catch (error) {
        console.error('Workspace init failed:', error);
      } finally {
        setLoading(false);
      }
    };

    init();

    return () => {
      fazWS.disconnect();
    };
  }, [projectId, setCurrentProject, setFiles, setActivities, setMessages]);

  const handleSendMessage = async (content: string) => {
    try {
      // Optimistic update handled by WS
      await fazApi.sendChatMessage(projectId, content);
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  const getLanguage = (path: string) => {
    if (path.endsWith('.tsx') || path.endsWith('.ts')) return 'typescript';
    if (path.endsWith('.css')) return 'css';
    if (path.endsWith('.json')) return 'json';
    return 'plaintext';
  };

  if (loading) {
    return (
      <div className="h-screen bg-[#0A0A0F] flex items-center justify-center text-[#94A3B8]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 size={32} className="animate-spin text-[#6366F1]" />
          <p>Loading workspace...</p>
        </div>
      </div>
    );
  }

  const selectedContent = selectedFile ? files.get(selectedFile) || '' : '// Select a file to view';
  const selectedLang = selectedFile ? getLanguage(selectedFile) : 'plaintext';

  // Left Sidebar Content
  const sidebarContent = (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        <div className="px-4 py-3 text-xs font-semibold text-[#64748B] uppercase tracking-wider">
          Files
        </div>
        <FileTree files={Array.from(files.keys())} />
      </div>
      
      {currentProject && (
        <div className="p-4 border-t border-[#1E1E2E] bg-[#12121A]">
          <div className="text-xs text-[#64748B] mb-2">PROJECT STATUS</div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-[#F1F5F9] capitalize">{currentProject.status}</span>
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          </div>
          {currentProject.current_agent && (
            <div className="text-xs text-[#94A3B8]">
              Agent: <span className="text-[#6366F1]">{currentProject.current_agent}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );

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
        <div className="p-3">
          <ChatInput onSend={handleSendMessage} />
        </div>
      </div>
    </div>
  );

  return (
    <WorkspaceLayout sidebar={sidebarContent} rightPanel={rightPanelContent}>
      <PanelGroup direction="horizontal">
        <Panel defaultSize={50} minSize={20}>
          {activeTab === 'preview' ? (
            <PreviewPane url={currentProject?.preview_url} />
          ) : activeTab === 'code' ? (
            <CodeViewer code={selectedContent} language={selectedLang} path={selectedFile || undefined} />
          ) : (
            // Split view - Code on left
            <CodeViewer code={selectedContent} language={selectedLang} path={selectedFile || undefined} />
          )}
        </Panel>
        
        {activeTab === 'split' && (
          <>
            <PanelResizeHandle className="w-1 bg-[#1E1E2E] hover:bg-[#6366F1] transition-colors" />
            <Panel defaultSize={50} minSize={20}>
              <PreviewPane url={currentProject?.preview_url} />
            </Panel>
          </>
        )}
      </PanelGroup>
    </WorkspaceLayout>
  );
}

