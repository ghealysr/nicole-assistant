'use client';

import { AlphawaveChatContainer } from '@/components/chat/AlphawaveChatContainer';

/**
 * Chat page component for Nicole V7.
 * 
 * QA NOTES:
 * - Main chat interface
 * - Full height container with message area and input
 * - Supports dashboard panel toggle
 */
export default function ChatPage() {
  return (
    <div className="h-full">
      <AlphawaveChatContainer />
    </div>
  );
}

