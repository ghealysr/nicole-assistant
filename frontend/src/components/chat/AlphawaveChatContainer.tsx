'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { AlphawaveChatInput, type FileAttachment } from './AlphawaveChatInput';
import { AlphawaveDashPanel } from './AlphawaveDashPanel';
import { AlphawaveHeader } from '../navigation/AlphawaveHeader';
import { useChat } from '@/lib/hooks/alphawave_use_chat';
import { useToast } from '@/components/ui/alphawave_toast';
import { useConversation } from '@/lib/context/ConversationContext';
import { getDynamicGreeting, getFormattedDate } from '@/lib/greetings';
import { NicoleMessageRenderer } from './NicoleMessageRenderer';
import { ThinkingBox, type ThinkingStep } from './NicoleThinkingUI';
import { NicoleActivityStatus } from './NicoleActivityStatus';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
  attachments?: FileAttachment[];
  thinkingSteps?: ThinkingStep[];
  thinkingSummary?: string;
}

/**
 * Thinking indicator component - shows thinking steps when available
 * (The spinning avatar is now shown in NicoleActivityStatus)
 */
function ThinkingIndicator({ steps }: { steps?: ThinkingStep[] }) {
  // Only show ThinkingBox if we have actual thinking steps
  if (steps && steps.length > 0) {
    return (
      <div className="py-4 px-6 animate-fade-in-up">
        <div className="max-w-[800px] mx-auto">
          <div className="flex gap-3">
            {/* Nicole Avatar */}
            <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-semibold bg-lavender text-white">
              N
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-sm mb-1.5 text-[#1f2937]">Nicole</div>
              <ThinkingBox steps={steps} defaultExpanded={true} />
            </div>
          </div>
        </div>
      </div>
    );
  }
  
  // Return null - activity status box handles the loading state now
  return null;
}

/**
 * Empty state component - shown when there are no messages
 * Features dynamic time-based greetings from Nicole
 */
function EmptyState({ greeting, date }: { greeting: string; date: string }) {
  return (
    <div className="empty-state">
      <div className="text-center">
        <div className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-5">
          <Image 
            src="/images/nicole-thinking-avatar.png" 
            alt="Nicole" 
            width={80} 
            height={80}
            className="rounded-full"
          />
        </div>
        <h2 className="empty-title">{greeting || 'Hey Glen. What can I help you with?'}</h2>
        <p className="empty-subtitle">{date || '\u00A0'}</p>
      </div>
    </div>
  );
}

/**
 * Claude-style file attachment chip.
 * Clean, minimal display - no Azure metadata visible.
 */
function AttachmentChip({ attachment }: { attachment: FileAttachment }) {
  const isImage = attachment.type.startsWith('image/');
  
  const getIcon = () => {
    if (isImage) {
      return (
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <circle cx="8.5" cy="8.5" r="1.5"/>
          <path d="M21 15l-5-5L5 21"/>
        </svg>
      );
    }
    if (attachment.type.includes('pdf')) {
      return (
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
          <path d="M14 2v6h6"/>
        </svg>
      );
    }
    return (
      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
        <path d="M14 2v6h6"/>
      </svg>
    );
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const truncateName = (name: string, maxLen: number = 18): string => {
    if (name.length <= maxLen) return name;
    const ext = name.split('.').pop() || '';
    const baseName = name.slice(0, name.length - ext.length - 1);
    const truncated = baseName.slice(0, maxLen - ext.length - 4);
    return `${truncated}...${ext}`;
  };

  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg 
                    bg-[#e8e7e0] border border-[#d8d7cc] text-[#4b5563] text-xs">
      <span className="text-[#6b7280]">{getIcon()}</span>
      <span className="font-medium">{truncateName(attachment.name)}</span>
      <span className="text-[#9ca3af]">{formatSize(attachment.size)}</span>
    </div>
  );
}

/**
 * Clean message content by removing any [Uploaded: ...] metadata blocks.
 */
function cleanMessageContent(content: string): string {
  let cleaned = content.replace(/\[Uploaded:[^\]]*\]\n*/g, '');
  cleaned = cleaned.trim();
  cleaned = cleaned.replace(/^Please review and summarize the document\(s\) I just uploaded\.?\s*/i, '');
  cleaned = cleaned.replace(/^Please review what I've shared\.?\s*/i, '');
  return cleaned;
}

// Markdown parsing is now handled by NicoleMessageRenderer

/**
 * Message bubble component - Claude style with attachment chips
 * Uses NicoleMessageRenderer for assistant messages with rich formatting
 */
function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  const hasAttachments = message.attachments && message.attachments.length > 0;
  
  // Clean content for user messages (remove metadata)
  const displayContent = isUser ? cleanMessageContent(message.content) : message.content;
  
  const [copied, setCopied] = useState(false);
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  return (
    <div className={`py-4 px-6 message ${isUser ? 'message-user' : 'message-assistant'} animate-fade-in-up`}>
      <div className="max-w-[800px] mx-auto flex gap-3">
        {/* Avatar */}
        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-semibold ${
          isUser ? 'bg-[#7A9B93] text-white' : 'bg-lavender text-white'
        }`}>
          {isUser ? 'G' : 'N'}
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-sm mb-1.5 text-[#1f2937]">
            {isUser ? 'Glen' : 'Nicole'}
          </div>
          
          {isUser ? (
            <div className="text-[15px] leading-relaxed text-[#374151]">
              {/* Attachment chips - Claude style */}
              {hasAttachments && (
                <div className="flex flex-wrap gap-2 mb-2">
                  {message.attachments!.map(attachment => (
                    <AttachmentChip key={attachment.id} attachment={attachment} />
                  ))}
                </div>
              )}
              
              {/* User's text message (clean, no metadata) */}
              {displayContent && (
                <span className="message-text">{displayContent}</span>
              )}
            </div>
          ) : (
            <>
              {/* Thinking steps if available */}
              {message.thinkingSteps && message.thinkingSteps.length > 0 && (
                <ThinkingBox 
                  steps={message.thinkingSteps} 
                  summary={message.thinkingSummary}
                  defaultExpanded={false}
                />
              )}
              
              {/* Nicole's response with rich formatting */}
              <NicoleMessageRenderer content={displayContent} />
            </>
          )}
          
          {/* Action buttons for assistant messages */}
          {!isUser && (
            <div className="message-actions mt-3 flex gap-1">
              <button className="action-btn p-1.5 border-0 bg-transparent rounded-md cursor-pointer hover:bg-black/5" title="Good response">
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} className="w-3.5 h-3.5 stroke-[#6b7280]">
                  <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
                </svg>
              </button>
              <button className="action-btn p-1.5 border-0 bg-transparent rounded-md cursor-pointer hover:bg-black/5" title="Bad response">
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} className="w-3.5 h-3.5 stroke-[#6b7280]">
                  <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/>
                </svg>
              </button>
              <button 
                className="action-btn p-1.5 border-0 bg-transparent rounded-md cursor-pointer hover:bg-black/5" 
                title={copied ? "Copied!" : "Copy"}
                onClick={handleCopy}
              >
                {copied ? (
                  <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} className="w-3.5 h-3.5 stroke-[#7A9B93]">
                    <path d="M5 13l4 4L19 7"/>
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} className="w-3.5 h-3.5 stroke-[#6b7280]">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                  </svg>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Main chat container component for Nicole V7.
 * Claude-style file uploads with invisible AI processing.
 * Integrates with conversation context for cross-component state management.
 */
export function AlphawaveChatContainer() {
  const { showToast } = useToast();
  const { currentConversationId, setCurrentConversationId } = useConversation();
  
  const { 
    messages, 
    sendMessage, 
    isLoading, 
    isPendingAssistant,
    error, 
    clearError,
    conversationId,
    setConversationId,
    activityStatus,
  } = useChat({
    conversationId: currentConversationId ? String(currentConversationId) : undefined,
    onError: (err) => {
      showToast(err.message, 'error');
    },
  });
  
  const [dashOpen, setDashOpen] = useState(false);
  const [dashboardWidth, setDashboardWidth] = useState(420);

  // Sync conversation ID from chat hook to context
  useEffect(() => {
    if (conversationId && conversationId !== currentConversationId) {
      setCurrentConversationId(conversationId);
    }
  }, [conversationId, currentConversationId, setCurrentConversationId]);

  // When context conversation changes (e.g., from Chats panel), update chat hook
  useEffect(() => {
    if (currentConversationId !== conversationId) {
      setConversationId(currentConversationId);
    }
  }, [currentConversationId, conversationId, setConversationId]);

  useEffect(() => {
    if (error) {
      showToast(error, 'error');
      clearError();
    }
  }, [error, showToast, clearError]);

  // Dynamic greeting state - initialized client-side only to avoid hydration mismatch
  const [greeting, setGreeting] = useState<string>('');
  const [formattedDate, setFormattedDate] = useState<string>('');

  // Generate greeting on client-side only (after hydration)
  useEffect(() => {
    setGreeting(getDynamicGreeting());
    setFormattedDate(getFormattedDate());
  }, []); // Run once on mount

  // Regenerate greeting when starting a new conversation
  useEffect(() => {
    if (currentConversationId === null && messages.length === 0) {
      setGreeting(getDynamicGreeting());
    }
  }, [currentConversationId, messages.length]);

  const hasMessages = messages.length > 0 || isPendingAssistant;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <AlphawaveHeader 
        onToggleDashboard={() => setDashOpen(!dashOpen)} 
        isDashboardOpen={dashOpen}
      />
      
      <div className="flex flex-1 overflow-hidden">
        {/* Chat area */}
        <div className="flex-1 flex flex-col min-w-[400px] transition-all duration-300 bg-[#F5F4ED]">
          {/* Messages area */}
          {hasMessages ? (
            <div className="flex-1 overflow-y-auto py-4">
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message as Message} />
              ))}
              {/* Real-time activity status box */}
              {activityStatus.isActive && (
                <NicoleActivityStatus status={activityStatus} />
              )}
              {/* Thinking steps (shown after activity completes if available) */}
              {(isLoading || isPendingAssistant) && <ThinkingIndicator />}
            </div>
          ) : (
            <EmptyState greeting={greeting} date={formattedDate} />
          )}
          
          {/* Input area - now passes attachments */}
          <AlphawaveChatInput 
            onSendMessage={sendMessage} 
            isLoading={isLoading} 
          />
        </div>

        {/* Dashboard panel */}
        <AlphawaveDashPanel 
          isOpen={dashOpen} 
          onClose={() => setDashOpen(false)}
          width={dashboardWidth}
          onWidthChange={setDashboardWidth}
        />
      </div>
    </div>
  );
}
