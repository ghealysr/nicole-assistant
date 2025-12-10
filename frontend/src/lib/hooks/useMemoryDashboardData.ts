/**
 * useMemoryDashboardData Hook
 * 
 * Centralized data fetching for the Memory Dashboard.
 * Handles authentication, loading states, and error handling.
 * 
 * Backend APIs:
 * - GET /api/memories/stats - Memory statistics
 * - GET /api/memories - Memory list
 * - GET /api/documents/list - Document list
 * - GET /api/conversations - Conversation history
 */

import { useState, useEffect, useCallback } from 'react';

// Types from backend APIs
export interface MemoryStats {
  total: number;
  active: number;
  archived: number;
  avgConfidence: number;
  highConfidenceCount: number;
  decayingCount: number;
  factCount: number;
  preferenceCount: number;
  patternCount: number;
  otherCount: number;
  by_type?: Record<string, number>;
  avg_confidence?: number;
  by_confidence?: {
    high: number;
    medium: number;
    low: number;
  };
}

export interface Memory {
  id: string | number;
  memory_id?: number;
  type: string;
  memory_type?: string;
  content: string;
  confidence: number;
  confidence_score?: number;
  access_count?: number;
  accessCount?: number;
  last_accessed?: string;
  lastAccessed?: string;
  created_at?: string;
}

export interface Document {
  id: number;
  doc_id?: number;
  name?: string;
  title?: string;
  filename?: string;
  file_name?: string;
  type: 'pdf' | 'image' | 'code' | string;
  source_type?: string;
  size: string;
  file_size?: number;
  chunks: number;
  chunk_count?: number;
  status: 'processed' | 'processing' | 'pending';
  uploaded: string;
  created_at?: string;
}

export interface Conversation {
  id: number;
  conversation_id?: number;
  title: string;
  preview?: string;
  first_message_preview?: string;
  date: string;
  created_at?: string;
  updated_at?: string;
  messages: number;
  message_count?: number;
  memoriesCreated?: number;
  is_pinned?: boolean;
}

export interface DashboardData {
  stats: MemoryStats | null;
  memories: Memory[];
  documents: Document[];
  conversations: Conversation[];
  loading: boolean;
  error: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.nicole.alphawavetech.com';

/**
 * Helper to get auth headers
 */
function getAuthHeaders(authToken?: string): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }
  
  return headers;
}

/**
 * Fetch memory statistics
 */
async function fetchMemoryStats(authToken?: string): Promise<MemoryStats | null> {
  if (!authToken) return null;
  
  try {
    const response = await fetch(`${API_BASE}/api/memories/stats`, {
      headers: getAuthHeaders(authToken),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch memory stats: ${response.status}`);
    }
    
    const data = await response.json();
    
    // Transform backend response to match frontend interface
    return {
      total: data.total || 0,
      active: data.active || data.total || 0,
      archived: data.archived || 0,
      avgConfidence: data.avg_confidence ? Math.round(data.avg_confidence * 100) : 0,
      highConfidenceCount: data.by_confidence?.high || 0,
      decayingCount: data.by_confidence?.low || 0,
      factCount: data.by_type?.fact || 0,
      preferenceCount: data.by_type?.preference || 0,
      patternCount: data.by_type?.pattern || 0,
      otherCount: (data.by_type?.correction || 0) + (data.by_type?.relationship || 0) + (data.by_type?.goal || 0),
    };
  } catch (error) {
    console.error('[MEMORY DASHBOARD] Failed to fetch stats:', error);
    return null;
  }
}

/**
 * Fetch memory list
 */
async function fetchMemories(authToken?: string, limit = 50): Promise<Memory[]> {
  if (!authToken) return [];
  
  try {
    const response = await fetch(`${API_BASE}/api/memories?limit=${limit}`, {
      headers: getAuthHeaders(authToken),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch memories: ${response.status}`);
    }
    
    const data = await response.json();
    const memories = data.memories || [];
    
    // Normalize the response
    return memories.map((m: Record<string, unknown>) => ({
      id: m.memory_id || m.id,
      type: m.memory_type || m.type,
      content: m.content,
      confidence: m.confidence_score || m.confidence || 0,
      accessCount: m.access_count || 0,
      lastAccessed: m.last_accessed || m.created_at || 'Unknown',
    }));
  } catch (error) {
    console.error('[MEMORY DASHBOARD] Failed to fetch memories:', error);
    return [];
  }
}

/**
 * Fetch document list
 */
