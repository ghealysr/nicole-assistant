'use client';

import { useState, useEffect } from 'react';
import { AlphawaveChatMessages } from './AlphawaveChatMessages';
import { AlphawaveChatInput } from './AlphawaveChatInput';
import { AlphawaveDashPanel } from './AlphawaveDashPanel';
import { useChat } from '@/lib/hooks/alphawave_use_chat';
import { useToast } from '@/components/ui/alphawave_toast';

/**
 * Main chat container component for Nicole V7.
 * 
 * QA NOTES:
 * - Chat area takes 60% width (40% if dashboard open)
 * - Integrates with useChat hook for message handling
 * - Shows toast notifications on errors
 * - Supports dashboard panel toggle
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

  return (
    <div className="flex h-full">
      {/* Chat area: 60% width (or 40% if dash open) */}
      <div className={`bg-cream ${dashOpen ? 'w-2/5' : 'w-3/5'} flex flex-col`}>
        <AlphawaveChatMessages messages={messages} />
        <AlphawaveChatInput 
          onSendMessage={sendMessage} 
          isLoading={isLoading} 
        />
      </div>

      {/* Toggle dashboard button */}
      <button
        onClick={() => setDashOpen(!dashOpen)}
        className="absolute right-4 top-24 z-10 p-2 bg-sage text-white rounded-full shadow-lg hover:bg-terracotta transition-colors"
        aria-label={dashOpen ? 'Close dashboard' : 'Open dashboard'}
      >
        {dashOpen ? '→' : '←'}
      </button>

      {/* Dashboard: 40% slide-in from right */}
      <AlphawaveDashPanel isOpen={dashOpen} onClose={() => setDashOpen(false)} />
    </div>
  );
}
