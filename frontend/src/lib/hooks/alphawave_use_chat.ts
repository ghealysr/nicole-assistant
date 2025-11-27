/**
 * Custom hook for managing chat state and SSE streaming.
 * 
 * QA NOTES:
 * - Uses environment-based API URL from config
 * - Handles SSE streaming for real-time responses
 * - Includes error handling with user-friendly messages
 * - Supports conversation loading from history
 */

import { useState, useCallback, useEffect } from 'react';
import { supabase } from '@/lib/alphawave_supabase';
import { ENDPOINTS, REQUEST_CONFIG } from '@/lib/alphawave_config';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
}

export interface UseChatOptions {
  conversationId?: string;
  onError?: (error: Error) => void;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  sendMessage: (content: string) => Promise<void>;
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
      // Don't set error state - this is a non-critical failure
    }
  }, []);

  // Load conversation history on mount if conversationId provided
  useEffect(() => {
    if (conversationId) {
      loadConversationHistory(conversationId);
    }
  }, [conversationId, loadConversationHistory]);

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  /**
   * Clear all messages
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  /**
   * Sends a message to the backend and streams the response.
   */
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return;
    
    // Clear any previous error
    setError(null);

    // Add user message immediately with sending status
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
      status: 'sending',
    };
    setMessages((prev) => [...prev, userMessage]);

    setIsLoading(true);

    try {
      // Get JWT token
      const { data: { session } } = await supabase.auth.getSession();
      
      if (!session?.access_token) {
        throw new Error('Please log in to continue chatting');
      }

      // Update user message to sent
      setMessages((prev) => prev.map((m) => 
        m.id === userMessage.id ? { ...m, status: 'sent' as const } : m
      ));

      // Create AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), REQUEST_CONFIG.timeout);

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
        }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle non-OK responses
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

      // Check for streaming response
      if (!response.body) {
        throw new Error('No response received');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      const assistantMessageId = crypto.randomUUID();
      let assistantCreated = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'token' || data.type === 'content') {
                const textContent = data.content || data.text || '';
                setMessages((prev) => {
                  if (!assistantCreated) {
                    assistantCreated = true;
                    return [...prev, {
                      id: assistantMessageId,
                      role: 'assistant' as const,
                      content: textContent,
                      timestamp: new Date(),
                      status: 'sent' as const,
                    }];
                  } else {
                    return prev.map((m) => 
                      m.id === assistantMessageId 
                        ? { ...m, content: m.content + textContent }
                        : m
                    );
                  }
                });
              } else if (data.type === 'error') {
                throw new Error(data.message || 'An error occurred during response');
              } else if (data.type === 'done') {
                // Stream complete
                console.log('Stream complete:', data.message_id);
              }
            } catch {
              // Skip invalid JSON lines (could be keep-alive or empty lines)
              if (line.slice(6).trim() && line.slice(6) !== '[DONE]') {
                console.warn('Failed to parse SSE data:', line);
              }
            }
          }
        }
      }
    } catch (err) {
      // Handle different error types
      let errorMessage = 'Something went wrong. Please try again.';
      
      if (err instanceof Error) {
        if (err.name === 'AbortError') {
          errorMessage = 'Request timed out. Please try again.';
        } else {
          errorMessage = err.message;
        }
      }

      setError(errorMessage);
      
      // Mark user message as error
      setMessages((prev) => prev.map((m) => 
        m.id === userMessage.id ? { ...m, status: 'error' as const } : m
      ));

      // Call onError callback if provided
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
