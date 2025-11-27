'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { AlphawaveChatInput } from './AlphawaveChatInput';
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
}

/**
 * Thinking indicator component - shows spinning Nicole avatar
 */
function ThinkingIndicator() {
  return (
    <div className="py-4 px-6 animate-fade-in-up">
      <div className="max-w-[800px] mx-auto flex gap-3">
        {/* Nicole avatar - spinning */}
        <div className="w-8 h-8 rounded-full flex-shrink-0 animate-spin-slow">
          <Image 
            src="/images/nicole-thinking-avatar.png" 
            alt="Nicole thinking" 
            width={32} 
            height={32}
            className="rounded-full"
          />
        </div>
        <div className="flex-1">
          <div className="font-semibold text-sm mb-1.5 text-[#1f2937]">Nicole</div>
          <div className="text-[15px] leading-relaxed text-[#374151]">
            <span className="text-lavender-text font-serif text-sm">Thinking...</span>
          </div>
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
        {/* Nicole logo spinning */}
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
 * Simple markdown parser for Nicole's responses
 * Converts basic markdown to HTML
 */
function parseMarkdown(text: string): string {
  let html = text;
  
  // Escape HTML first
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  
  // Bold: **text** or __text__
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');
  
  // Italic: *text* or _text_
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/_(.+?)_/g, '<em>$1</em>');
  
  // Inline code: `code`
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // Numbered lists: 1. item
  html = html.replace(/^(\d+)\.\s+(.+)$/gm, '<li>$2</li>');
  
  // Bullet lists: - item or * item
  html = html.replace(/^[-*]\s+(.+)$/gm, '<li>$1</li>');
  
  // Wrap consecutive <li> in <ol> or <ul>
  html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => {
    if (match.includes('1.')) {
      return '<ol>' + match + '</ol>';
    }
    return '<ul>' + match + '</ul>';
  });
  
  // Headers: ## Header
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');
  
  // Paragraphs: double newlines
  html = html.split(/\n\n+/).map(p => {
    if (p.startsWith('<h') || p.startsWith('<ul') || p.startsWith('<ol') || p.startsWith('<pre')) {
      return p;
    }
    return `<p>${p}</p>`;
  }).join('');
  
  // Single line breaks within paragraphs
  html = html.replace(/\n/g, '<br/>');
  
  // Clean up extra <br/> in lists
  html = html.replace(/<\/li><br\/>/g, '</li>');
  html = html.replace(/<br\/><li>/g, '<li>');
  
  return html;
}

/**
 * Message bubble component
 */
function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  
  // Parse markdown for assistant messages
  const formattedContent = isUser ? message.content : parseMarkdown(message.content);
  
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
              <span className="message-text">{message.content}</span>
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
 * 
 * QA NOTES:
 * - Full redesign matching the HTML mockup
 * - Includes header with dashboard toggle
 * - Spinning Nicole avatar for thinking state
 * - Clean message layout with action buttons
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

  // Show toast when error state changes
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
                <MessageBubble key={message.id} message={message} />
              ))}
              {isLoading && <ThinkingIndicator />}
            </div>
          ) : (
            <EmptyState />
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
