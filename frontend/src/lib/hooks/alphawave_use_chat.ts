/**
 * Custom hook for managing chat state and SSE streaming.
 * 
 * QA NOTES:
 * - Uses environment-based API URL from config
 * - Handles SSE streaming for real-time responses
 * - Includes error handling with user-friendly messages
 * - Supports conversation loading from history
 * - Claude-style attachments with invisible AI processing
 */

import { useState, useCallback, useEffect } from 'react';
import { supabase } from '@/lib/alphawave_supabase';
import { ENDPOINTS, REQUEST_CONFIG } from '@/lib/alphawave_config';
import type { FileAttachment } from '@/components/chat/AlphawaveChatInput';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
  attachments?: FileAttachment[];  // Claude-style file attachments
}

export interface UseChatOptions {
  conversationId?: string;
  onError?: (error: Error) => void;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  sendMessage: (content: string, attachments?: FileAttachment[]) => Promise<void>;
  isLoading: boolean;
  error: string | null;
  clearError: () => void;
  clearMessages: () => void;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const { conversationId, onError } = options;
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Load existing conversation history
   */
  const loadConversationHistory = useCallback(async (convId: string) => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const response = await fetch(ENDPOINTS.chat.history(convId), {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.messages) {
          setMessages(data.messages.map((m: { id: string; role: string; content: string; created_at: string }) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            timestamp: new Date(m.created_at),
            status: 'sent' as const,
          })));
        }
      }
    } catch (err) {
      console.error('Failed to load conversation history:', err);
    }
  }, []);

  useEffect(() => {
    if (conversationId) {
      loadConversationHistory(conversationId);
    }
  }, [conversationId, loadConversationHistory]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  /**
   * Sends a message to the backend with optional file attachments.
   * 
   * Claude-style flow:
   * - User sees clean message + attachment chips
   * - Document IDs sent to backend for context injection
   * - Azure analysis invisible to user - Nicole responds naturally
   */
  const sendMessage = useCallback(async (content: string, attachments?: FileAttachment[]) => {
    if (!content.trim() && (!attachments || attachments.length === 0)) return;
    
    setError(null);

    // Add user message with attachments (displayed as chips, not metadata)
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
      status: 'sending',
      attachments,  // Displayed as Claude-style chips
    };
    setMessages((prev) => [...prev, userMessage]);

    setIsLoading(true);

    try {
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session?.access_token) {
        throw new Error('Please log in to continue chatting');
      }

      setMessages((prev) => prev.map((m) => 
        m.id === userMessage.id ? { ...m, status: 'sent' as const } : m
      ));

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), REQUEST_CONFIG.timeout);

      // Extract document IDs for backend context injection
      // These are used internally - user never sees the Azure analysis
      const documentIds = attachments
        ?.filter(a => a.documentId)
        .map(a => a.documentId) || [];

      // SSE streaming request
      const response = await fetch(ENDPOINTS.chat.message, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: content,
          conversation_id: conversationId,
          // Send document IDs for invisible context injection
          document_ids: documentIds.length > 0 ? documentIds : undefined,
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Session expired. Please log in again.');
        } else if (response.status === 429) {
          throw new Error('Too many messages. Please wait a moment and try again.');
        } else if (response.status >= 500) {
          throw new Error('Nicole is having a moment. Please try again shortly.');
        } else {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || 'Something went wrong. Please try again.');
        }
      }

      if (!response.body) {
        throw new Error('No response received');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      const assistantMessageId = crypto.randomUUID();
      
      // Create empty assistant message for streaming
      setMessages((prev) => [...prev, {
        id: assistantMessageId,
        role: 'assistant' as const,
        content: '',
        timestamp: new Date(),
        status: 'sent' as const,
      }]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const jsonStr = line.slice(6).trim();
              if (!jsonStr) continue;
              
              const data = JSON.parse(jsonStr);

              if (data.type === 'token' || data.type === 'content') {
                const textContent = data.content || data.text || '';
                
                setMessages((prev) => 
                  prev.map((m) => 
                    m.id === assistantMessageId 
                      ? { ...m, content: m.content + textContent }
                      : m
                  )
                );
              } else if (data.type === 'error') {
                throw new Error(data.message || 'An error occurred during response');
              }
            } catch (parseError) {
              const trimmed = line.slice(6).trim();
              if (trimmed && trimmed !== '[DONE]') {
                console.warn('[SSE] Parse error:', trimmed);
              }
            }
          }
        }
      }
    } catch (err) {
      let errorMessage = 'Something went wrong. Please try again.';
      
      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          errorMessage = 'Request timed out. Please try again.';
        } else {
          errorMessage = err.message;
        }
      }

      setError(errorMessage);
      
      setMessages((prev) => prev.map((m) => 
        m.id === userMessage.id ? { ...m, status: 'error' as const } : m
      ));

      if (onError && err instanceof Error) {
        onError(err);
      }

      console.error('Chat error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, onError]);

  return { 
    messages, 
    sendMessage, 
    isLoading, 
    error, 
    clearError,
    clearMessages,
  };
}
