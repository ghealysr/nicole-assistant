'use client';

import { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Props for AlphawaveChatInput.
 */
interface AlphawaveChatInputProps {
  onSendMessage: (content: string) => void;
  isLoading: boolean;
}

type ModelType = 'Sonnet 4.5' | 'Opus 4.5' | 'Haiku 4.5';

interface PendingFile {
  id: string;
  name: string;
  file: File;
  status: 'pending' | 'uploading' | 'processing' | 'ready' | 'error';
  summary?: string;
  error?: string;
}

/**
 * Chat input component for Nicole V7.
 * Supports file uploads with document intelligence processing.
 */
export function AlphawaveChatInput({ onSendMessage, isLoading }: AlphawaveChatInputProps) {
  const [content, setContent] = useState('');
  const [selectedModel, setSelectedModel] = useState<ModelType>('Sonnet 4.5');
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const modelMenuRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = '60px';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [content]);

  // Close model menu on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (modelMenuRef.current && !modelMenuRef.current.contains(e.target as Node)) {
        setIsModelMenuOpen(false);
      }
    }
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  /**
   * Upload a file to the document intelligence API.
   */
  const uploadFile = useCallback(async (file: File, fileId: string) => {
    // Update status to uploading
    setPendingFiles(prev => prev.map(f => 
      f.id === fileId ? { ...f, status: 'uploading' as const } : f
    ));

    try {
      const formData = new FormData();
      formData.append('file', file);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://api.nicole.alphawavetech.com';
      const token = localStorage.getItem('supabase.auth.token');
      
      // Parse token to get access_token
      let accessToken = '';
      if (token) {
        try {
          const parsed = JSON.parse(token);
          accessToken = parsed.access_token || '';
        } catch {
          accessToken = token;
        }
      }

      // Update status to processing
      setPendingFiles(prev => prev.map(f => 
        f.id === fileId ? { ...f, status: 'processing' as const } : f
      ));

      const response = await fetch(`${apiUrl}/documents/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${accessToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const result = await response.json();

      // Update with result
      setPendingFiles(prev => prev.map(f => 
        f.id === fileId ? { 
          ...f, 
          status: 'ready' as const, 
          summary: result.summary || 'Document processed' 
        } : f
      ));

    } catch (error) {
      console.error('File upload error:', error);
      setPendingFiles(prev => prev.map(f => 
        f.id === fileId ? { 
          ...f, 
          status: 'error' as const, 
          error: 'Upload failed' 
        } : f
      ));
    }
  }, []);

  /**
   * Handles file selection from input.
   */
  const handleFileSelect = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return;

    const maxFiles = 5 - pendingFiles.length;
    const newFiles: PendingFile[] = [];

    for (let i = 0; i < Math.min(files.length, maxFiles); i++) {
      const file = files[i];
      const fileId = `${Date.now()}-${i}`;
      
      newFiles.push({
        id: fileId,
        name: file.name,
        file: file,
        status: 'pending',
      });
    }

    if (newFiles.length > 0) {
      setPendingFiles(prev => [...prev, ...newFiles]);
      
      // Start uploads
      newFiles.forEach(f => uploadFile(f.file, f.id));
    }
  }, [pendingFiles.length, uploadFile]);

  /**
   * Handles form submission to send the message.
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Include file context in message
    let messageContent = content.trim();
    
    const readyFiles = pendingFiles.filter(f => f.status === 'ready');
    if (readyFiles.length > 0) {
      const fileContext = readyFiles
        .map(f => `[Uploaded: ${f.name}${f.summary ? ` - ${f.summary}` : ''}]`)
        .join('\n');
      
      if (messageContent) {
        messageContent = `${fileContext}\n\n${messageContent}`;
      } else {
        messageContent = `${fileContext}\n\nPlease review and summarize the document(s) I just uploaded.`;
      }
    }

    if (messageContent && !isLoading) {
      onSendMessage(messageContent);
      setContent('');
      setPendingFiles([]);
    }
  };

  /**
   * Handles keyboard shortcuts (Enter to send).
   */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  /**
   * Opens file picker.
   */
  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  /**
   * Removes a pending file.
   */
  const removeFile = (id: string) => {
    setPendingFiles(pendingFiles.filter(f => f.id !== id));
  };

  /**
   * Handle drag events.
   */
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  };

  /**
   * Get file icon based on type.
   */
  const getFileIcon = (fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') return '📕';
    if (ext === 'doc' || ext === 'docx') return '📘';
    if (ext === 'txt' || ext === 'md') return '📄';
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext || '')) return '🖼️';
    return '📎';
  };

  /**
   * Get status indicator.
   */
  const getStatusIndicator = (status: PendingFile['status']) => {
    switch (status) {
      case 'uploading':
      case 'processing':
        return <span className="animate-spin">⏳</span>;
      case 'ready':
        return <span className="text-green-600">✓</span>;
      case 'error':
        return <span className="text-red-500">✕</span>;
      default:
        return null;
    }
  };

  const hasReadyFiles = pendingFiles.some(f => f.status === 'ready');
  const hasProcessingFiles = pendingFiles.some(f => f.status === 'uploading' || f.status === 'processing');

  return (
    <div 
      className={`bg-[#F5F4ED] px-6 py-4 pb-6 shrink-0 transition-all ${isDragOver ? 'ring-2 ring-[#B8A8D4] ring-inset' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="max-w-[800px] mx-auto">
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.txt,.md,.jpg,.jpeg,.png,.gif,.webp"
          className="hidden"
          onChange={(e) => handleFileSelect(e.target.files)}
        />

        {/* Drag overlay message */}
        {isDragOver && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#F5F4ED]/90 z-10 pointer-events-none">
            <div className="text-center">
              <div className="text-4xl mb-2">📄</div>
              <div className="text-lg text-[#6b7280]">Drop files here</div>
            </div>
          </div>
        )}

        {/* Pending files */}
        {pendingFiles.length > 0 && (
          <div className="flex gap-2 flex-wrap mb-3">
            {pendingFiles.map(file => (
              <div 
                key={file.id} 
                className={`
                  flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-white text-sm
                  ${file.status === 'error' ? 'border-red-300 bg-red-50' : 'border-[#d8d7cc]'}
                  ${file.status === 'ready' ? 'border-green-300 bg-green-50' : ''}
                `}
              >
                <span>{getFileIcon(file.name)}</span>
                <span className="max-w-[150px] truncate text-[#374151]">{file.name}</span>
                {getStatusIndicator(file.status)}
                <button 
                  onClick={() => removeFile(file.id)}
                  className="border-0 bg-transparent text-[#9ca3af] cursor-pointer text-base px-1 hover:text-[#6b7280]"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
        
        {/* Processing indicator */}
        {hasProcessingFiles && (
          <div className="text-xs text-[#6b7280] mb-2 flex items-center gap-1">
            <span className="animate-spin">⏳</span>
            Processing documents with Azure Document Intelligence...
          </div>
        )}
        
        {/* Input box */}
        <form onSubmit={handleSubmit} className="input-box">
          <textarea
            ref={textareaRef}
            className="input-textarea"
            placeholder={hasReadyFiles ? "Add a message about your files, or send to get a summary..." : "Message Nicole..."}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
          />
          
          <div className="flex items-center justify-between mt-3">
            {/* Tool buttons */}
            <div className="flex gap-1">
              <button 
                type="button" 
                className="tool-btn" 
                onClick={openFilePicker} 
                title="Upload document (PDF, Word, images)"
                disabled={pendingFiles.length >= 5}
              >
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                  <line x1="12" y1="5" x2="12" y2="19"/>
                  <line x1="5" y1="12" x2="19" y2="12"/>
                </svg>
              </button>
              <button type="button" className="tool-btn" title="Extended thinking">
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 6v6l4 2"/>
                </svg>
              </button>
              <button type="button" className="tool-btn" title="Web search">
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                  <circle cx="11" cy="11" r="8"/>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
              </button>
            </div>

            {/* Right side - model selector and send */}
            <div className="flex items-center gap-3">
              {/* Model selector */}
              <div className="relative" ref={modelMenuRef}>
                <button 
                  type="button"
                  onClick={() => setIsModelMenuOpen(!isModelMenuOpen)}
                  className="flex items-center gap-1 px-2.5 py-1.5 border-0 bg-transparent rounded-lg cursor-pointer text-[13px] text-[#6b7280] transition-colors hover:bg-[#f3f4f6]"
                >
                  <span>{selectedModel}</span>
                  <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} className="w-3 h-3 stroke-[#6b7280]">
                    <path d="M6 9l6 6 6-6"/>
                  </svg>
                </button>
                
                {isModelMenuOpen && (
                  <div className="model-dropdown">
                    {(['Sonnet 4.5', 'Opus 4.5', 'Haiku 4.5'] as ModelType[]).map(model => (
                      <button
                        key={model}
                        type="button"
                        className="model-option"
                        onClick={() => {
                          setSelectedModel(model);
                          setIsModelMenuOpen(false);
                        }}
                      >
                        {model}
                        {selectedModel === model && (
                          <svg viewBox="0 0 24 24" fill="none" className="w-3.5 h-3.5 stroke-[#B8A8D4]" strokeWidth={2.5}>
                            <path d="M20 6L9 17l-5-5"/>
                          </svg>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Send button */}
              <button 
                type="submit"
                className="send-btn"
                disabled={(!content.trim() && !hasReadyFiles) || isLoading || hasProcessingFiles}
              >
                <svg viewBox="0 0 24 24" fill="none" className="w-[18px] h-[18px] stroke-white" strokeWidth={2.5}>
                  <path d="M12 19V5m0 0l-7 7m7-7l7 7"/>
                </svg>
              </button>
            </div>
          </div>
        </form>
        
        {/* File types hint */}
        <div className="text-[10px] text-[#9ca3af] mt-2 text-center">
          Supports PDF, Word, text, and images • Drag & drop or click +
        </div>
      </div>
    </div>
  );
}
