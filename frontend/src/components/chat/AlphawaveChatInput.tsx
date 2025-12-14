'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import Image from 'next/image';
import { getStoredToken } from '@/lib/google_auth';
import { API_URL } from '@/lib/alphawave_config';
import { parseSlashCommand } from '@/lib/hooks/useImageGeneration';

// Voice state types
type VoiceInputState = 'idle' | 'listening' | 'processing';
type VoiceOutputState = 'off' | 'on';

/**
 * File attachment with metadata for Claude-style display.
 */
export interface FileAttachment {
  id: string;
  name: string;
  type: string;
  size: number;
  documentId?: string;  // From backend after processing
  thumbnailUrl?: string;  // For image previews
}

/**
 * Props for AlphawaveChatInput.
 */
interface AlphawaveChatInputProps {
  onSendMessage: (content: string, attachments?: FileAttachment[]) => void;
  isLoading: boolean;
}

type ModelType = 'Sonnet 4.5' | 'Opus 4.5' | 'Haiku 4.5';

interface PendingFile {
  id: string;
  name: string;
  file: File;
  type: string;
  size: number;
  status: 'pending' | 'uploading' | 'processing' | 'ready' | 'error';
  documentId?: string;
  thumbnailUrl?: string;
  error?: string;
}

/**
 * Chat input component for Nicole V7.
 * Claude-style file uploads with thumbnail previews and invisible AI processing.
 */
