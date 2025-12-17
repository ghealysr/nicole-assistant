/**
 * Custom hook for managing chat state and SSE streaming.
 * 
 * QA NOTES:
 * - Uses environment-based API URL from config
 * - Handles SSE streaming for real-time responses
 * - Includes error handling with user-friendly messages
 * - Supports conversation loading from history
 * - Claude-style attachments with invisible AI processing
 * - Uses Google OAuth for authentication
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { getStoredToken } from '@/lib/google_auth';
import { ENDPOINTS, REQUEST_CONFIG } from '@/lib/alphawave_config';
import type { FileAttachment } from '@/components/chat/AlphawaveChatInput';

export interface ThinkingStep {
  description: string;
  status: 'complete' | 'running' | 'pending';
  file?: string;
}

/**
 * Individual thinking step with full content
 */
export interface ThinkingContent {
  id: string;
  title: string;        // Short title for collapsed view
  content: string;      // Full thinking content
  status: 'running' | 'complete';
  timestamp: Date;
}

/**
 * Extended thinking state
 * 
 * Tracks Claude's extended thinking block:
 * - isThinking: actively receiving thinking content
 * - content: accumulated thinking text (streaming)
 * - isComplete: thinking phase has ended
 * - duration: how long thinking took (seconds)
 */
export interface ExtendedThinking {
  isThinking: boolean;
  content: string;
  isComplete: boolean;
  duration?: number;
}

/**
 * Tool use tracking
 */
export interface ToolUse {
  id: string;
  name: string;
  isActive: boolean;
  result?: string;
  success?: boolean;
}

/**
 * Activity status for real-time display
 */
export interface ActivityStatus {
  isActive: boolean;
  type: 'idle' | 'thinking' | 'tool' | 'responding';
  toolName?: string;
  displayText: string;
  thinkingSteps: ThinkingContent[];     // Completed steps (collapsible)
  currentThinking: string | null;        // Currently streaming thought
  shouldShow: boolean;                   // Master visibility control
  completedAt: number | null;            // Timestamp when processing completed
  
  // Extended thinking (Claude-style)
  extendedThinking: ExtendedThinking;
  
  // Tool uses (for transparency)
  toolUses: ToolUse[];
  
  // Memory notification (shows when Nicole remembers something)
  memoryNotification?: string;
}

/**
 * Map tool names to user-friendly display text
 */
function getToolDisplayText(toolName: string): string {
  const toolDisplayMap: Record<string, string> = {
    // Core tools
    'think': 'Reasoning through this...',
    'memory_search': 'Searching memories...',
    'memory_store': 'Saving to memory...',
    'document_search': 'Analyzing documents...',
    'search_tools': 'Finding the right tools...',
    'dashboard_status': 'Checking system status...',
    'skills_library': 'Checking skills...',
    
    // MCP tools
    'bravewebsearch': 'Searching the web...',
    'brave_web_search': 'Searching the web...',
    'recraftgenerateimage': 'Generating image...',
    'recraft_generate_image': 'Generating image...',
    
    // Notion tools
    'notion_search': 'Searching Notion...',
    'notion_get_page': 'Loading Notion page...',
    'notion_create_page': 'Creating Notion page...',
    'notion_update_page': 'Updating Notion page...',
    
    // File tools
    'readfile': 'Reading file...',
    'read_file': 'Reading file...',
    'listdirectory': 'Listing files...',
    'list_directory': 'Listing files...',
  };
  
  // Check for exact match first
  const lowerName = toolName.toLowerCase();
  if (toolDisplayMap[lowerName]) {
    return toolDisplayMap[lowerName];
  }
  
  // Check for partial matches
  if (lowerName.includes('notion')) return 'Loading Notion...';
  if (lowerName.includes('brave') || lowerName.includes('search')) return 'Searching the web...';
  if (lowerName.includes('memory')) return 'Accessing memories...';
  if (lowerName.includes('document')) return 'Analyzing documents...';
  if (lowerName.includes('file') || lowerName.includes('directory')) return 'Accessing files...';
  if (lowerName.includes('image') || lowerName.includes('recraft')) return 'Generating image...';
  if (lowerName.includes('skill')) return 'Using skill...';
  
  // Default: capitalize tool name
  return `Using ${toolName.replace(/_/g, ' ')}...`;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'error';
  attachments?: FileAttachment[];  // Claude-style file attachments
  thinkingSteps?: ThinkingStep[];  // Sequential thinking steps
  thinkingSummary?: string;        // Summary after thinking completes
}

