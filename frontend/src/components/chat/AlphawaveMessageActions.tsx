'use client';

import { useState } from 'react';
import { useDebouncedCallback } from 'use-debounce';

/**
 * Props for AlphawaveMessageActions.
 */
interface AlphawaveMessageActionsProps {
  messageId: string;
}

/**
 * Message actions component for Nicole V7.
 * Provides thumbs up/down feedback and copy functionality with 300ms debouncing.
 */
export function AlphawaveMessageActions({ messageId }: AlphawaveMessageActionsProps) {
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);

  // 300ms debounce to prevent double-clicks
  const handleFeedback = useDebouncedCallback(
    async (type: 'up' | 'down') => {
      setFeedback(type);
      await fetch('/api/feedback', {
        method: 'POST',
        body: JSON.stringify({ messageId, type }),
      });
    },
    300
  );

  /**
   * Copies the message content to the clipboard.
   */
  const handleCopy = async () => {
    const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
    if (messageElement) {
      await navigator.clipboard.writeText(messageElement.textContent || '');
    }
  };

  return (
    <div className="flex space-x-2 mt-2">
      <button
        onClick={() => handleFeedback('up')}
        className={`rounded p-1 hover:bg-light-gray ${
          feedback === 'up' ? 'text-lavender' : 'text-text-tertiary'
        }`}
        aria-label="Thumbs up"
      >
        👍
      </button>

      <button
        onClick={() => handleFeedback('down')}
        className={`rounded p-1 hover:bg-light-gray ${
          feedback === 'down' ? 'text-lavender' : 'text-text-tertiary'
        }`}
        aria-label="Thumbs down"
      >
        👎
      </button>

      <button
        onClick={handleCopy}
        className="rounded p-1 hover:bg-light-gray text-text-tertiary"
        aria-label="Copy message"
      >
        📋
      </button>
    </div>
  );
}

