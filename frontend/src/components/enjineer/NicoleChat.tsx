'use client';

/**
 * Nicole Chat Component
 * 
 * Right panel chat interface for conversational interaction with Nicole.
 * This is the core of Enjineer - all commands, approvals, and feedback
 * flow through this chat just like Cursor.
 * 
 * Handles:
 * - Streaming text responses
 * - Tool call visualization
 * - Code creation/update events
 * - Approval request handling
 */

import React from 'react';
import { cn } from '@/lib/utils';
import { 
  Send, Loader2, Wrench, CheckCircle2, XCircle, 
  Sparkles, Code, FileText, Rocket, File, 
  AlertCircle, ThumbsUp, ThumbsDown
} from 'lucide-react';
import { useEnjineerStore, ChatMessage, ToolCall } from '@/lib/enjineer/store';
import { LotusSphere } from '@/components/chat/LotusSphere';
import { enjineerApi, ChatEvent } from '@/lib/enjineer/api';

export function NicoleChat() {
  const {
    messages,
    addMessage,
    updateMessage,
    isNicoleThinking,
    setNicoleThinking,
    isChatCollapsed,
    currentProject,
    addFile,
    updateFile,
    openFile,
    setPlan,
    setPlanOverview,
  } = useEnjineerStore();

  const [input, setInput] = React.useState('');
  const [pendingApproval, setPendingApproval] = React.useState<{
    id: string;
    title: string;
  } | null>(null);
  const messagesEndRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLTextAreaElement>(null);

  // Auto-scroll on new messages
  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  React.useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || isNicoleThinking) return;
    if (!currentProject || !currentProject.id || currentProject.id === 0) {
      addMessage({
        id: crypto.randomUUID(),
        role: 'system',
        content: 'Creating project... please wait a moment and try again.',
        timestamp: new Date(),
      });
      return;
    }

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    addMessage(userMessage);
    setInput('');
    setNicoleThinking(true);

    // Create placeholder for Nicole's streaming response
    const nicoleMessageId = crypto.randomUUID();
    addMessage({
      id: nicoleMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
      toolCalls: [],
    });

    try {
      let fullContent = '';
      const toolCalls: ToolCall[] = [];
      let toolIdCounter = 0;

      await enjineerApi.chat(
        currentProject.id,
        userMessage.content,
        (event: ChatEvent) => {
          switch (event.type) {
            case 'text':
              // Append text content
              fullContent += event.content || '';
              updateMessage(nicoleMessageId, { 
                content: fullContent,
                toolCalls: [...toolCalls],
              });
              break;

            case 'thinking':
              // Could show thinking in a special way
              console.log('[Nicole] Thinking:', event.content);
              break;

            case 'tool_use':
              // Tool is starting or running
              const toolCall: ToolCall = {
                id: `tool-${toolIdCounter++}`,
                name: event.tool || 'unknown',
                status: event.status === 'starting' ? 'pending' : 
                        event.status === 'running' ? 'running' : 'pending',
                result: undefined,
              };
              toolCalls.push(toolCall);
              updateMessage(nicoleMessageId, { 
                content: fullContent,
                toolCalls: [...toolCalls],
              });
              break;

            case 'tool_result':
              // Tool completed - update the last tool call
              const lastTool = toolCalls[toolCalls.length - 1];
              if (lastTool) {
                const result = event.result || {};
                lastTool.status = result.success ? 'complete' : 'error';
                lastTool.result = JSON.stringify(result.result || result.error || result);
                updateMessage(nicoleMessageId, { 
                  content: fullContent,
                  toolCalls: [...toolCalls],
                });
                
                // Refresh plan and files when create_plan succeeds
                if (lastTool.name === 'create_plan' && result.success && currentProject?.id) {
                  // Refresh plan
                  enjineerApi.getPlan(currentProject.id).then(({ overview, phases }) => {
                    setPlanOverview(overview);
                    setPlan(phases);
                  }).catch(console.error);
                  // Refresh files to get plan.md
                  enjineerApi.getFiles(currentProject.id).then((files) => {
                    useEnjineerStore.getState().setFiles(files);
                  }).catch(console.error);
                }
              }
              break;

            case 'code':
              // File was created or updated - update the store
              if (event.path && event.content !== undefined) {
                const isNewFile = event.action === 'created';
                const language = getLanguageFromPath(event.path);
                
                if (isNewFile) {
                  addFile({
                    path: event.path,
                    content: event.content,
                    language,
                    isModified: false,
                  });
                } else {
                  updateFile(event.path, event.content);
                }
                
                // Open the file in the editor
                openFile(event.path);
              }
              break;

            case 'approval_required':
              // Show approval UI
              if (event.approval_id) {
                setPendingApproval({
                  id: event.approval_id,
                  title: event.title || 'Action requires approval',
                });
              }
              break;

            case 'error':
              // Error occurred
              console.error('[Nicole] Error:', event.content);
              fullContent += `\n\n❌ Error: ${event.content}`;
              updateMessage(nicoleMessageId, { 
                content: fullContent,
                toolCalls: [...toolCalls],
              });
              break;

            case 'done':
              // Stream complete
              console.log('[Nicole] Stream complete');
              break;
          }
        }
      );

      // Finalize the message
      updateMessage(nicoleMessageId, { 
        content: fullContent || "I'm ready to help! What would you like to build?",
        isStreaming: false,
        toolCalls: [...toolCalls],
      });
    } catch (error) {
      console.error('[NicoleChat] Error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      
      // Check for auth errors
      if (errorMessage.includes('Invalid or expired token') || errorMessage.includes('401')) {
        updateMessage(nicoleMessageId, {
          content: `⚠️ **Session expired.** Please refresh the page to continue.\n\n[Click here to refresh](javascript:window.location.reload())`,
          isStreaming: false,
        });
        // Also show an alert
        setTimeout(() => {
          if (confirm('Your session has expired. Would you like to refresh the page?')) {
            window.location.reload();
          }
        }, 100);
      } else {
        updateMessage(nicoleMessageId, {
          content: `I encountered an error: ${errorMessage}. Please try again.`,
          isStreaming: false,
        });
      }
    } finally {
      setNicoleThinking(false);
    }
  };

  const handleApprove = async () => {
    if (!pendingApproval || !currentProject) return;
    
    try {
      await enjineerApi.approveAction(currentProject.id, pendingApproval.id);
      addMessage({
        id: crypto.randomUUID(),
        role: 'system',
        content: `✅ Approved: ${pendingApproval.title}`,
        timestamp: new Date(),
      });
    } catch (error) {
      console.error('Failed to approve:', error);
    }
    setPendingApproval(null);
  };

  const handleReject = async () => {
    if (!pendingApproval || !currentProject) return;
    
    try {
      await enjineerApi.rejectAction(currentProject.id, pendingApproval.id);
      addMessage({
        id: crypto.randomUUID(),
        role: 'system',
        content: `❌ Rejected: ${pendingApproval.title}`,
        timestamp: new Date(),
      });
    } catch (error) {
      console.error('Failed to reject:', error);
    }
    setPendingApproval(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (isChatCollapsed) {
    return null;
  }

  return (
    <div className="w-96 bg-[#0D0D12] border-l border-[#1E1E2E] flex flex-col h-full">
      {/* Header */}
      <div className="h-14 border-b border-[#1E1E2E] flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="relative">
            <LotusSphere 
              state={isNicoleThinking ? 'thinking' : 'default'}
              size={32}
              isActive={true}
            />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Nicole</h3>
            <p className="text-[10px] text-[#8B5CF6]">
              {isNicoleThinking ? 'Working...' : 'Ready to help'}
            </p>
          </div>
        </div>
        {currentProject && (
          <div className="text-right">
            <p className="text-[10px] text-[#64748B]">Project</p>
            <p className="text-xs text-[#94A3B8] font-medium truncate max-w-[120px]">
              {currentProject.name}
            </p>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
        {messages.length === 0 ? (
          <WelcomeMessage />
        ) : (
          messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))
        )}
        
        {/* Thinking Indicator - only show when streaming hasn't started */}
        {isNicoleThinking && messages.length > 0 && messages[messages.length - 1]?.content === '' && (
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-full bg-[#8B5CF6]/20 flex items-center justify-center">
              <Loader2 size={16} className="text-[#8B5CF6] animate-spin" />
            </div>
            <div className="flex-1 bg-[#12121A] rounded-2xl rounded-tl-none px-4 py-3">
              <div className="flex items-center gap-2 text-[#8B5CF6] text-sm">
                <Sparkles size={14} className="animate-pulse" />
                <span>Nicole is thinking...</span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Approval Banner */}
      {pendingApproval && (
        <div className="border-t border-[#1E1E2E] p-4 bg-[#1a1520]">
          <div className="flex items-center gap-2 mb-3">
            <AlertCircle size={16} className="text-[#F59E0B]" />
            <span className="text-sm font-medium text-white">Approval Required</span>
          </div>
          <p className="text-xs text-[#94A3B8] mb-3">{pendingApproval.title}</p>
          <div className="flex gap-2">
            <button
              onClick={handleApprove}
              className="flex-1 py-2 px-3 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              <ThumbsUp size={14} />
              Approve
            </button>
            <button
              onClick={handleReject}
              className="flex-1 py-2 px-3 bg-[#1E1E2E] hover:bg-[#2E2E3E] text-[#94A3B8] text-sm rounded-lg flex items-center justify-center gap-2 transition-colors"
            >
              <ThumbsDown size={14} />
              Reject
            </button>
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="border-t border-[#1E1E2E] p-4 shrink-0">
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={currentProject ? "Ask Nicole anything..." : "Select a project first..."}
              disabled={!currentProject}
              rows={1}
              className="w-full bg-[#12121A] border border-[#1E1E2E] rounded-xl px-4 py-3 pr-12 text-sm text-white placeholder-[#64748B] resize-none focus:outline-none focus:border-[#8B5CF6] transition-colors disabled:opacity-50"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isNicoleThinking || !currentProject}
              className={cn(
                "absolute right-2 bottom-2 p-2 rounded-lg transition-colors",
                input.trim() && !isNicoleThinking && currentProject
                  ? "bg-[#8B5CF6] text-white hover:bg-[#7C3AED]"
                  : "bg-[#1E1E2E] text-[#64748B]"
              )}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
        <p className="text-[10px] text-[#64748B] mt-2 text-center">
          Press Enter to send • Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}

// Welcome Message Component
function WelcomeMessage() {
  return (
    <div className="text-center py-8">
      <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-[#8B5CF6] to-[#6366F1] flex items-center justify-center">
        <Sparkles size={28} className="text-white" />
      </div>
      <h3 className="text-lg font-semibold text-white mb-2">
        Welcome to Enjineer
      </h3>
      <p className="text-sm text-[#94A3B8] mb-6 max-w-[280px] mx-auto">
        I&apos;m Nicole, your coding partner. Tell me what you want to build and I&apos;ll help you create it.
      </p>
      
      <div className="space-y-2">
        <p className="text-xs text-[#64748B] mb-3">Try asking me to:</p>
        <QuickAction icon={<FileText size={14} />} text="Create a Next.js landing page" />
        <QuickAction icon={<Code size={14} />} text="Add a contact form component" />
        <QuickAction icon={<Rocket size={14} />} text="Deploy to production" />
      </div>
    </div>
  );
}

function QuickAction({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <button className="w-full px-4 py-2.5 bg-[#12121A] hover:bg-[#1E1E2E] border border-[#1E1E2E] rounded-lg text-sm text-[#94A3B8] hover:text-white transition-colors flex items-center gap-2 text-left">
      <span className="text-[#8B5CF6]">{icon}</span>
      {text}
    </button>
  );
}

// Message Bubble Component
interface MessageBubbleProps {
  message: ChatMessage;
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <div className="px-4 py-2 bg-[#1E1E2E]/50 rounded-full text-xs text-[#64748B]">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex items-start gap-3", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div className={cn(
        "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
        isUser 
          ? "bg-[#1E1E2E]"
          : "bg-gradient-to-br from-[#8B5CF6] to-[#6366F1]"
      )}>
        {isUser ? (
          <span className="text-xs font-semibold text-white">G</span>
        ) : (
          <Sparkles size={14} className="text-white" />
        )}
      </div>

      {/* Content */}
      <div className={cn(
        "flex-1 rounded-2xl px-4 py-3 max-w-[85%]",
        isUser 
          ? "bg-[#8B5CF6] text-white rounded-tr-none"
          : "bg-[#12121A] text-[#F1F5F9] rounded-tl-none"
      )}>
        {/* Streaming indicator */}
        {message.isStreaming && !message.content && (
          <div className="flex items-center gap-2 text-[#8B5CF6]">
            <Loader2 size={14} className="animate-spin" />
            <span className="text-sm">Nicole is thinking...</span>
          </div>
        )}
        
        {/* Text content */}
        {message.content && (
          <div className="text-sm whitespace-pre-wrap leading-relaxed">
            {message.content}
          </div>
        )}
        
        {/* Tool Calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-3 space-y-2">
            {message.toolCalls.map(tool => (
              <ToolCallDisplay key={tool.id} tool={tool} />
            ))}
          </div>
        )}

        {/* Timestamp */}
        {!message.isStreaming && (
          <div className={cn(
            "text-[10px] mt-2",
            isUser ? "text-white/60" : "text-[#64748B]"
          )}>
            {formatTime(message.timestamp)}
          </div>
        )}
      </div>
    </div>
  );
}

// Tool Call Display
interface ToolCallDisplayProps {
  tool: ToolCall;
}

function ToolCallDisplay({ tool }: ToolCallDisplayProps) {
  const statusConfig = {
    pending: { icon: <Loader2 size={12} className="animate-spin text-[#64748B]" />, color: 'text-[#64748B]' },
    running: { icon: <Loader2 size={12} className="animate-spin text-[#8B5CF6]" />, color: 'text-[#8B5CF6]' },
    complete: { icon: <CheckCircle2 size={12} className="text-green-500" />, color: 'text-green-500' },
    error: { icon: <XCircle size={12} className="text-red-500" />, color: 'text-red-500' },
  };

  const config = statusConfig[tool.status];
  
  // Tool name to icon mapping
  const toolIcon = {
    create_file: <File size={12} />,
    update_file: <Code size={12} />,
    delete_file: <XCircle size={12} />,
    create_plan: <FileText size={12} />,
    dispatch_agent: <Sparkles size={12} />,
    deploy: <Rocket size={12} />,
  }[tool.name] || <Wrench size={12} />;

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-[#0A0A0F] rounded-lg border border-[#1E1E2E]">
      <span className="text-[#8B5CF6]">{toolIcon}</span>
      <span className="text-xs text-[#94A3B8] flex-1 font-mono">
        {formatToolName(tool.name)}
      </span>
      {config.icon}
    </div>
  );
}

// Helpers
function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatToolName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function getLanguageFromPath(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase();
  const langMap: Record<string, string> = {
    ts: 'typescript',
    tsx: 'typescript',
    js: 'javascript',
    jsx: 'javascript',
    css: 'css',
    json: 'json',
    md: 'markdown',
    html: 'html',
  };
  return langMap[ext || ''] || 'plaintext';
}
