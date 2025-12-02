'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { supabase } from '@/lib/alphawave_supabase';
import { ENDPOINTS } from '@/lib/alphawave_config';

/**
 * Conversation data structure from backend
 */
interface Conversation {
  conversation_id: number;
  title: string;
  message_count: number;
  last_message_at: string;
  created_at: string;
  is_pinned: boolean;
  pin_order: number | null;
}

interface AlphawaveChatsPanelProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectConversation: (conversationId: number) => void;
  onNewChat: () => void;
  currentConversationId?: number | null;
}

/**
 * Format relative time for conversation timestamps
 */
function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Format title to be professional (Title Case)
 */
function formatTitle(title: string): string {
  if (!title) return 'New Conversation';
  
  // Clean up the title
  let cleaned = title.trim();
  
  // If it looks like a message snippet, truncate nicely
  if (cleaned.length > 50) {
    cleaned = cleaned.slice(0, 47) + '...';
  }
  
  // Convert to Title Case (capitalize first letter of each word)
  // But preserve common acronyms and handle edge cases
  const titleCased = cleaned
    .split(' ')
    .map(word => {
      // Skip if it's an acronym (all caps) or already properly cased
      if (word === word.toUpperCase() && word.length <= 4) return word;
      // Skip URLs or paths
      if (word.includes('/') || word.includes('.')) return word;
      // Capitalize first letter
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    })
    .join(' ');
  
  return titleCased;
}

/**
 * Nicole V7 Chats Panel - Memory Dashboard Style
 * 
 * Features:
 * - Resizable panel (400px - 800px)
 * - Pinned conversations at top (max 5)
 * - Drag-and-drop to reorder pinned chats
 * - Delete conversations
 * - Draft indicator for short conversations
 * - Search functionality
 * - Matches Memory Dashboard design language
 */
