import { useFazStore } from './store';
import { API_URL } from '@/lib/alphawave_config';

class FazWebSocket {
  private ws: WebSocket | null = null;
  private projectId: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectTimer: NodeJS.Timeout | null = null;

  connect(projectId: number) {
    if (this.ws && this.projectId === projectId) return;
    
    this.disconnect();
    this.projectId = projectId;
    
    // Construct WS URL (handle https -> wss)
    const wsUrl = API_URL.replace('http', 'ws') + `/faz/projects/${projectId}/ws`;
    
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      console.log('[Faz WS] Connected');
      this.reconnectAttempts = 0;
      // Send ping immediately
      this.send({ type: 'ping' });
    };
    
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleMessage(data);
      } catch (e) {
        console.error('[Faz WS] Failed to parse message:', e);
      }
    };
    
    this.ws.onclose = () => {
      console.log('[Faz WS] Disconnected');
      this.handleReconnect();
    };
    
    this.ws.onerror = (error) => {
      console.error('[Faz WS] Error:', error);
    };
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.projectId = null;
  }
  
  send(message: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.warn('[Faz WS] Not connected, cannot send:', message);
    }
  }
  
  private handleMessage(data: any) {
    const store = useFazStore.getState();
    
    switch (data.type) {
      case 'activity':
        store.addActivity(data);
        break;
        
      case 'chat':
        store.addMessage({
          message_id: data.message_id,
          role: data.role,
          content: data.content,
          agent_name: data.agent,
          created_at: data.timestamp
        });
        break;
        
      case 'status':
        if (store.currentProject) {
          store.setCurrentProject({
            ...store.currentProject,
            status: data.status,
            current_agent: data.current_agent
          });
        }
        break;
        
      case 'complete':
        if (store.currentProject) {
          store.setCurrentProject({
            ...store.currentProject,
            status: data.status,
            file_count: data.file_count,
            total_tokens_used: data.total_tokens,
            total_cost_cents: data.total_cost_cents
          });
        }
        break;
        
      case 'file':
        // Handle file updates if we implement live file streaming
        break;
        
      case 'error':
        console.error('[Faz WS] Server error:', data.message);
        break;
        
      case 'pong':
        // Keep-alive response
        break;
    }
  }
  
  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts && this.projectId) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
      
      console.log(`[Faz WS] Reconnecting in ${delay}ms...`);
      
      this.reconnectTimer = setTimeout(() => {
        if (this.projectId) {
          this.connect(this.projectId);
        }
      }, delay);
    }
  }
}

export const fazWS = new FazWebSocket();

