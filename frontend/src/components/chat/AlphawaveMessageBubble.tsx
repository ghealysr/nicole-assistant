'use client';

import { AlphawaveMessageActions } from './AlphawaveMessageActions';
import type { FileAttachment } from './AlphawaveChatInput';

/**
 * Interface for message objects.
 */
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
  attachments?: FileAttachment[];
}

/**
 * Props for AlphawaveMessageBubble.
 */
interface AlphawaveMessageBubbleProps {
  message: Message;
}

/**
 * Claude-style file attachment chip.
 * Shows icon + filename, NOT the full image or Azure metadata.
 */
function AttachmentChip({ attachment }: { attachment: FileAttachment }) {
  const isImage = attachment.type.startsWith('image/');
  
  /**
   * Get icon based on file type.
   */
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
          <path d="M10 9H8"/>
          <path d="M16 13H8"/>
          <path d="M16 17H8"/>
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

  /**
   * Format file size.
   */
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  /**
   * Truncate filename with ellipsis.
   */
  const truncateName = (name: string, maxLen: number = 20): string => {
    if (name.length <= maxLen) return name;
    const ext = name.split('.').pop() || '';
    const baseName = name.slice(0, name.length - ext.length - 1);
    const truncated = baseName.slice(0, maxLen - ext.length - 4);
    return `${truncated}...${ext}`;
  };

  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg 
                    bg-[#f5f5f0] border border-[#e5e5dc] text-[#4b5563] text-xs
                    hover:bg-[#eeede6] transition-colors cursor-default">
      <span className="text-[#6b7280]">{getIcon()}</span>
      <span className="font-medium">{truncateName(attachment.name)}</span>
      <span className="text-[#9ca3af]">{formatSize(attachment.size)}</span>
    </div>
  );
}

/**
 * Clean message content by removing any [Uploaded: ...] metadata blocks.
 * This ensures Azure analysis is never visible to users.
 */
function cleanMessageContent(content: string): string {
  // Remove [Uploaded: ...] blocks
  let cleaned = content.replace(/\[Uploaded:[^\]]*\]\n*/g, '');
  // Remove any leading/trailing whitespace
  cleaned = cleaned.trim();
  // Remove "Please review and summarize..." auto-generated text
  cleaned = cleaned.replace(/^Please review and summarize the document\(s\) I just uploaded\.?\s*/i, '');
  cleaned = cleaned.replace(/^Please review what I've shared\.?\s*/i, '');
  return cleaned;
}

/**
 * Message bubble component for Nicole V7.
 * Claude-style design with invisible AI processing.
 * 
 * Design:
 * - Nicole's messages: Left-aligned, prose styling
 * - User messages: Right-aligned, mint bubble with attachment chips
 * - No Azure metadata visible - clean, natural feel
 */
export function AlphawaveMessageBubble({ message }: AlphawaveMessageBubbleProps) {
  /**
   * Formats the timestamp for display.
   */
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Clean the content to remove any metadata
  const cleanContent = cleanMessageContent(message.content);
  const hasAttachments = message.attachments && message.attachments.length > 0;

  // Nicole's response
  if (message.role === 'assistant') {
    return (
      <div className="flex justify-start animate-fade-in-up">
        <div className="max-w-xl lg:max-w-2xl">
          {/* Header with avatar and name */}
          <div className="flex items-center mb-2">
            <div className="w-8 h-8 rounded-full bg-lavender/20 flex items-center justify-center mr-2">
              <span className="text-lavender-text text-sm">N</span>
            </div>
            <span className="text-lavender-text font-serif font-medium">Nicole</span>
            <span className="mx-2 text-text-tertiary">•</span>
            <span className="text-xs text-text-tertiary">{formatTime(message.timestamp)}</span>
          </div>
          
          {/* Message content - elegant prose styling */}
          <div className="pl-10 text-text-primary nicole-message leading-relaxed prose prose-sm max-w-none">
            {message.content}
          </div>
          
          {/* Action buttons */}
          <div className="pl-10 mt-2">
            <AlphawaveMessageActions messageId={message.id} />
          </div>
        </div>
      </div>
    );
  }

  // User message - mint background bubble with attachment chips
  return (
    <div className="flex justify-end animate-fade-in-up">
      <div className={`max-w-md lg:max-w-lg rounded-2xl px-4 py-3 ${
        message.status === 'error' 
          ? 'bg-red-100 border border-red-200' 
          : 'bg-mint'
      }`}>
        {/* Header */}
        <div className="flex items-center justify-end mb-1">
          <span className="text-xs text-mint-dark mr-2">{formatTime(message.timestamp)}</span>
          <span className="text-mint-dark font-medium text-sm">You</span>
        </div>
        
        {/* Attachment chips - Claude style */}
        {hasAttachments && (
          <div className="flex flex-wrap gap-2 mb-2">
            {message.attachments!.map(attachment => (
              <AttachmentChip key={attachment.id} attachment={attachment} />
            ))}
          </div>
        )}
        
        {/* Message content - clean, no metadata */}
        {cleanContent && (
          <div className="text-text-primary">
            {cleanContent}
          </div>
        )}
        
        {/* Status indicator */}
        {message.status === 'sending' && (
          <div className="flex justify-end mt-1">
            <span className="text-xs text-mint-dark opacity-60">Sending...</span>
          </div>
        )}
        {message.status === 'error' && (
          <div className="flex justify-end mt-1">
            <span className="text-xs text-red-500">Failed to send</span>
          </div>
        )}
      </div>
    </div>
  );
}
