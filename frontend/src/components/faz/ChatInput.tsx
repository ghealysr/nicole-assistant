'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Send, ImageIcon, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { fazApi } from '@/lib/faz/api';
import { useFazStore } from '@/lib/faz/store';

interface UploadedImage {
  file: File;
  preview: string;
  note: string;
}

interface ChatInputProps {
  projectId?: number;
  onSend: (message: string, imageUrls?: string[]) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ projectId, onSend, disabled, placeholder }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Get store functions for dismissing approval gate when user types
  const { currentGate, setCurrentGate } = useFazStore();

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    
    // Dismiss approval button when user starts typing (considered as "no approval")
    if (currentGate && e.target.value.trim()) {
      setCurrentGate(null);
    }
    
    // Auto-resize
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = async () => {
    if ((!input.trim() && uploadedImages.length === 0) || disabled || isUploading) return;
    
    let imageUrls: string[] = [];
    
    // Upload images if any
    if (uploadedImages.length > 0 && projectId) {
      setIsUploading(true);
      try {
        const files = uploadedImages.map(img => img.file);
        const result = await fazApi.uploadReferenceImages(projectId, files);
        if (result.success) {
          imageUrls = result.images.map(img => img.url);
        }
      } catch (error) {
        console.error('Failed to upload images:', error);
      } finally {
        setIsUploading(false);
      }
    }
    
    // Build message with image notes if any
    let fullMessage = input.trim();
    if (uploadedImages.length > 0) {
      const imageNotes = uploadedImages
        .filter(img => img.note.trim())
        .map((img, i) => `[Reference Image ${i + 1}]: ${img.note}`)
        .join('\n');
      if (imageNotes) {
        fullMessage = fullMessage ? `${fullMessage}\n\n${imageNotes}` : imageNotes;
      }
    }
    
    // Send the message with optional image URLs
    onSend(fullMessage, imageUrls.length > 0 ? imageUrls : undefined);
    
    // Clean up
    setInput('');
    uploadedImages.forEach(img => URL.revokeObjectURL(img.preview));
    setUploadedImages([]);
    
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    
    // Limit to 5 images total
    const remaining = 5 - uploadedImages.length;
    const toAdd = files.slice(0, remaining);
    
    const newImages: UploadedImage[] = toAdd.map(file => ({
      file,
      preview: URL.createObjectURL(file),
      note: ''
    }));
    
    setUploadedImages(prev => [...prev, ...newImages]);
    
    // Clear the input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeImage = (index: number) => {
    setUploadedImages(prev => {
      const removed = prev[index];
      URL.revokeObjectURL(removed.preview);
      return prev.filter((_, i) => i !== index);
    });
  };

  const updateImageNote = (index: number, note: string) => {
    setUploadedImages(prev => 
      prev.map((img, i) => i === index ? { ...img, note } : img)
    );
  };

  // Cleanup previews on unmount
  useEffect(() => {
    return () => {
      uploadedImages.forEach(img => URL.revokeObjectURL(img.preview));
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-3">
      {/* Image previews with notes */}
      <AnimatePresence>
        {uploadedImages.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="grid grid-cols-2 sm:grid-cols-3 gap-2"
          >
            {uploadedImages.map((img, idx) => (
              <motion.div
                key={img.preview}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="relative group"
              >
                <div className="relative aspect-video bg-[#1E1E2E] rounded-lg overflow-hidden">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img 
                    src={img.preview} 
                    alt={`Reference ${idx + 1}`}
                    className="w-full h-full object-cover"
                  />
                  <button
                    onClick={() => removeImage(idx)}
                    className="absolute top-1 right-1 p-1 bg-black/60 rounded-full text-white opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X size={12} />
                  </button>
                </div>
                <input
                  type="text"
                  placeholder="Add note..."
                  value={img.note}
                  onChange={(e) => updateImageNote(idx, e.target.value)}
                  className="mt-1 w-full text-[10px] px-2 py-1 bg-[#1E1E2E] border border-[#2D2D3D] rounded text-[#94A3B8] placeholder-[#4a4a5a] focus:outline-none focus:border-[#6366F1]"
                />
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input area */}
      <div className="relative bg-[#12121A] border border-[#1E1E2E] rounded-xl focus-within:border-[#6366F1] transition-colors">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || "Ask Nicole to change something..."}
          className="w-full bg-transparent text-[#F1F5F9] placeholder-[#64748B] p-4 pr-24 text-sm resize-none outline-none min-h-[50px] max-h-[200px]"
          rows={1}
          disabled={disabled || isUploading}
        />
        
        {/* Action buttons */}
        <div className="absolute right-3 bottom-3 flex items-center gap-2">
          {/* Image upload button */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={handleImageUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || uploadedImages.length >= 5 || isUploading}
            className={cn(
              "p-1.5 rounded-lg transition-all",
              uploadedImages.length < 5 && !disabled && !isUploading
                ? "text-zinc-400 hover:text-purple-400 hover:bg-zinc-800"
                : "text-zinc-600 cursor-not-allowed"
            )}
            title={`Add reference images (${uploadedImages.length}/5)`}
          >
            <ImageIcon size={16} />
          </button>
          
          {/* Send button */}
          <button
            onClick={handleSubmit}
            disabled={(!input.trim() && uploadedImages.length === 0) || disabled || isUploading}
            className={cn(
              "p-1.5 rounded-lg transition-all",
              (input.trim() || uploadedImages.length > 0) && !disabled && !isUploading
                ? "bg-[#6366F1] text-white hover:bg-[#818CF8]" 
                : "bg-[#1E1E2E] text-[#64748B] cursor-not-allowed"
            )}
          >
            {isUploading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
          </button>
        </div>
        
        <div className="absolute left-4 -bottom-6 flex gap-3 text-[10px] text-[#64748B]">
          <span>Cmd + Enter to send</span>
          {uploadedImages.length > 0 && (
            <span className="text-purple-400/70">
              {uploadedImages.length} image{uploadedImages.length > 1 ? 's' : ''} attached
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

