'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { AlphawaveChatInput, type FileAttachment } from './AlphawaveChatInput';
import { AlphawaveDashPanel } from './AlphawaveDashPanel';
import { AlphawaveHeader } from '../navigation/AlphawaveHeader';
import { useChat } from '@/lib/hooks/alphawave_use_chat';
import { useToast } from '@/components/ui/alphawave_toast';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
  attachments?: FileAttachment[];
}

/**
 * Thinking indicator component - shows only the spinning Nicole avatar
 */
function ThinkingIndicator() {
  return (
    <div className="py-6 px-6 animate-fade-in-up">
      <div className="max-w-[800px] mx-auto flex justify-center">
        <div className="w-12 h-12 animate-spin-slow">
          <Image 
            src="/images/nicole-thinking-avatar.png" 
            alt="Nicole thinking" 
            width={48} 
            height={48}
            className="w-12 h-12"
          />
        </div>
      </div>
    </div>
  );
}

/**
 * Empty state component - shown when there are no messages
 */
function EmptyState() {
  return (
    <div className="empty-state">
      <div className="text-center">
        <div className="w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-5 animate-spin-slow">
          <Image 
            src="/images/nicole-thinking-avatar.png" 
            alt="Nicole" 
            width={80} 
            height={80}
            className="rounded-full"
          />
        </div>
        <h2 className="empty-title">How can I help you today?</h2>
        <p className="empty-subtitle">Ask me anything, I&apos;m here for you.</p>
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
 * Simple markdown parser for Nicole's responses
 */
function parseMarkdown(text: string): string {
  let html = text;
  
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/_(.+?)_/g, '<em>$1</em>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  html = html.replace(/^(\d+)\.\s+(.+)$/gm, '<li>$2</li>');
  html = html.replace(/^[-*]\s+(.+)$/gm, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => {
    if (match.includes('1.')) {
      return '<ol>' + match + '</ol>';
    }
    return '<ul>' + match + '</ul>';
  });
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  html = html.split(/\n\n+/).map(p => {
    if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<ol') || p.startsWith('<pre')) {
      return p;
    }
    return `<p>${p}</p>`;
  }).join('');
  html = html.replace(/\n/g, '<br/>');
  html = html.replace(/<\/li><br\/>/g, '</li>');
  html = html.replace(/<br\/><li>/g, '<li>');
  
  return html;
}

/**
 * Message bubble component - Claude style with attachment chips
 */
function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  const hasAttachments = message.attachments && message.attachments.length > 0;
  
  // Clean content for user messages (remove metadata)
  const displayContent = isUser ? cleanMessageContent(message.content) : message.content;
  const formattedContent = isUser ? displayContent : parseMarkdown(displayContent);
  
  return (
    <div className={`py-4 px-6 message ${isUser ? 'message-user' : 'message-assistant'}`}>
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
            <div 
              className="nicole-message"
              dangerouslySetInnerHTML={{ __html: formattedContent }}
            />
          )}
          
          {/* Action buttons for assistant messages */}
          {!isUser && (
            <div className="message-actions">
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
              <button className="action-btn p-1.5 border-0 bg-transparent rounded-md cursor-pointer hover:bg-black/5" title="Copy">
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} className="w-3.5 h-3.5 stroke-[#6b7280]">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
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
 */
export function AlphawaveChatContainer() {
  const { showToast } = useToast();
  const { messages, sendMessage, isLoading, error, clearError } = useChat({
    onError: (err) => {
      showToast(err.message, 'error');
    },
  });
  const [dashOpen, setDashOpen] = useState(false);
  const [dashboardWidth, setDashboardWidth] = useState(420);

  useEffect(() => {
    if (error) {
      showToast(error, 'error');
      clearError();
    }
  }, [error, showToast, clearError]);

  const hasMessages = messages.length > 0;

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
              {isLoading && <ThinkingIndicator />}
            </div>
          ) : (
            <EmptyState />
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
