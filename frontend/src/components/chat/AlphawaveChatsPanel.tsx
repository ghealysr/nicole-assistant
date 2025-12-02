'use client';

import { useState, useEffect, useCallback } from 'react';
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
 * Truncate title for display
 */
function truncateTitle(title: string, maxLength: number = 40): string {
  if (title.length <= maxLength) return title;
  return title.slice(0, maxLength - 3) + '...';
}

/**
 * Conversation item component with drag-drop support
 */
function ConversationItem({ 
  conversation, 
  isActive,
  onSelect,
  onPin,
  onDelete,
  onDragStart,
  onDragOver,
  onDrop,
  isDragging,
  isDropTarget,
}: {
  conversation: Conversation;
  isActive: boolean;
  onSelect: () => void;
  onPin: () => void;
  onDelete: () => void;
  onDragStart: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  isDragging: boolean;
  isDropTarget: boolean;
}) {
  const [showActions, setShowActions] = useState(false);
  const isShortConversation = conversation.message_count <= 3;

  return (
    <div
      draggable={conversation.is_pinned}
      onDragStart={onDragStart}
      onDragOver={onDragOver}
      onDrop={onDrop}
      onClick={onSelect}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
      className={`
        group relative px-3 py-2.5 rounded-lg cursor-pointer transition-all duration-150
        ${isActive 
          ? 'bg-[#B8A8D4]/20 border border-[#B8A8D4]/40' 
          : 'hover:bg-[#2a2a2a] border border-transparent'
        }
        ${isDragging ? 'opacity-50' : ''}
        ${isDropTarget ? 'border-[#B8A8D4] border-dashed' : ''}
      `}
    >
      {/* Pin indicator */}
      {conversation.is_pinned && (
        <div className="absolute -left-1 top-1/2 -translate-y-1/2 w-1 h-4 bg-[#B8A8D4] rounded-full" />
      )}
      
      <div className="flex items-start gap-2">
        {/* Icon */}
        <div className={`
          w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5
          ${conversation.is_pinned ? 'bg-[#B8A8D4]/20' : 'bg-[#333]'}
        `}>
          {conversation.is_pinned ? (
            <svg className="w-4 h-4 text-[#B8A8D4]" viewBox="0 0 24 24" fill="currentColor">
              <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
              <path d="M15 2H9a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1z"/>
            </svg>
          ) : (
            <svg className="w-4 h-4 text-[#9ca3af]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          )}
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`
              text-sm font-medium truncate
              ${isActive ? 'text-white' : 'text-[#e5e5e5]'}
            `}>
              {truncateTitle(conversation.title)}
            </span>
            {isShortConversation && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#333] text-[#9ca3af]">
                Draft
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-[#6b7280]">
              {conversation.message_count} messages
            </span>
            <span className="text-[#444]">•</span>
            <span className="text-xs text-[#6b7280]">
              {formatRelativeTime(conversation.last_message_at || conversation.created_at)}
            </span>
          </div>
        </div>
        
        {/* Actions */}
        {showActions && (
          <div className="flex items-center gap-1">
            <button
              onClick={(e) => { e.stopPropagation(); onPin(); }}
              className={`
                p-1.5 rounded-md transition-colors
                ${conversation.is_pinned 
                  ? 'text-[#B8A8D4] hover:bg-[#B8A8D4]/20' 
                  : 'text-[#6b7280] hover:text-white hover:bg-[#333]'
                }
              `}
              title={conversation.is_pinned ? 'Unpin' : 'Pin'}
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill={conversation.is_pinned ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={2}>
                <path d="M12 2L12 12"/>
                <path d="M18.5 12.5L18.5 8.5L5.5 8.5L5.5 12.5L8 15L8 22L16 22L16 15L18.5 12.5Z"/>
              </svg>
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(); }}
              className="p-1.5 rounded-md text-[#6b7280] hover:text-red-400 hover:bg-red-400/10 transition-colors"
              title="Delete"
            >
              <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Chats Panel - Slide-out dashboard for conversation management
 * 
 * Features:
 * - Lists recent conversations (last 30)
 * - Pinned conversations at top (max 5)
 * - Drag-and-drop to reorder pinned chats
 * - Delete conversations
 * - Shows draft indicator for short conversations
 * - Search functionality
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
   * Pin/unpin a conversation
   */
  const handlePin = async (conversationId: number) => {
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
  const handleDelete = async (conversationId: number) => {
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
        c.title.toLowerCase().includes(searchQuery.toLowerCase())
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

  return (
    <div 
      className={`
        fixed top-0 right-0 h-full bg-[#1a1a1a] border-l border-[#333] 
        shadow-2xl z-50 transition-transform duration-300 ease-out
        ${isOpen ? 'translate-x-0' : 'translate-x-full'}
      `}
      style={{ width: '380px' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-[#333]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-[#B8A8D4]/20 flex items-center justify-center">
            <svg className="w-5 h-5 text-[#B8A8D4]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <div>
            <h2 className="text-white font-semibold">Conversations</h2>
            <p className="text-xs text-[#6b7280]">{conversations.length} total</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-2 rounded-lg hover:bg-[#333] text-[#9ca3af] hover:text-white transition-colors"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
        </button>
      </div>

      {/* Search */}
      <div className="px-4 py-3 border-b border-[#333]">
        <div className="relative">
          <svg 
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#6b7280]" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth={2}
          >
            <circle cx="11" cy="11" r="8"/>
            <path d="M21 21l-4.35-4.35"/>
          </svg>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="w-full pl-10 pr-4 py-2 bg-[#2a2a2a] border border-[#333] rounded-lg 
                       text-sm text-white placeholder-[#6b7280] 
                       focus:outline-none focus:border-[#B8A8D4]/50"
          />
        </div>
      </div>

      {/* New Chat Button */}
      <div className="px-4 py-3">
        <button
          onClick={() => { onNewChat(); onClose(); }}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 
                     bg-[#B8A8D4] hover:bg-[#a898c4] text-white rounded-lg 
                     font-medium transition-colors"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="M12 5v14M5 12h14"/>
          </svg>
          New Conversation
        </button>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto px-3 pb-4" style={{ maxHeight: 'calc(100vh - 220px)' }}>
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-[#B8A8D4] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <>
            {/* Pinned Section */}
            {pinnedConvs.length > 0 && (
              <div className="mb-4">
                <div className="flex items-center gap-2 px-2 py-2">
                  <svg className="w-3.5 h-3.5 text-[#B8A8D4]" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2L12 12"/>
                    <path d="M18.5 12.5L18.5 8.5L5.5 8.5L5.5 12.5L8 15L8 22L16 22L16 15L18.5 12.5Z"/>
                  </svg>
                  <span className="text-xs font-semibold text-[#B8A8D4] uppercase tracking-wide">
                    Pinned ({pinnedConvs.length}/5)
                  </span>
                </div>
                <div className="space-y-1">
                  {pinnedConvs.map(conv => (
                    <ConversationItem
                      key={conv.conversation_id}
                      conversation={conv}
                      isActive={conv.conversation_id === currentConversationId}
                      onSelect={() => { onSelectConversation(conv.conversation_id); onClose(); }}
                      onPin={() => handlePin(conv.conversation_id)}
                      onDelete={() => handleDelete(conv.conversation_id)}
                      onDragStart={(e) => handleDragStart(e, conv.conversation_id)}
                      onDragOver={(e) => handleDragOver(e, conv.conversation_id)}
                      onDrop={(e) => handleDrop(e, conv.conversation_id)}
                      isDragging={draggedId === conv.conversation_id}
                      isDropTarget={dropTargetId === conv.conversation_id}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Recent Section */}
            <div>
              <div className="flex items-center gap-2 px-2 py-2">
                <svg className="w-3.5 h-3.5 text-[#6b7280]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 6v6l4 2"/>
                </svg>
                <span className="text-xs font-semibold text-[#6b7280] uppercase tracking-wide">
                  Recent
                </span>
              </div>
              <div className="space-y-1">
                {recentConvs.length > 0 ? (
                  recentConvs.map(conv => (
                    <ConversationItem
                      key={conv.conversation_id}
                      conversation={conv}
                      isActive={conv.conversation_id === currentConversationId}
                      onSelect={() => { onSelectConversation(conv.conversation_id); onClose(); }}
                      onPin={() => handlePin(conv.conversation_id)}
                      onDelete={() => handleDelete(conv.conversation_id)}
                      onDragStart={() => {}}
                      onDragOver={() => {}}
                      onDrop={() => {}}
                      isDragging={false}
                      isDropTarget={false}
                    />
                  ))
                ) : (
                  <div className="text-center py-8 text-[#6b7280]">
                    <svg className="w-12 h-12 mx-auto mb-3 opacity-50" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                    </svg>
                    <p className="text-sm">No conversations yet</p>
                    <p className="text-xs mt-1">Start chatting with Nicole!</p>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Footer Info */}
      <div className="px-4 py-3 border-t border-[#333] bg-[#1a1a1a]">
        <p className="text-xs text-[#6b7280] text-center">
          Drag pinned chats to reorder • Short chats auto-delete after 3 days
        </p>
      </div>
    </div>
  );
}

