/**
 * Faz Code WebSocket Client
 * 
 * Handles real-time communication with the backend for:
 * - Agent activity updates
 * - Chat messages
 * - Project status changes
 * - File generation events
 * 
 * Includes authentication via query parameter token.
 */

import { useFazStore } from './store';
import { API_URL } from '@/lib/alphawave_config';
import { getAuthToken } from '@/lib/alphawave_utils';
import type { FazActivity } from '@/types/faz';

interface WebSocketMessage {
  type: string;
  [key: string]: unknown;
}

type ActivityContentType = FazActivity['content_type'];
type ActivityStatus = FazActivity['status'];

function normalizeContentType(value: unknown): ActivityContentType {
  switch (value) {
    case 'status':
    case 'thinking':
    case 'response':
    case 'tool_call':
    case 'error':
      return value;
    default:
      return 'status';
  }
}

function normalizeActivityStatus(value: unknown): ActivityStatus {
  switch (value) {
    case 'running':
    case 'complete':
    case 'error':
    case 'cancelled':
      return value;
    default:
      return 'complete';
  }
}

function toNumber(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const n = Number(value);
    if (Number.isFinite(n)) return n;
  }
  return fallback;
}

class FazWebSocket {
  private ws: WebSocket | null = null;
  private projectId: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private pingInterval: NodeJS.Timeout | null = null;
  private authenticated = false;
  
  /**
   * Connect to WebSocket for a specific project
   */
  connect(projectId: number) {
    if (this.ws && this.projectId === projectId && this.ws.readyState === WebSocket.OPEN) {
      return; // Already connected to this project
    }
    
    this.disconnect();
    this.projectId = projectId;
    
    // Get authentication token
    const token = getAuthToken();
    
    if (!token) {
      console.error('[Faz WS] No auth token available');
      // Redirect to login
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      return;
    }
    
    // Construct WS URL with token (handle https -> wss)
    const wsBase = API_URL.replace('http', 'ws');
    const wsUrl = `${wsBase}/faz/projects/${projectId}/ws?token=${encodeURIComponent(token)}`;
    
    try {
      this.ws = new WebSocket(wsUrl);
    } catch (error) {
      console.error('[Faz WS] Failed to create WebSocket:', error);
      return;
    }
    
    this.ws.onopen = () => {
      console.log('[Faz WS] Connected to project', projectId);
      this.reconnectAttempts = 0;
      this.authenticated = false;
      
      // Start ping interval to keep connection alive
      this.startPingInterval();
    };
    
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (e) {
        console.error('[Faz WS] Failed to parse message:', e);
      }
    };
    
    this.ws.onclose = (event) => {
      console.log('[Faz WS] Disconnected', event.code, event.reason);
      this.stopPingInterval();
      this.authenticated = false;
      
      // Handle specific close codes
      if (event.code === 4001) {
        // Authentication required - redirect to login
        console.error('[Faz WS] Authentication failed');
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return;
      }
      
      if (event.code === 4003) {
        // Access denied - don't reconnect
        console.error('[Faz WS] Access denied to project');
        return;
      }
      
      // Attempt reconnect for other disconnections
      this.handleReconnect();
    };
    
    this.ws.onerror = (error) => {
      console.error('[Faz WS] Error:', error);
    };
  }
  
  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    this.stopPingInterval();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    this.projectId = null;
    this.authenticated = false;
  }
  
  /**
   * Send message to server
   */
  send(message: WebSocketMessage) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('[Faz WS] Not connected, cannot send:', message);
    }
  }
  
  /**
   * Send chat message
   */
  sendChat(message: string) {
    this.send({ type: 'chat', message });
  }
  
  /**
   * Run pipeline
   */
  runPipeline(startAgent: string = 'nicole') {
    this.send({ type: 'run', start_agent: startAgent });
  }
  
  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
  
  /**
   * Check if authenticated
   */
  isAuthenticated(): boolean {
    return this.authenticated;
  }
  
  /**
   * Handle incoming message
   */
  private handleMessage(data: WebSocketMessage) {
    const store = useFazStore.getState();
    
    switch (data.type) {
      case 'auth':
        // Authentication confirmation
        this.authenticated = data.authenticated as boolean;
        console.log('[Faz WS] Authenticated:', data.user);
        break;
        
      case 'activity':
        store.addActivity({
          activity_id: data.activity_id as number,
          agent_name: data.agent as string,
          agent_model: data.model as string,
          activity_type: data.activity_type as string,
          message: data.message as string,
          content_type: normalizeContentType(data.content_type),
          // FazActivity.full_content is optional (undefined), so normalize null -> undefined
          full_content: ((data.full_content as string | null) ?? undefined),
          status: normalizeActivityStatus(data.status),
          started_at: data.timestamp as string,
          input_tokens: toNumber((data as { input_tokens?: unknown }).input_tokens, 0),
          output_tokens: toNumber((data as { output_tokens?: unknown }).output_tokens, 0),
          cost_cents: toNumber((data as { cost_cents?: unknown }).cost_cents, 0),
        });
        break;
        
      case 'chat':
        store.addMessage({
          message_id: data.message_id as number,
          role: data.role as string,
          content: data.content as string,
          agent_name: data.agent as string | undefined,
          created_at: data.timestamp as string,
        });
        break;
        
      case 'status':
        if (store.currentProject) {
          store.setCurrentProject({
            ...store.currentProject,
            status: data.status as string,
            current_agent: data.current_agent as string | null,
          });
        }
        break;
        
      case 'complete':
        if (store.currentProject) {
          store.setCurrentProject({
            ...store.currentProject,
            status: data.status as string,
            file_count: data.file_count as number,
            total_tokens_used: data.total_tokens as number,
            total_cost_cents: data.total_cost_cents as number,
          });
        }
        // Clear loading state
        store.setLoading(false);
        break;
        
      case 'file':
        // Handle file updates for live preview
        if (data.path && data.content) {
          store.addFile({
            file_id: data.file_id as number,
            path: data.path as string,
            filename: (data.path as string).split('/').pop() || '',
            content: data.content as string,
            extension: (data.path as string).split('.').pop() || '',
            file_type: data.file_type as string,
            line_count: (data.content as string).split('\n').length,
            generated_by: data.agent as string,
            version: 1,
            status: 'generated',
            created_at: data.timestamp as string,
          });
        }
        break;
        
      case 'routing':
        // Agent routing decision
        console.log('[Faz WS] Routing to:', data.next_agent, 'Intent:', data.intent);
        break;
        
      case 'error':
        console.error('[Faz WS] Server error:', data.message);
        store.setError(data.message as string);
        break;
        
      case 'pong':
        // Keep-alive response
        break;
        
      default:
        console.log('[Faz WS] Unknown message type:', data.type);
    }
  }
  
  /**
   * Start ping interval for keep-alive
   */
  private startPingInterval() {
    this.stopPingInterval();
    this.pingInterval = setInterval(() => {
      this.send({ type: 'ping' });
    }, 30000); // Ping every 30 seconds
  }
  
  /**
   * Stop ping interval
   */
  private stopPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
  
  /**
   * Handle reconnection with exponential backoff
   */
  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts && this.projectId) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
      
      console.log(`[Faz WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
      
      this.reconnectTimer = setTimeout(() => {
        if (this.projectId) {
          this.connect(this.projectId);
        }
      }, delay);
    } else {
      console.log('[Faz WS] Max reconnection attempts reached');
    }
  }
}

// Export singleton instance
export const fazWS = new FazWebSocket();
