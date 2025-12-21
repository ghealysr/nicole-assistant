'use client';

/**
 * Nicole Chat Component
 * 
 * Right panel chat interface for conversational interaction with Nicole.
 * This is the core of Enjineer - all commands, approvals, and feedback
 * flow through this chat just like Cursor.
 */

import React from 'react';
import { cn } from '@/lib/utils';
import { 
  Send, Loader2, Wrench, CheckCircle2, XCircle, 
  Sparkles, Code, FileText, Rocket
} from 'lucide-react';
import { useEnjineerStore, ChatMessage, ToolCall } from '@/lib/enjineer/store';
import { LotusSphere } from '@/components/chat/LotusSphere';

export function NicoleChat() {
  const {
    messages,
    addMessage,
    isNicoleThinking,
    setNicoleThinking,
    isChatCollapsed,
    currentProject,
  } = useEnjineerStore();

  const [input, setInput] = React.useState('');
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

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    addMessage(userMessage);
    setInput('');
    setNicoleThinking(true);

    // Placeholder for actual API call - will be connected in backend phase
    // For now, simulate Nicole's response
    setTimeout(() => {
      const nicoleMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `I received your message: "${userMessage.content}"\n\nThe Enjineer backend is not yet connected. Once connected, I'll be able to:\n\n• Create and edit files\n• Run your code\n• Deploy to production\n• Coordinate with my agents\n\nFor now, the UI is ready for you to explore!`,
        timestamp: new Date(),
      };
      addMessage(nicoleMessage);
      setNicoleThinking(false);
    }, 1500);
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
      <div className="h-14 border-b border-[#1E1E2E] flex items-center justify-between px-4">
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
              {isNicoleThinking ? 'Thinking...' : 'Ready to help'}
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
        
        {/* Thinking Indicator */}
        {isNicoleThinking && (
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

      {/* Input Area */}
      <div className="border-t border-[#1E1E2E] p-4">
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask Nicole anything..."
              rows={1}
              className="w-full bg-[#12121A] border border-[#1E1E2E] rounded-xl px-4 py-3 pr-12 text-sm text-white placeholder-[#64748B] resize-none focus:outline-none focus:border-[#8B5CF6] transition-colors"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isNicoleThinking}
              className={cn(
                "absolute right-2 bottom-2 p-2 rounded-lg transition-colors",
                input.trim() && !isNicoleThinking
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
        <div className="text-sm whitespace-pre-wrap leading-relaxed">
          {message.content}
        </div>
        
        {/* Tool Calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="mt-3 space-y-2">
            {message.toolCalls.map(tool => (
              <ToolCallDisplay key={tool.id} tool={tool} />
            ))}
          </div>
        )}

        {/* Timestamp */}
        <div className={cn(
          "text-[10px] mt-2",
          isUser ? "text-white/60" : "text-[#64748B]"
        )}>
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
}

// Tool Call Display
interface ToolCallDisplayProps {
  tool: ToolCall;
}

function ToolCallDisplay({ tool }: ToolCallDisplayProps) {
  const statusIcon = {
    pending: <Loader2 size={12} className="animate-spin text-[#64748B]" />,
    running: <Loader2 size={12} className="animate-spin text-[#8B5CF6]" />,
    complete: <CheckCircle2 size={12} className="text-green-500" />,
    error: <XCircle size={12} className="text-red-500" />,
  };

  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-[#0A0A0F] rounded-lg">
      <Wrench size={12} className="text-[#8B5CF6]" />
      <span className="text-xs text-[#94A3B8] flex-1 font-mono">
        {tool.name}
      </span>
      {statusIcon[tool.status]}
    </div>
  );
}

// Helper
function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