export function AlphawaveChatsPanel({
  isOpen,
  onClose,
  onSelectConversation,
  onNewChat,
  currentConversationId,
}: AlphawaveChatsPanelProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [draggedId, setDraggedId] = useState<number | null>(null);
  const [dropTargetId, setDropTargetId] = useState<number | null>(null);
  const [dashboardWidth, setDashboardWidth] = useState(520);
  const [isResizing, setIsResizing] = useState(false);
  
  const resizeRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(520);

  const MIN_WIDTH = 400;
  const MAX_WIDTH = 800;

  // Resize handlers
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    startXRef.current = e.clientX;
    startWidthRef.current = dashboardWidth;
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'ew-resize';
  }, [dashboardWidth]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return;
      const diff = startXRef.current - e.clientX;
      const newWidth = Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, startWidthRef.current + diff));
      setDashboardWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  /**
   * Fetch conversations from backend
   */
  const fetchConversations = useCallback(async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      const response = await fetch(`${ENDPOINTS.chat.conversations}?limit=30`, {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setConversations(data.conversations || []);
      }
    } catch (err) {
      console.error('Failed to fetch conversations:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchConversations();
    }
  }, [isOpen, fetchConversations]);

  /**
   * Handle selecting a conversation
   */
  const handleSelectConversation = useCallback((conversationId: number) => {
    onSelectConversation(conversationId);
    onClose();
  }, [onSelectConversation, onClose]);

  /**
   * Pin/unpin a conversation
   */
  const handlePin = async (e: React.MouseEvent, conversationId: number) => {
    e.stopPropagation();
    const conv = conversations.find(c => c.conversation_id === conversationId);
    if (!conv) return;

    // Check pin limit
    const pinnedCount = conversations.filter(c => c.is_pinned).length;
    if (!conv.is_pinned && pinnedCount >= 5) {
      alert('You can only pin up to 5 conversations');
      return;
    }

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      await fetch(`${ENDPOINTS.chat.conversations}/${conversationId}/pin`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_pinned: !conv.is_pinned }),
      });

      // Optimistic update
      setConversations(prev => prev.map(c => 
        c.conversation_id === conversationId 
          ? { ...c, is_pinned: !c.is_pinned, pin_order: !c.is_pinned ? pinnedCount : null }
          : c
      ));
    } catch (err) {
      console.error('Failed to pin conversation:', err);
    }
  };

  /**
   * Delete a conversation
   */
  const handleDelete = async (e: React.MouseEvent, conversationId: number) => {
    e.stopPropagation();
    if (!confirm('Delete this conversation? This cannot be undone.')) return;

    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session?.access_token) return;

      await fetch(`${ENDPOINTS.chat.conversations}/${conversationId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      // Optimistic update
      setConversations(prev => prev.filter(c => c.conversation_id !== conversationId));
      
      // If deleted current conversation, start new chat
      if (conversationId === currentConversationId) {
        onNewChat();
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  };

  /**
   * Drag and drop handlers for pinned conversations
   */
  const handleDragStart = (e: React.DragEvent, conversationId: number) => {
    setDraggedId(conversationId);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent, conversationId: number) => {
    e.preventDefault();
    if (draggedId && draggedId !== conversationId) {
      const targetConv = conversations.find(c => c.conversation_id === conversationId);
      if (targetConv?.is_pinned) {
        setDropTargetId(conversationId);
      }
    }
  };

  const handleDrop = async (e: React.DragEvent, targetId: number) => {
    e.preventDefault();
    if (!draggedId || draggedId === targetId) {
      setDraggedId(null);
      setDropTargetId(null);
      return;
    }

    // Reorder pinned conversations locally
    const pinnedConvs = conversations.filter(c => c.is_pinned);
    const draggedIndex = pinnedConvs.findIndex(c => c.conversation_id === draggedId);
    const targetIndex = pinnedConvs.findIndex(c => c.conversation_id === targetId);

    if (draggedIndex !== -1 && targetIndex !== -1) {
      const newPinned = [...pinnedConvs];
      const [removed] = newPinned.splice(draggedIndex, 1);
      newPinned.splice(targetIndex, 0, removed);

      // Update pin orders
      const updatedConvs = conversations.map(c => {
        const pinnedIndex = newPinned.findIndex(p => p.conversation_id === c.conversation_id);
        if (pinnedIndex !== -1) {
          return { ...c, pin_order: pinnedIndex };
        }
        return c;
      });

      setConversations(updatedConvs);

      // Sync to backend
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (session?.access_token) {
          await fetch(`${ENDPOINTS.chat.conversations}/reorder-pins`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${session.access_token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              order: newPinned.map((c, i) => ({ conversation_id: c.conversation_id, pin_order: i })),
            }),
          });
        }
      } catch (err) {
        console.error('Failed to reorder pins:', err);
      }
    }

    setDraggedId(null);
    setDropTargetId(null);
  };

  // Filter conversations by search
  const filteredConversations = searchQuery
    ? conversations.filter(c => 
        c.title?.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : conversations;

  // Separate pinned and unpinned
  const pinnedConvs = filteredConversations
    .filter(c => c.is_pinned)
    .sort((a, b) => (a.pin_order ?? 0) - (b.pin_order ?? 0));
  
  const recentConvs = filteredConversations
    .filter(c => !c.is_pinned)
    .sort((a, b) => 
      new Date(b.last_message_at || b.created_at).getTime() - 
      new Date(a.last_message_at || a.created_at).getTime()
    );

  // Stats
  const totalConversations = conversations.length;
  const pinnedCount = conversations.filter(c => c.is_pinned).length;
  const totalMessages = conversations.reduce((sum, c) => sum + (c.message_count || 0), 0);
  const draftCount = conversations.filter(c => (c.message_count || 0) <= 3).length;

  return (
    <aside 
      className={`mem-dashboard-panel ${isOpen ? 'mem-open' : ''}`}
      style={{ '--mem-dashboard-width': `${dashboardWidth}px` } as React.CSSProperties}
    >
      {/* Resize Handle */}
      <div 
        ref={resizeRef}
        className={`mem-resize-handle ${isResizing ? 'mem-dragging' : ''}`}
        onMouseDown={handleMouseDown}
      />

      <div className="mem-dashboard-inner">
        {/* Header */}
        <div className="mem-dash-header">
          <div className="mem-dash-header-left">
            <div className="mem-dash-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <span className="mem-dash-title">Conversations</span>
          </div>
          <button className="mem-dash-close-btn" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* New Chat Button */}
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #333' }}>
          <button
            onClick={() => { onNewChat(); onClose(); }}
            className="mem-filter-pill mem-active"
            style={{ 
              width: '100%', 
              padding: '10px 16px', 
              justifyContent: 'center',
              gap: '8px',
              fontSize: '13px',
              fontWeight: 600,
            }}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} style={{ width: '16px', height: '16px' }}>
              <path d="M12 5v14M5 12h14"/>
            </svg>
            New Conversation
          </button>
        </div>

        {/* Content */}
        <div className="mem-dash-content">
          <div className="mem-tab-panel">
            {/* Stats Widget */}
            <div className="mem-widget">
              <div className="mem-widget-header">
                <span className="mem-widget-title">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                  Chat Statistics
                </span>
              </div>
              <div className="mem-stat-grid mem-stat-grid-4">
                <div className="mem-stat-box">
                  <div className="mem-stat-value mem-small mem-highlight">{totalConversations}</div>
                  <div className="mem-stat-label">Total</div>
                </div>
                <div className="mem-stat-box">
                  <div className="mem-stat-value mem-small">{pinnedCount}</div>
                  <div className="mem-stat-label">Pinned</div>
                </div>
                <div className="mem-stat-box">
                  <div className="mem-stat-value mem-small">{totalMessages}</div>
                  <div className="mem-stat-label">Messages</div>
                </div>
                <div className="mem-stat-box">
                  <div className="mem-stat-value mem-small">{draftCount}</div>
                  <div className="mem-stat-label">Drafts</div>
                </div>
              </div>
            </div>

            {/* Search */}
            <div className="mem-search-input-wrapper">
              <svg className="mem-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <input 
                type="text" 
                className="mem-search-input" 
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {isLoading ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: '40px 0' }}>
                <div style={{ 
                  width: '32px', 
                  height: '32px', 
                  border: '2px solid #B8A8D4', 
                  borderTopColor: 'transparent', 
                  borderRadius: '50%', 
                  animation: 'spin 1s linear infinite' 
                }} />
              </div>
            ) : (
              <>
                {/* Pinned Section */}
                {pinnedConvs.length > 0 && (
                  <div className="mem-widget">
                    <div className="mem-widget-header">
                      <span className="mem-widget-title">
                        <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4" style={{ color: '#B8A8D4' }}>
                          <path d="M12 2L12 12"/>
                          <path d="M18.5 12.5L18.5 8.5L5.5 8.5L5.5 12.5L8 15L8 22L16 22L16 15L18.5 12.5Z"/>
                        </svg>
                        Pinned ({pinnedConvs.length}/5)
                      </span>
                    </div>
                    <div className="mem-chat-history-list">
                      {pinnedConvs.map(conv => (
                        <div 
                          key={conv.conversation_id}
                          draggable
                          onDragStart={(e) => handleDragStart(e, conv.conversation_id)}
                          onDragOver={(e) => handleDragOver(e, conv.conversation_id)}
                          onDrop={(e) => handleDrop(e, conv.conversation_id)}
                          onClick={() => handleSelectConversation(conv.conversation_id)}
                          className={`mem-chat-item ${conv.conversation_id === currentConversationId ? 'mem-active' : ''} ${draggedId === conv.conversation_id ? 'mem-dragging' : ''} ${dropTargetId === conv.conversation_id ? 'mem-drop-target' : ''}`}
                          style={{ 
                            cursor: 'pointer',
                            borderLeft: '3px solid #B8A8D4',
                            opacity: draggedId === conv.conversation_id ? 0.5 : 1,
                            border: dropTargetId === conv.conversation_id ? '1px dashed #B8A8D4' : undefined,
                          }}
                        >
                          <div className="mem-chat-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {formatTitle(conv.title)}
                            {(conv.message_count || 0) <= 3 && (
                              <span style={{ 
                                fontSize: '10px', 
                                padding: '2px 6px', 
                                background: '#333', 
                                borderRadius: '4px',
                                color: '#9ca3af'
                              }}>
                                Draft
                              </span>
                            )}
                          </div>
                          <div className="mem-chat-meta" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>{conv.message_count || 0} messages • {formatRelativeTime(conv.last_message_at || conv.created_at)}</span>
                            <div style={{ display: 'flex', gap: '4px' }}>
                              <button 
                                onClick={(e) => handlePin(e, conv.conversation_id)}
                                style={{ 
                                  padding: '4px', 
                                  background: 'transparent', 
                                  border: 'none', 
                                  cursor: 'pointer',
                                  color: '#B8A8D4',
                                  borderRadius: '4px',
                                }}
                                title="Unpin"
                              >
                                <svg viewBox="0 0 24 24" fill="currentColor" style={{ width: '14px', height: '14px' }}>
                                  <path d="M12 2L12 12"/>
                                  <path d="M18.5 12.5L18.5 8.5L5.5 8.5L5.5 12.5L8 15L8 22L16 22L16 15L18.5 12.5Z"/>
                                </svg>
                              </button>
                              <button 
                                onClick={(e) => handleDelete(e, conv.conversation_id)}
                                style={{ 
                                  padding: '4px', 
                                  background: 'transparent', 
                                  border: 'none', 
                                  cursor: 'pointer',
                                  color: '#6b7280',
                                  borderRadius: '4px',
                                }}
                                title="Delete"
                              >
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} style={{ width: '14px', height: '14px' }}>
                                  <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                                </svg>
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recent Section */}
                <div className="mem-widget">
                  <div className="mem-widget-header">
                    <span className="mem-widget-title">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M12 6v6l4 2"/>
                      </svg>
                      Recent Conversations
                    </span>
                  </div>
                  {recentConvs.length > 0 ? (
                    <div className="mem-chat-history-list">
                      {recentConvs.map(conv => (
                        <div 
                          key={conv.conversation_id}
                          onClick={() => handleSelectConversation(conv.conversation_id)}
                          className={`mem-chat-item ${conv.conversation_id === currentConversationId ? 'mem-active' : ''}`}
                          style={{ cursor: 'pointer' }}
                        >
                          <div className="mem-chat-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {formatTitle(conv.title)}
                            {(conv.message_count || 0) <= 3 && (
                              <span style={{ 
                                fontSize: '10px', 
                                padding: '2px 6px', 
                                background: '#333', 
                                borderRadius: '4px',
                                color: '#9ca3af'
                              }}>
                                Draft
                              </span>
                            )}
                          </div>
                          <div className="mem-chat-meta" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span>{conv.message_count || 0} messages • {formatRelativeTime(conv.last_message_at || conv.created_at)}</span>
                            <div style={{ display: 'flex', gap: '4px' }}>
                              <button 
                                onClick={(e) => handlePin(e, conv.conversation_id)}
                                style={{ 
                                  padding: '4px', 
                                  background: 'transparent', 
                                  border: 'none', 
                                  cursor: 'pointer',
                                  color: '#6b7280',
                                  borderRadius: '4px',
                                }}
                                title="Pin"
                              >
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} style={{ width: '14px', height: '14px' }}>
                                  <path d="M12 2L12 12"/>
                                  <path d="M18.5 12.5L18.5 8.5L5.5 8.5L5.5 12.5L8 15L8 22L16 22L16 15L18.5 12.5Z"/>
                                </svg>
                              </button>
                              <button 
                                onClick={(e) => handleDelete(e, conv.conversation_id)}
                                style={{ 
                                  padding: '4px', 
                                  background: 'transparent', 
                                  border: 'none', 
                                  cursor: 'pointer',
                                  color: '#6b7280',
                                  borderRadius: '4px',
                                }}
                                title="Delete"
                              >
                                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} style={{ width: '14px', height: '14px' }}>
                                  <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                                </svg>
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '32px 16px', color: '#6b7280' }}>
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} style={{ width: '48px', height: '48px', margin: '0 auto 12px', opacity: 0.5 }}>
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                      </svg>
                      <p style={{ fontSize: '13px', marginBottom: '4px' }}>No conversations yet</p>
                      <p style={{ fontSize: '11px' }}>Start chatting with Nicole!</p>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="mem-dash-footer">
          <div className="mem-dash-footer-text">
            Drag pinned chats to reorder • Short chats auto-delete after 3 days
          </div>
        </div>
      </div>
    </aside>
  );
}
