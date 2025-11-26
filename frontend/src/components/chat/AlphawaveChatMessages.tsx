'use client';

import { useEffect, useRef } from 'react';
import { AlphawaveMessageBubble } from './AlphawaveMessageBubble';

/**
 * Interface for message objects.
 */
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

/**
 * Props for AlphawaveChatMessages.
 */
interface AlphawaveChatMessagesProps {
  messages: Message[];
}

/**
 * Chat messages component for Nicole V7.
 * Displays messages with auto-scroll to bottom.
 */
export function AlphawaveChatMessages({ messages }: AlphawaveChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  /**
   * Scrolls to the bottom of the messages when new messages are added.
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((message) => (
        <AlphawaveMessageBubble key={message.id} message={message} />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
}

