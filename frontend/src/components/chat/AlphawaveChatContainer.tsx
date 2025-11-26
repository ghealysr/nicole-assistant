'use client';

import { useState, useEffect } from 'react';
import { AlphawaveChatMessages } from './AlphawaveChatMessages';
import { AlphawaveChatInput } from './AlphawaveChatInput';
import { AlphawaveDashPanel } from './AlphawaveDashPanel';
import { useChat } from '@/lib/hooks/alphawave_use_chat';
import { useToast } from '@/components/ui/alphawave_toast';

/**
 * Typing indicator component - shows animated dots when Nicole is thinking
 */
function TypingIndicator() {
  return (
    <div className="flex items-center space-x-1 px-4 py-2">
      <div className="w-8 h-8 rounded-full bg-lavender/20 flex items-center justify-center mr-2">
        <span className="text-lavender-text text-sm">N</span>
      </div>
      <span className="text-lavender-text font-serif text-sm mr-2">Nicole is thinking</span>
      <div className="flex space-x-1">
        <div className="w-2 h-2 rounded-full bg-lavender typing-dot"></div>
        <div className="w-2 h-2 rounded-full bg-lavender typing-dot"></div>
        <div className="w-2 h-2 rounded-full bg-lavender typing-dot"></div>
      </div>
    </div>
  );
}

/**
 * Empty state component - shown when there are no messages
 */
function EmptyState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
      <div className="w-20 h-20 rounded-full bg-lavender/20 flex items-center justify-center mb-6">
        <span className="text-lavender-text text-3xl font-serif">N</span>
      </div>
      <h2 className="text-2xl font-serif text-lavender-text mb-3">
        Hello! I'm Nicole
      </h2>
      <p className="text-text-secondary max-w-md leading-relaxed">
        Your personal AI assistant. I'm here to help with anything you need —
        just type a message below to get started.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-2">
        {["What's on my calendar today?", "Help me plan my week", "Tell me a fun fact"].map((suggestion) => (
          <button
            key={suggestion}
            className="px-4 py-2 text-sm border border-border-light rounded-full text-text-secondary hover:bg-lavender/10 hover:text-lavender-text hover:border-lavender transition-colors"
          >
            {suggestion}
          </button>
        ))}
      </div>
    </div>
  );
}

/**
 * Main chat container component for Nicole V7.
 * 
 * QA NOTES:
 * - Chat area takes 60% width (40% if dashboard open)
 * - Integrates with useChat hook for message handling
 * - Shows toast notifications on errors
 * - Includes typing indicator during AI response
 * - Shows empty state for new conversations
 */
export function AlphawaveChatContainer() {
  const { showToast } = useToast();
  const { messages, sendMessage, isLoading, error, clearError } = useChat({
    onError: (err) => {
      showToast(err.message, 'error');
    },
  });
  const [dashOpen, setDashOpen] = useState(false);

  // Show toast when error state changes
  useEffect(() => {
    if (error) {
      showToast(error, 'error');
      clearError();
    }
  }, [error, showToast, clearError]);

  const hasMessages = messages.length > 0;

  return (
    <div className="flex h-full bg-cream">
      {/* Chat area */}
      <div className={`flex flex-col transition-all duration-300 ${dashOpen ? 'w-3/5' : 'w-full'}`}>
        {/* Messages area */}
        {hasMessages ? (
          <div className="flex-1 overflow-y-auto">
            <AlphawaveChatMessages messages={messages} />
            {isLoading && <TypingIndicator />}
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

      {/* Toggle dashboard button */}
      <button
        onClick={() => setDashOpen(!dashOpen)}
        className="fixed right-4 bottom-24 z-20 w-12 h-12 bg-lavender text-white rounded-full shadow-lg hover:bg-lavender-text transition-colors flex items-center justify-center"
        aria-label={dashOpen ? 'Close dashboard' : 'Open dashboard'}
      >
        <svg 
          className={`w-5 h-5 transition-transform ${dashOpen ? 'rotate-180' : ''}`} 
          fill="none" 
          viewBox="0 0 24 24" 
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19l-7-7 7-7m8 14l-7-7 7-7" />
        </svg>
      </button>

      {/* Dashboard panel - slides in from right */}
      <AlphawaveDashPanel isOpen={dashOpen} onClose={() => setDashOpen(false)} />
    </div>
  );
}