export function AlphawaveChatInput({ onSendMessage, isLoading }: AlphawaveChatInputProps) {
  const [content, setContent] = useState('');
  const [selectedModel, setSelectedModel] = useState<ModelType>('Sonnet 4.5');
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  
  // Voice states
  const [voiceInputState, setVoiceInputState] = useState<VoiceInputState>('idle');
  const [voiceOutputEnabled, setVoiceOutputEnabled] = useState<VoiceOutputState>('off');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  
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
   * Create thumbnail URL for image files.
   */
  const createThumbnail = (file: File): string | undefined => {
    if (file.type.startsWith('image/')) {
      return URL.createObjectURL(file);
    }
    return undefined;
  };

  /**
   * Upload a file to the document intelligence API.
   * Azure analysis is internal - not exposed to user.
   */
  const uploadFile = useCallback(async (file: File, fileId: string) => {
    setPendingFiles(prev => prev.map(f => 
      f.id === fileId ? { ...f, status: 'uploading' as const } : f
    ));

    try {
      const token = getStoredToken();
      if (!token) {
        throw new Error('Please log in to upload files');
      }

      const formData = new FormData();
      formData.append('file', file);

      setPendingFiles(prev => prev.map(f => 
        f.id === fileId ? { ...f, status: 'processing' as const } : f
      ));

      const response = await fetch(`${API_URL}/documents/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Upload failed');
      }

      const result = await response.json();

      // Store document ID for backend context - NO visible metadata
      setPendingFiles(prev => prev.map(f => 
        f.id === fileId ? { 
          ...f, 
          status: 'ready' as const,
          documentId: result.document_id,
        } : f
      ));

    } catch (error) {
      console.error('File upload error:', error);
      setPendingFiles(prev => prev.map(f => 
        f.id === fileId ? { 
          ...f, 
          status: 'error' as const, 
          error: error instanceof Error ? error.message : 'Upload failed' 
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
      const thumbnailUrl = createThumbnail(file);
      
      newFiles.push({
        id: fileId,
        name: file.name,
        file: file,
        type: file.type,
        size: file.size,
        status: 'pending',
        thumbnailUrl,
      });
    }

    if (newFiles.length > 0) {
      setPendingFiles(prev => [...prev, ...newFiles]);
      newFiles.forEach(f => uploadFile(f.file, f.id));
    }
  }, [pendingFiles.length, uploadFile]);

  /**
   * Handles form submission - sends CLEAN message + attachment metadata.
   * No [Uploaded: ...] blocks - Azure analysis stays invisible.
   * Also handles slash commands for image generation.
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const messageText = content.trim();
    
    // Check for image generation slash commands
    const slashCommand = parseSlashCommand(messageText);
    if (slashCommand) {
      // Open Image Studio with the prompt and preset
      const openImageStudio = (window as unknown as { 
        openImageStudio?: (prompt?: string, preset?: string) => void 
      }).openImageStudio;
      
      if (openImageStudio) {
        // Map command to preset slash command
        const presetMap: Record<string, string> = {
          logo: '1',
          hero: '2',
          ig: '3',
          poster: '4',
          thumb: '5',
          image: '1', // default to logo
        };
        openImageStudio(slashCommand.prompt, presetMap[slashCommand.command]);
        setContent('');
        return;
      }
    }
    
    const readyFiles = pendingFiles.filter(f => f.status === 'ready');
    
    // Build clean attachments array (no Azure metadata exposed)
    const attachments: FileAttachment[] = readyFiles.map(f => ({
      id: f.id,
      name: f.name,
      type: f.type,
      size: f.size,
      documentId: f.documentId,
      thumbnailUrl: f.thumbnailUrl,
    }));

    // Send message with attachments - NO metadata in message content
    if ((messageText || attachments.length > 0) && !isLoading) {
      const finalMessage = messageText || (attachments.length > 0 
        ? "Please review what I've shared." 
        : '');
      
      onSendMessage(finalMessage, attachments.length > 0 ? attachments : undefined);
      setContent('');
      
      // Clean up thumbnail URLs
      pendingFiles.forEach(f => {
        if (f.thumbnailUrl) URL.revokeObjectURL(f.thumbnailUrl);
      });
      setPendingFiles([]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  const removeFile = (id: string) => {
    const file = pendingFiles.find(f => f.id === id);
    if (file?.thumbnailUrl) URL.revokeObjectURL(file.thumbnailUrl);
    setPendingFiles(pendingFiles.filter(f => f.id !== id));
  };

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
   * Check if file is an image type.
   */
  const isImageFile = (type: string): boolean => {
    return type.startsWith('image/');
  };

  const hasReadyFiles = pendingFiles.some(f => f.status === 'ready');
  const hasProcessingFiles = pendingFiles.some(f => 
    f.status === 'uploading' || f.status === 'processing'
  );

  /**
   * Start voice recording for Whisper STT.
   */
  const startVoiceInput = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setVoiceInputState('processing');
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        try {
          const token = getStoredToken();
          if (!token) throw new Error('Not authenticated');

          const formData = new FormData();
          formData.append('audio', audioBlob, 'recording.webm');

          const response = await fetch(`${API_URL}/voice/transcribe`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData,
          });

          if (response.ok) {
            const data = await response.json();
            if (data.text) {
              setContent(prev => prev + (prev ? ' ' : '') + data.text);
            }
          }
        } catch (error) {
          console.error('Transcription error:', error);
        } finally {
          setVoiceInputState('idle');
          stream.getTracks().forEach(track => track.stop());
        }
      };

      mediaRecorder.start();
      setVoiceInputState('listening');
    } catch (error) {
      console.error('Microphone access error:', error);
      setVoiceInputState('idle');
    }
  }, []);

  /**
   * Stop voice recording.
   */
  const stopVoiceInput = useCallback(() => {
    if (mediaRecorderRef.current && voiceInputState === 'listening') {
      mediaRecorderRef.current.stop();
    }
  }, [voiceInputState]);

  /**
   * Toggle voice input recording.
   */
  const toggleVoiceInput = useCallback(() => {
    if (voiceInputState === 'idle') {
      startVoiceInput();
    } else if (voiceInputState === 'listening') {
      stopVoiceInput();
    }
  }, [voiceInputState, startVoiceInput, stopVoiceInput]);

  /**
   * Toggle voice output (TTS for Nicole's responses).
   */
  const toggleVoiceOutput = useCallback(() => {
    setVoiceOutputEnabled(prev => prev === 'off' ? 'on' : 'off');
    // Store preference in localStorage
    const newState = voiceOutputEnabled === 'off' ? 'on' : 'off';
    localStorage.setItem('nicole_voice_output', newState);
  }, [voiceOutputEnabled]);

  // Load voice output preference on mount
  useEffect(() => {
    const saved = localStorage.getItem('nicole_voice_output') as VoiceOutputState | null;
    if (saved) setVoiceOutputEnabled(saved);
  }, []);

  return (
    <div 
      className={`bg-[#F5F4ED] px-6 py-4 pb-6 shrink-0 transition-all ${
        isDragOver ? 'ring-2 ring-[#B8A8D4] ring-inset' : ''
      }`}
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

        {/* Drag overlay */}
        {isDragOver && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#F5F4ED]/90 z-10 pointer-events-none">
            <div className="text-center">
              <div className="text-4xl mb-2">📄</div>
              <div className="text-lg text-[#6b7280]">Drop files here</div>
            </div>
          </div>
        )}

        {/* Claude-style Thumbnail Previews */}
        {pendingFiles.length > 0 && (
          <div className="flex gap-3 flex-wrap mb-4">
            {pendingFiles.map(file => (
              <div 
                key={file.id} 
                className={`
                  relative group rounded-xl overflow-hidden border-2 transition-all
                  ${file.status === 'error' 
                    ? 'border-red-300 bg-red-50' 
                    : file.status === 'ready' 
                      ? 'border-[#d8d7cc] bg-white' 
                      : 'border-[#e5e4dc] bg-[#fafaf8]'
                  }
                `}
              >
                {/* Image Thumbnail */}
                {isImageFile(file.type) && file.thumbnailUrl ? (
                  <div className="w-20 h-20 relative">
                    <Image
                      src={file.thumbnailUrl}
                      alt={file.name}
                      fill
                      className="object-cover"
                    />
                    {/* Processing overlay */}
                    {(file.status === 'uploading' || file.status === 'processing') && (
                      <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      </div>
                    )}
                  </div>
                ) : (
                  /* Document Preview */
                  <div className="w-20 h-20 flex flex-col items-center justify-center p-2">
                    <div className="text-2xl mb-1">
                      {file.type.includes('pdf') ? '📕' : 
                       file.type.includes('word') ? '📘' : '📄'}
                    </div>
                    <div className="text-[9px] text-[#6b7280] text-center truncate w-full px-1">
                      {file.name.length > 12 
                        ? file.name.slice(0, 10) + '...' 
                        : file.name
                      }
                    </div>
                    {(file.status === 'uploading' || file.status === 'processing') && (
                      <div className="absolute inset-0 bg-white/60 flex items-center justify-center">
                        <div className="w-5 h-5 border-2 border-[#B8A8D4] border-t-transparent rounded-full animate-spin" />
                      </div>
                    )}
                  </div>
                )}

                {/* Remove button - appears on hover */}
                <button
                  onClick={() => removeFile(file.id)}
                  className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-[#374151] text-white rounded-full 
                           flex items-center justify-center text-xs opacity-0 group-hover:opacity-100 
                           transition-opacity hover:bg-[#1f2937] shadow-sm"
                >
                  ×
                </button>

                {/* Ready indicator */}
                {file.status === 'ready' && (
                  <div className="absolute bottom-1 right-1 w-4 h-4 bg-green-500 rounded-full 
                                flex items-center justify-center">
                    <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}

                {/* Error indicator */}
                {file.status === 'error' && (
                  <div className="absolute bottom-1 right-1 w-4 h-4 bg-red-500 rounded-full 
                                flex items-center justify-center text-white text-xs font-bold">
                    !
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Processing status - subtle, not technical */}
        {hasProcessingFiles && (
          <div className="text-xs text-[#9ca3af] mb-2 flex items-center gap-1.5">
            <div className="w-3 h-3 border-2 border-[#B8A8D4] border-t-transparent rounded-full animate-spin" />
            Preparing files...
          </div>
        )}
        
        {/* Input box */}
        <form onSubmit={handleSubmit} className="input-box">
          <textarea
            ref={textareaRef}
            className="input-textarea"
            placeholder={pendingFiles.length > 0 
              ? "Add a message..." 
              : "Message Nicole..."
            }
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
                title="Attach files"
                disabled={pendingFiles.length >= 5}
              >
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
                </svg>
              </button>
              <button 
                type="button" 
                className={`tool-btn ${voiceInputState === 'listening' ? 'voice-active' : ''} ${voiceInputState === 'processing' ? 'voice-processing' : ''}`}
                title={voiceInputState === 'idle' ? 'Voice input (Whisper)' : voiceInputState === 'listening' ? 'Stop recording' : 'Processing...'}
                onClick={toggleVoiceInput}
                disabled={voiceInputState === 'processing'}
              >
                {/* Microphone icon for Whisper STT */}
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                  <line x1="12" y1="19" x2="12" y2="23"/>
                  <line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
              </button>
              <button 
                type="button" 
                className={`tool-btn ${voiceOutputEnabled === 'on' ? 'voice-enabled' : ''}`}
                title={voiceOutputEnabled === 'on' ? "Disable Nicole's voice" : "Enable Nicole's voice"}
                onClick={toggleVoiceOutput}
              >
                {/* Speaker/volume icon for ElevenLabs TTS */}
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                  {voiceOutputEnabled === 'on' ? (
                    <>
                      <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
                      <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
                    </>
                  ) : (
                    <line x1="23" y1="9" x2="17" y2="15"/>
                  )}
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
                  className="flex items-center gap-1 px-2.5 py-1.5 border-0 bg-transparent rounded-lg 
                           cursor-pointer text-[13px] text-[#6b7280] transition-colors hover:bg-[#f3f4f6]"
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
      </div>
    </div>
  );
}
