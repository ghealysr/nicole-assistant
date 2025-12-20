'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Send, Image as ImageIcon, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useFazStore } from '@/lib/faz/store';
import { fazWS } from '@/lib/faz/websocket';
import { motion, AnimatePresence } from 'framer-motion';

interface ChatInputProps {
  onSend: (message: string, images?: File[]) => void;
  disabled?: boolean;
  placeholder?: string;
}

interface UploadedImage {
  file: File;
  preview: string;
  note: string;
}

export function ChatInput({ onSend, disabled, placeholder }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const { currentGate, setCurrentGate } = useFazStore();

  // Dismiss approval button when user starts typing
  const handleInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInput(value);
    
    // If user starts typing while there's a pending approval, dismiss it
    if (currentGate && value.length > 0) {
      // User is typing feedback instead of clicking approve
      // This will be treated as "not approved" - Nicole will ask again after addressing
      setCurrentGate(null);
    }
    
    // Auto-resize
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [currentGate, setCurrentGate]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if ((!input.trim() && uploadedImages.length === 0) || disabled) return;
    
    // If there are images, include them
    const files = uploadedImages.map(img => img.file);
    
    // Build message with image notes if any
    let fullMessage = input.trim();
    if (uploadedImages.length > 0) {
      const imageNotes = uploadedImages
        .filter(img => img.note.trim())
        .map((img, i) => `[Image ${i + 1}]: ${img.note}`)
        .join('\n');
      
      if (imageNotes) {
        fullMessage = `${fullMessage}\n\n---\n**Reference Images:**\n${imageNotes}`;
      }
    }
    
    onSend(fullMessage, files.length > 0 ? files : undefined);
    
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
    
    // Limit to 10 images total
    const remaining = 10 - uploadedImages.length;
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
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2"
          >
            {uploadedImages.map((img, idx) => (
              <motion.div
                key={img.preview}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="relative group"
              >
                <div className="relative rounded-lg overflow-hidden border border-zinc-700 bg-zinc-800">
                  <img
                    src={img.preview}
                    alt={`Reference ${idx + 1}`}
                    className="w-full h-20 object-cover"
                  />
                  <button
                    onClick={() => removeImage(idx)}
                    className="absolute top-1 right-1 p-1 bg-black/60 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="w-3 h-3 text-white" />
                  </button>
                </div>
                <input
                  type="text"
                  placeholder="What do you like?"
                  value={img.note}
                  onChange={(e) => updateImageNote(idx, e.target.value)}
                  className="mt-1 w-full px-2 py-1 text-xs bg-zinc-800 border border-zinc-700 rounded text-zinc-300 placeholder:text-zinc-500 focus:outline-none focus:border-orange-500/50"
                />
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Main input */}
      <div className="relative bg-[#12121A] border border-zinc-700/50 rounded-xl focus-within:border-orange-500/50 transition-colors">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={placeholder || "Describe your vision, ask questions, or provide feedback..."}
          className="w-full bg-transparent text-[#F1F5F9] placeholder-[#64748B] p-4 pr-24 text-sm resize-none outline-none min-h-[50px] max-h-[200px]"
          rows={1}
          disabled={disabled}
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
            disabled={disabled || uploadedImages.length >= 10}
            className={cn(
              "p-1.5 rounded-lg transition-all",
              uploadedImages.length < 10 && !disabled
                ? "text-zinc-400 hover:text-orange-400 hover:bg-zinc-800"
                : "text-zinc-600 cursor-not-allowed"
            )}
            title={`Add reference images (${uploadedImages.length}/10)`}
          >
            <ImageIcon size={16} />
          </button>
          
          {/* Send button */}
          <button
            onClick={handleSubmit}
            disabled={(!input.trim() && uploadedImages.length === 0) || disabled}
            className={cn(
              "p-1.5 rounded-lg transition-all",
              (input.trim() || uploadedImages.length > 0) && !disabled
                ? "bg-orange-500 text-white hover:bg-orange-400" 
                : "bg-zinc-800 text-zinc-600 cursor-not-allowed"
            )}
          >
            {isUploading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Send size={16} />
            )}
          </button>
        </div>
      </div>
      
      {/* Hint */}
      <div className="flex items-center justify-between px-1">
        <span className="text-[10px] text-zinc-600">
          Cmd/Ctrl + Enter to send
        </span>
        {uploadedImages.length > 0 && (
          <span className="text-[10px] text-orange-400/70">
            {uploadedImages.length} image{uploadedImages.length > 1 ? 's' : ''} attached
          </span>
        )}
      </div>
    </div>
  );
}

export default ChatInput;