export interface UseChatOptions {
  conversationId?: string;
  onError?: (error: Error) => void;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  sendMessage: (content: string, attachments?: FileAttachment[]) => Promise<void>;
  isLoading: boolean;
  isPendingAssistant: boolean;
  error: string | null;
  clearError: () => void;
  clearMessages: () => void;
  conversationId: number | null;
  setConversationId: (id: number | null) => void;
  activityStatus: ActivityStatus;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const { conversationId: initialConversationId, onError } = options;
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isPendingAssistant, setIsPendingAssistant] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<number | null>(
    initialConversationId ? parseInt(initialConversationId) : null
  );
  
  // Activity status for real-time display
  const [activityStatus, setActivityStatus] = useState<ActivityStatus>({
    isActive: false,
    type: 'idle',
    displayText: '',
    thinkingSteps: [],
    currentThinking: null,
    shouldShow: false,
    completedAt: null,
    extendedThinking: {
      isThinking: false,
      content: '',
      isComplete: false,
    },
    toolUses: [],
  });
  
  // Flag to prevent loading history when we just created a new conversation during streaming
  const isNewConversationRef = useRef(false);

  /**
   * Load existing conversation history
   */
  const loadConversationHistory = useCallback(async (convId: string) => {
    try {
      const token = getStoredToken();
      if (!token) return;

      const response = await fetch(ENDPOINTS.chat.history(convId), {
        headers: {
          'Authorization': `Bearer ${token}`,
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
    // Don't load history if:
    // 1. This is a new conversation we just created (ref is true)
    // 2. We already have messages in state (avoid overwriting streaming content)
    if (conversationId && !isNewConversationRef.current && messages.length === 0) {
      loadConversationHistory(String(conversationId));
    }
    // Reset the flag after the effect runs
    isNewConversationRef.current = false;
  }, [conversationId, loadConversationHistory, messages.length]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setIsPendingAssistant(false);
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
    setIsPendingAssistant(true);
    
    // Start activity status - clear previous thinking
    setActivityStatus({
      isActive: true,
      type: 'thinking',
      displayText: 'Processing...',
      thinkingSteps: [],
      currentThinking: null,
      shouldShow: true,
      completedAt: null,
      extendedThinking: {
        isThinking: false,
        content: '',
        isComplete: false,
      },
      toolUses: [],
    });

    try {
      const token = getStoredToken();
      
      if (!token) {
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
          'Authorization': `Bearer ${token}`,
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
        } else if (response.status === 403) {
          throw new Error('Access denied. Your account is not authorized.');
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

              if (data.type === 'start') {
                // Initial acknowledgment - keep thinking status
                setActivityStatus(prev => ({
                  ...prev,
                  isActive: true,
                  type: 'thinking',
                  displayText: 'Processing...',
                }));
              } else if (data.type === 'thinking_start') {
                // Extended thinking begins
                setActivityStatus(prev => ({
                  ...prev,
                  isActive: true,
                  type: 'thinking',
                  displayText: 'Thinking...',
                  shouldShow: true,
                  extendedThinking: {
                    isThinking: true,
                    content: '',
                    isComplete: false,
                  },
                }));
              } else if (data.type === 'thinking_delta') {
                // Streaming thinking content
                const thinkingContent = data.content || '';
                setActivityStatus(prev => ({
                  ...prev,
                  isActive: true,
                  type: 'thinking',
                  shouldShow: true,
                  extendedThinking: {
                    ...prev.extendedThinking,
                    isThinking: true,
                    content: prev.extendedThinking.content + thinkingContent,
                  },
                }));
              } else if (data.type === 'thinking_stop') {
                // Thinking complete - mark with duration
                const duration = data.duration || 0;
                setActivityStatus(prev => ({
                  ...prev,
                  type: 'thinking',
                  displayText: 'Responding...',
                  extendedThinking: {
                    ...prev.extendedThinking,
                    isThinking: false,
                    isComplete: true,
                    duration,
                  },
                }));
              } else if (data.type === 'status') {
                // Simple status update - just update display text
                const statusText = data.text || 'Processing...';
                setActivityStatus(prev => ({
                  ...prev,
                  isActive: true,
                  type: 'thinking',
                  displayText: statusText,
                }));
              } else if (data.type === 'tool_start') {
                // Tool execution started
                const toolName = data.tool_name || 'tool';
                const toolId = data.tool_id || crypto.randomUUID();
                setActivityStatus(prev => ({
                  ...prev,
                  isActive: true,
                  type: 'tool',
                  toolName,
                  displayText: getToolDisplayText(toolName),
                  // Add new tool use to tracking
                  toolUses: [
                    ...prev.toolUses.map(t => ({ ...t, isActive: false })),
                    { id: toolId, name: toolName, isActive: true }
                  ],
                }));
              } else if (data.type === 'tool_complete') {
                // Tool finished - update tool status
                const toolName = data.tool_name || '';
                const success = data.success !== false;
                setActivityStatus(prev => ({
                  ...prev,
                  isActive: true,
                  type: 'thinking',
                  displayText: 'Processing...',
                  // Mark the tool as complete
                  toolUses: prev.toolUses.map(t => 
                    t.name === toolName && t.isActive 
                      ? { ...t, isActive: false, success }
                      : t
                  ),
                }));
              } else if (data.type === 'thinking_step') {
                // Simple status update from thinking step
                const category = data.category || data.description || 'Thinking';
                setActivityStatus(prev => ({
                  ...prev,
                  isActive: true,
                  type: 'thinking',
                  displayText: category.includes('...') ? category : `${category}...`,
                }));
              } else if (data.type === 'thinking_complete') {
                // Thinking done - will transition to responding soon
                setActivityStatus(prev => ({
                  ...prev,
                  displayText: 'Responding...',
                }));
              } else if (data.type === 'token' || data.type === 'content') {
                const textContent = data.content || data.text || '';
                
                // First token - keep thinking block visible but mark as complete
                setActivityStatus(prev => {
                  // Skip if already responding (prevents re-triggering on each token)
                  if (prev.type === 'responding') return prev;
                  
                  return {
                    ...prev,
                    isActive: false,
                    type: 'responding',
                    displayText: '',
                    thinkingSteps: [],
                    currentThinking: null,
                    // Keep shouldShow true if we have thinking content to display
                    shouldShow: prev.extendedThinking.content.length > 0,
                    completedAt: Date.now(),
                    extendedThinking: {
                      ...prev.extendedThinking,
                      isThinking: false,
                      isComplete: true,
                    },
                  };
                });
                
                setMessages((prev) => 
                  prev.map((m) => 
                    m.id === assistantMessageId 
                      ? { ...m, content: m.content + textContent }
                      : m
                  )
                );
                // Yield to the browser to allow paint between token updates
                await new Promise((resolve) => setTimeout(resolve, 0));
              } else if (data.type === 'conversation_id' && data.conversation_id) {
                // Capture conversation ID from backend for new conversations
                // Set flag to prevent reloading history (we already have the messages in state)
                isNewConversationRef.current = true;
                setConversationId(data.conversation_id);
              } else if (data.type === 'memory_saved') {
                // Nicole remembered something
                const count = data.count || 1;
                setActivityStatus(prev => ({
                  ...prev,
                  memoryNotification: `✨ Nicole remembered ${count} thing${count > 1 ? 's' : ''}`,
                }));
                // Clear notification after 4 seconds
                setTimeout(() => {
                  setActivityStatus(prev => ({
                    ...prev,
                    memoryNotification: undefined,
                  }));
                }, 4000);
              } else if (data.type === 'error') {
                throw new Error(data.message || 'An error occurred during response');
              }
            } catch {
              const trimmed = line.slice(6).trim();
              if (trimmed && trimmed !== '[DONE]') {
                console.warn('[SSE] Parse error:', trimmed);
              }
            }
          }
        }
      }
      setIsPendingAssistant(false);
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
      setIsPendingAssistant(false);
      // Finalize activity status - keep thinking content for display
      setActivityStatus(prev => ({
        ...prev,
        isActive: false,
        type: 'idle',
        displayText: '',
        currentThinking: null,
        completedAt: prev.completedAt || Date.now(),
        // Keep thinking content visible (collapsed)
        extendedThinking: {
          ...prev.extendedThinking,
          isThinking: false,
          isComplete: true,
        },
      }));
    }
  }, [conversationId, onError]);

  return { 
    messages, 
    sendMessage, 
    isLoading, 
    isPendingAssistant,
    error, 
    clearError,
    clearMessages,
    conversationId,
    setConversationId,
    activityStatus,
  };
}
