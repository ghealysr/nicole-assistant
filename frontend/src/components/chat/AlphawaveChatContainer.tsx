'use client';

import { useState, useEffect, useRef } from 'react';
import { AlphawaveChatInput, type FileAttachment } from './AlphawaveChatInput';
import { AlphawaveDashPanel } from './AlphawaveDashPanel';
import { AlphawaveHeader } from '../navigation/AlphawaveHeader';
import { useChat } from '@/lib/hooks/alphawave_use_chat';
import { useToast } from '@/components/ui/alphawave_toast';
import { useConversation } from '@/lib/context/ConversationContext';
import { getDynamicGreeting, getFormattedDate } from '@/lib/greetings';
import { NicoleMessageRenderer } from './NicoleMessageRenderer';
import { NicoleActivityStatus } from './NicoleActivityStatus';
import { LotusSphere, type ThinkingState } from './LotusSphere';
import type { ThinkingStep, ActivityStatus } from '@/lib/hooks/alphawave_use_chat';

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
 * Empty state component - shown when there are no messages
 * Features dynamic time-based greetings from Nicole
 */
function EmptyState({ greeting, date }: { greeting: string; date: string }) {
  return (
    <div className="empty-state">
      <div className="text-center">
        <div className="flex items-center justify-center mx-auto mb-4">
          <LotusSphere 
            state="default"
            size={120}
            isActive={true}
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

/**
 * ThinkingBox - Shows saved thinking steps in message history
 * Collapsible view of Nicole's reasoning process after completion
 */
function ThinkingBox({ 
  steps, 
  summary,
  defaultExpanded = false 
}: { 
  steps: ThinkingStep[]; 
  summary?: string;
  defaultExpanded?: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  
  if (!steps || steps.length === 0) return null;
  
  return (
    <div 
      className="mb-3 rounded-lg overflow-hidden"
      style={{ 
        backgroundColor: '#E8E0F0',
        border: '1px solid #D4C8E8',
      }}
    >
      {/* Header - clickable to expand */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-black/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div 
            className="w-4 h-4 rounded-full flex items-center justify-center"
            style={{ backgroundColor: '#B8A8D4' }}
          >
            <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <span className="text-xs font-medium text-gray-700">
            {summary || `${steps.length} reasoning step${steps.length > 1 ? 's' : ''}`}
          </span>
        </div>
        <svg 
          className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor" 
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {/* Expandable content */}
      <div className={`overflow-hidden transition-all duration-200 ${isExpanded ? 'max-h-96' : 'max-h-0'}`}>
        <div className="px-3 pb-3 space-y-2" style={{ borderTop: '1px solid #D4C8E8' }}>
          {steps.map((step, index) => (
            <div key={index} className="flex items-start gap-2 pt-2">
              <div 
                className={`w-3 h-3 rounded-full flex-shrink-0 mt-0.5 ${
                  step.status === 'complete' ? 'bg-[#7A9B93]' : 'bg-gray-300'
                }`}
              />
              <span className="text-xs text-gray-600">{step.description}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Message bubble component - Clean, minimal design
 * NO avatar or name for Nicole - just clean content
 */
interface MessageBubbleProps {
  message: Message;
  activityStatus?: ActivityStatus;
  showThinking?: boolean;
}

function MessageBubble({ message, activityStatus, showThinking = false }: MessageBubbleProps) {
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
  
  // Determine if we should show the real-time thinking block
  const shouldShowThinking = !isUser && showThinking && activityStatus && (
    activityStatus.isActive ||
    activityStatus.extendedThinking?.isThinking ||
    activityStatus.extendedThinking?.content ||
    activityStatus.extendedThinking?.isStreaming ||
    activityStatus.toolUses?.length > 0
  );
  
  return (
    <div className={`py-3 px-6 message ${isUser ? 'message-user' : 'message-assistant'} animate-fade-in-up`}>
      <div className="max-w-[800px] mx-auto">
        {isUser ? (
          // User message - keep avatar and name
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-semibold bg-[#7A9B93] text-white">
              G
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-sm mb-1.5 text-[#1f2937]">Glen</div>
              <div className="text-[15px] leading-relaxed text-[#374151]">
                {hasAttachments && (
                  <div className="flex flex-wrap gap-2 mb-2">
                    {message.attachments!.map(attachment => (
                      <AttachmentChip key={attachment.id} attachment={attachment} />
                    ))}
                  </div>
                )}
                {displayContent && (
                  <span className="message-text">{displayContent}</span>
                )}
              </div>
            </div>
          </div>
        ) : (
          // Nicole message - NO avatar, NO name, just clean content
          <div className="pl-11"> {/* Indent to align with user content */}
            {/* Real-time thinking block */}
            {shouldShowThinking && activityStatus && (
              <div className="mb-3">
                <NicoleActivityStatus status={activityStatus} />
              </div>
            )}
            
            {/* Saved thinking steps from history */}
            {message.thinkingSteps && message.thinkingSteps.length > 0 && !shouldShowThinking && (
              <ThinkingBox 
                steps={message.thinkingSteps} 
                summary={message.thinkingSummary}
                defaultExpanded={false}
              />
            )}
            
            {/* Nicole's response with rich formatting */}
            <NicoleMessageRenderer content={displayContent} />
            
            {/* Action buttons */}
            {displayContent && (
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
        )}
      </div>
    </div>
  );
}

/**
 * Main chat container component for Nicole V7.
 * Features a SINGLE persistent LotusSphere indicator at the bottom.
 */
export function AlphawaveChatContainer() {
  const { showToast } = useToast();
  const { currentConversationId, setCurrentConversationId } = useConversation();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  
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

  // Smart scroll: only auto-scroll if user is already near bottom, 
  // and ensure content doesn't get clipped at top
  useEffect(() => {
    const container = messagesContainerRef.current;
    const anchor = messagesEndRef.current;
    
    if (!container || !anchor) return;
    
    // Check if user is near the bottom (within 150px)
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 150;
    
    // Always scroll when there's new activity or if already near bottom
    if (isNearBottom || isPendingAssistant) {
      // Use scrollTop instead of scrollIntoView for more control
      // This scrolls to show the anchor but won't push first message out of view
      const targetScroll = container.scrollHeight - container.clientHeight;
      container.scrollTo({
        top: targetScroll,
        behavior: 'smooth'
      });
    }
  }, [messages, isPendingAssistant, activityStatus]);

  const hasMessages = messages.length > 0;

  // Calculate LotusSphere state based on activity
  const getLotusSphereState = (): ThinkingState => {
    // Active states - user sent message and awaiting response
    if (isLoading || isPendingAssistant) {
      // Check for specific tool activity first
      if (activityStatus?.toolUses?.some(t => t.isActive)) {
        const activeTool = activityStatus.toolUses.find(t => t.isActive);
        const toolName = activeTool?.name?.toLowerCase() || '';
        
        // Map tool types to animations
        if (toolName.includes('search') || toolName.includes('brave') || toolName.includes('web')) {
          return 'searching';
        }
        if (toolName.includes('memory') || toolName.includes('recall')) {
          return 'thinking';
        }
        // All other tools = processing (orange bursts)
        return 'processing';
      }
      
      // Extended thinking active
      if (activityStatus?.extendedThinking?.isThinking) return 'thinking';
      if (activityStatus?.extendedThinking?.isStreaming) return 'thinking';
      
      // Loading but no specific activity yet - searching (yellow pulse)
      return 'searching';
    }
    
    // Idle state
    return 'default';
  };

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
          {hasMessages || isPendingAssistant ? (
            <div ref={messagesContainerRef} className="flex-1 overflow-y-auto pt-8 pb-4">
              {/* All messages - first message gets extra top margin for header clearance */}
              {messages.map((message, index) => {
                const isLastMessage = index === messages.length - 1;
                const isAssistantMessage = message.role === 'assistant';
                const shouldShowThinking = isLastMessage && isAssistantMessage;
                const isFirstMessage = index === 0;
                
                return (
                  <div key={message.id} className={isFirstMessage ? 'mt-4' : ''}>
                    <MessageBubble 
                      message={message as Message}
                      activityStatus={shouldShowThinking ? activityStatus : undefined}
                      showThinking={shouldShowThinking}
                    />
                  </div>
                );
              })}
              
              {/* Thinking box when awaiting response (before first assistant message) */}
              {isPendingAssistant && (messages.length === 0 || messages[messages.length - 1]?.role === 'user') && activityStatus && (
                <div className="py-3 px-6 animate-fade-in-up">
                  <div className="max-w-[800px] mx-auto pl-11">
                    <NicoleActivityStatus status={activityStatus} />
                  </div>
                </div>
              )}
              
              {/* Scroll anchor - BEFORE LotusSphere so scroll doesn't push first message out of view */}
              <div ref={messagesEndRef} />
              
              {/* SINGLE PERSISTENT LOTUS SPHERE - left aligned under response */}
              <div className="px-6 pt-2 pb-4">
                <div className="max-w-[800px] mx-auto pl-11">
                  <LotusSphere 
                    state={getLotusSphereState()}
                    size={72}
                    isActive={true}
                  />
                </div>
              </div>
            </div>
          ) : (
            <EmptyState greeting={greeting} date={formattedDate} />
          )}
          
          {/* Input area */}
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