async function fetchDocuments(authToken?: string, limit = 50): Promise<Document[]> {
  if (!authToken) return [];
  
  try {
    const response = await fetch(`${API_BASE}/api/documents/list?limit=${limit}`, {
      headers: getAuthHeaders(authToken),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch documents: ${response.status}`);
    }
    
    const data = await response.json();
    const documents = data.documents || [];
    
    // Normalize the response
    return documents.map((d: Record<string, unknown>) => ({
      id: d.document_id || d.doc_id || d.id,  // Backend now returns document_id
      name: d.title || d.filename || d.file_name || 'Untitled',  // Backend returns filename
      type: inferDocumentType((d.filename || d.file_name || '') as string),
      size: formatFileSize((d.file_size || 0) as number),
      chunks: d.chunks_count || d.chunk_count || d.chunks || 0,  // Backend returns chunks_count
      status: (d.status || 'processed') as 'processed' | 'processing' | 'pending',
      uploaded: formatDate(d.created_at as string | undefined),
    }));
  } catch (error) {
    console.error('[MEMORY DASHBOARD] Failed to fetch documents:', error);
    return [];
  }
}

/**
 * Fetch conversation list
 */
async function fetchConversations(authToken?: string, limit = 50): Promise<Conversation[]> {
  if (!authToken) return [];
  
  try {
    const response = await fetch(`${API_BASE}/api/conversations?limit=${limit}`, {
      headers: getAuthHeaders(authToken),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to fetch conversations: ${response.status}`);
    }
    
    const data = await response.json();
    const conversations = data.conversations || [];
    
    // Normalize the response
    return conversations.map((c: Record<string, unknown>) => ({
      id: c.conversation_id || c.id,
      title: c.title || 'Untitled',
      preview: c.first_message_preview || c.preview || '',
      date: formatDate((c.updated_at || c.created_at) as string | undefined),
      messages: c.message_count || c.messages || 0,
      memoriesCreated: 0, // This data isn't available from the API yet
    }));
  } catch (error) {
    console.error('[MEMORY DASHBOARD] Failed to fetch conversations:', error);
    return [];
  }
}

/**
 * Helper: Infer document type from filename
 */
function inferDocumentType(filename: string): 'pdf' | 'image' | 'code' {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  
  if (ext === 'pdf') return 'pdf';
  if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return 'image';
  return 'code';
}

/**
 * Helper: Format file size
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${Math.round(bytes / Math.pow(k, i))} ${sizes[i]}`;
}

/**
 * Helper: Format date relative to now
 */
function formatDate(dateString?: string): string {
  if (!dateString) return 'Unknown';
  
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} week${Math.floor(diffDays / 7) > 1 ? 's' : ''} ago`;
    
    return date.toLocaleDateString();
  } catch {
    return 'Unknown';
  }
}

/**
 * Main hook: useMemoryDashboardData
 */
export function useMemoryDashboardData(authToken?: string) {
  const [data, setData] = useState<DashboardData>({
    stats: null,
    memories: [],
    documents: [],
    conversations: [],
    loading: true,
    error: null,
  });
  
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  
  const loadData = useCallback(async () => {
    if (!authToken) {
      console.log('[MEMORY DASHBOARD] No auth token, skipping data load');
      setData({
        stats: null,
        memories: [],
        documents: [],
        conversations: [],
        loading: false,
        error: null,
      });
      return;
    }
    
    console.log('[MEMORY DASHBOARD] Loading data with auth token:', authToken.substring(0, 20) + '...');
    setData(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      // Fetch all data in parallel
      const [stats, memories, documents, conversations] = await Promise.all([
        fetchMemoryStats(authToken),
        fetchMemories(authToken),
        fetchDocuments(authToken),
        fetchConversations(authToken),
      ]);
      
      console.log('[MEMORY DASHBOARD] Data loaded:', {
        stats: stats ? 'OK' : 'NULL',
        memoriesCount: memories.length,
        documentsCount: documents.length,
        conversationsCount: conversations.length,
      });
      
      setData({
        stats,
        memories,
        documents,
        conversations,
        loading: false,
        error: null,
      });
    } catch (error) {
      console.error('[MEMORY DASHBOARD] Failed to load data:', error);
      setData(prev => ({
        ...prev,
        loading: false,
        error: 'Failed to load dashboard data. Please try again.',
      }));
    }
  }, [authToken]);
  
  // Load data on mount and when auth token changes
  useEffect(() => {
    loadData();
  }, [loadData, refreshTrigger]);
  
  // Provide a refresh function
  const refresh = useCallback(() => {
    setRefreshTrigger(prev => prev + 1);
  }, []);
  
  return {
    ...data,
    refresh,
  };
}

