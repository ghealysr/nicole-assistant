'use client';

import { useState } from 'react';

/**
 * Props for AlphawaveChatInput.
 */
interface AlphawaveChatInputProps {
  onSendMessage: (content: string) => void;
  isLoading: boolean;
}

/**
 * Chat input component for Nicole V7.
 * Allows users to type and send messages.
 */
export function AlphawaveChatInput({ onSendMessage, isLoading }: AlphawaveChatInputProps) {
  const [content, setContent] = useState('');

  /**
   * Handles form submission to send the message.
   * @param e The form event.
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (content.trim() && !isLoading) {
      onSendMessage(content.trim());
      setContent('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 border-t border-border-line">
      <div className="flex space-x-2">
        <input
          type="text"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Type your message..."
          className="flex-1 rounded-lg border border-border-light px-4 py-3 text-text-primary bg-white focus:outline-none focus:ring-2 focus:ring-lavender"
          disabled={isLoading}
        />
        <button
          type="submit"
          className="px-4 py-3 bg-lavender text-white rounded-lg hover:bg-lavender-text focus:outline-none focus:ring-2 focus:ring-lavender disabled:opacity-50"
          disabled={!content.trim() || isLoading}
        >
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </form>
  );
}

