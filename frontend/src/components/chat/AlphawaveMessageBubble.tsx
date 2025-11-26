'use client';

import { AlphawaveMessageActions } from './AlphawaveMessageActions';

/**
 * Interface for message objects.
 */
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
}

/**
 * Props for AlphawaveMessageBubble.
 */
interface AlphawaveMessageBubbleProps {
  message: Message;
}

/**
 * Message bubble component for Nicole V7.
 * 
 * Design:
 * - Nicole's messages: Left-aligned, no background, elegant serif font
 * - User messages: Right-aligned, mint background bubble
 * - Smooth fade-in animation on new messages
 */
export function AlphawaveMessageBubble({ message }: AlphawaveMessageBubbleProps) {
  /**
   * Formats the timestamp for display.
   */
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

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
          
          {/* Message content - elegant serif styling */}
          <div className="pl-10 text-text-primary nicole-message leading-relaxed">
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

  // User message - mint background bubble
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
        
        {/* Message content */}
        <div className="text-text-primary">
          {message.content}
        </div>
        
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
