'use client';

/**
 * InspirationImageManager Component
 * 
 * Manages up to 5 inspiration images with:
 * - Image thumbnails with preview
 * - Editable text annotation for each image
 * - Save/Edit/Delete controls per image
 * - Images and annotations are included in Nicole's planning context
 * 
 * Anthropic Quality Standards:
 * - Type-safe interface with full TypeScript
 * - Clean separation of concerns
 * - Accessible UI with ARIA labels
 * - Optimized rendering with React.memo
 */

import React, { useState, useRef, useCallback, memo } from 'react';
import { cn } from '@/lib/utils';
import { 
  X, Edit2, Check, Image as ImageIcon, Plus, Lock
} from 'lucide-react';
import type { InspirationImage, InspirationAnalysis } from '@/lib/enjineer/store';

// Re-export types for convenience (consumers can import from either location)
export type { InspirationImage, InspirationAnalysis };

// Maximum number of inspiration images allowed
const MAX_INSPIRATION_IMAGES = 5;

interface InspirationImageManagerProps {
  images: InspirationImage[];
  onImagesChange: (images: InspirationImage[]) => void;
  disabled?: boolean;
  className?: string;
}

/**
 * Single inspiration card with thumbnail, annotation, and controls
 */
const InspirationCard = memo(function InspirationCard({
  image,
  onUpdate,
  onDelete,
  disabled,
}: {
  image: InspirationImage;
  onUpdate: (updates: Partial<InspirationImage>) => void;
  onDelete: () => void;
  disabled?: boolean;
}) {
  const [isEditing, setIsEditing] = useState(!image.isLocked && !image.annotation);
  const [editText, setEditText] = useState(image.annotation);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus textarea when editing starts
  React.useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isEditing]);

  const handleSave = useCallback(() => {
    onUpdate({ annotation: editText, isLocked: true });
    setIsEditing(false);
  }, [editText, onUpdate]);

  const handleEdit = useCallback(() => {
    onUpdate({ isLocked: false });
    setIsEditing(true);
  }, [onUpdate]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSave();
    }
    if (e.key === 'Escape') {
      setEditText(image.annotation);
      if (image.annotation) {
        setIsEditing(false);
      }
    }
  }, [handleSave, image.annotation]);

  return (
    <div 
      className={cn(
        "group relative flex gap-3 p-3 bg-[#12121A] border rounded-xl transition-all",
        image.isLocked 
          ? "border-emerald-500/30 bg-emerald-500/5" 
          : "border-[#2D2D3A] hover:border-[#8B5CF6]/40"
      )}
    >
      {/* Thumbnail - Using native <img> because:
          1. previewUrl is a blob URL from URL.createObjectURL()
          2. Next.js Image requires known dimensions and remote patterns
          3. Blob URLs are local and don't benefit from Next.js optimization */}
      <div className="relative shrink-0">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={image.previewUrl}
          alt="Inspiration"
          className="w-16 h-16 object-cover rounded-lg border border-[#2D2D3A]"
        />
        {image.isLocked && (
          <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full flex items-center justify-center">
            <Lock size={8} className="text-white" />
          </div>
        )}
      </div>

      {/* Annotation Area */}
      <div className="flex-1 min-w-0">
        {isEditing ? (
          <textarea
            ref={textareaRef}
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe what inspires you about this image... (colors, layout, typography, style)"
            disabled={disabled}
            className="w-full h-16 text-xs bg-[#0A0A0F] border border-[#2D2D3A] rounded-lg px-2 py-1.5 text-[#F1F5F9] placeholder-[#64748B] resize-none focus:outline-none focus:border-[#8B5CF6] transition-colors"
            maxLength={500}
          />
        ) : (
          <div className="h-16 overflow-y-auto scrollbar-thin scrollbar-thumb-[#3E3E5E] scrollbar-track-transparent">
            <p className="text-xs text-[#94A3B8] leading-relaxed">
              {image.annotation || <span className="italic text-[#64748B]">No annotation</span>}
            </p>
          </div>
        )}

        {/* Controls Row */}
        <div className="flex items-center justify-between mt-1.5">
          <span className="text-[10px] text-[#64748B]">
            {image.isLocked ? 'Locked' : 'Editing'}
          </span>
          
          <div className="flex gap-1">
            {isEditing ? (
              <button
                onClick={handleSave}
                disabled={disabled}
                className="p-1 rounded bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors"
                title="Save (Cmd+Enter)"
                aria-label="Save annotation"
              >
                <Check size={12} />
              </button>
            ) : (
              <button
                onClick={handleEdit}
                disabled={disabled}
                className="p-1 rounded bg-[#1E1E2E] text-[#8B5CF6] hover:bg-[#2E2E3E] transition-colors"
                title="Edit annotation"
                aria-label="Edit annotation"
              >
                <Edit2 size={12} />
              </button>
            )}
            <button
              onClick={onDelete}
              disabled={disabled}
              className="p-1 rounded bg-[#1E1E2E] text-red-400 hover:bg-red-500/20 transition-colors opacity-0 group-hover:opacity-100"
              title="Remove image"
              aria-label="Remove inspiration image"
            >
              <X size={12} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
});

/**
 * Add Image Button - Triggers file selection
 */
const AddImageButton = memo(function AddImageButton({
  onClick,
  disabled,
  remainingSlots,
}: {
  onClick: () => void;
  disabled?: boolean;
  remainingSlots: number;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || remainingSlots <= 0}
      className={cn(
        "flex items-center gap-2 px-3 py-2 rounded-lg border border-dashed transition-all text-xs",
        remainingSlots > 0 && !disabled
          ? "border-[#8B5CF6]/40 text-[#8B5CF6] hover:border-[#8B5CF6] hover:bg-[#8B5CF6]/10 cursor-pointer"
          : "border-[#2D2D3A] text-[#64748B] cursor-not-allowed opacity-50"
      )}
      aria-label={`Add inspiration image (${remainingSlots} remaining)`}
    >
      <Plus size={14} />
      <span>Add Inspiration ({remainingSlots} left)</span>
    </button>
  );
});

/**
 * Main InspirationImageManager Component
 */
export function InspirationImageManager({
  images,
  onImagesChange,
  disabled = false,
  className,
}: InspirationImageManagerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const imageFiles = files.filter(f => f.type.startsWith('image/'));
    
    // Limit to remaining slots
    const remainingSlots = MAX_INSPIRATION_IMAGES - images.length;
    const filesToAdd = imageFiles.slice(0, remainingSlots);

    // Create new inspiration images
    const newImages: InspirationImage[] = filesToAdd.map(file => ({
      id: crypto.randomUUID(),
      file,
      previewUrl: URL.createObjectURL(file),
      annotation: '',
      isLocked: false,
    }));

    onImagesChange([...images, ...newImages]);
    e.target.value = ''; // Reset for same file selection
  }, [images, onImagesChange]);

  const handleUpdateImage = useCallback((id: string, updates: Partial<InspirationImage>) => {
    onImagesChange(
      images.map(img => img.id === id ? { ...img, ...updates } : img)
    );
  }, [images, onImagesChange]);

  const handleDeleteImage = useCallback((id: string) => {
    const imageToDelete = images.find(img => img.id === id);
    if (imageToDelete) {
      // Revoke object URL to prevent memory leaks
      URL.revokeObjectURL(imageToDelete.previewUrl);
    }
    onImagesChange(images.filter(img => img.id !== id));
  }, [images, onImagesChange]);

  const triggerFileInput = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const remainingSlots = MAX_INSPIRATION_IMAGES - images.length;

  // Don't render if no images and not enough context
  if (images.length === 0) {
    return (
      <div className={cn("px-4 py-2 border-t border-[#1E1E2E] bg-[#0A0A0F]", className)}>
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          onChange={handleFileSelect}
          className="hidden"
          aria-hidden="true"
        />
        
        {/* Add button when empty */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-[#64748B]">
            <ImageIcon size={14} className="text-[#8B5CF6]" />
            <span>Inspiration Images</span>
          </div>
          <AddImageButton 
            onClick={triggerFileInput} 
            disabled={disabled} 
            remainingSlots={remainingSlots}
          />
        </div>
      </div>
    );
  }

  return (
    <div className={cn("px-4 py-3 border-t border-[#1E1E2E] bg-[#0A0A0F]", className)}>
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        onChange={handleFileSelect}
        className="hidden"
        aria-hidden="true"
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 text-xs text-[#94A3B8]">
          <ImageIcon size={14} className="text-[#8B5CF6]" />
          <span className="font-medium">Inspiration Images</span>
          <span className="text-[#64748B]">({images.length}/{MAX_INSPIRATION_IMAGES})</span>
        </div>
        {remainingSlots > 0 && (
          <AddImageButton 
            onClick={triggerFileInput} 
            disabled={disabled} 
            remainingSlots={remainingSlots}
          />
        )}
      </div>

      {/* Image Cards */}
      <div className="space-y-2">
        {images.map(image => (
          <InspirationCard
            key={image.id}
            image={image}
            onUpdate={(updates) => handleUpdateImage(image.id, updates)}
            onDelete={() => handleDeleteImage(image.id)}
            disabled={disabled}
          />
        ))}
      </div>

      {/* Instructions */}
      <p className="text-[10px] text-[#64748B] mt-2">
        💡 Lock annotations to include them in Nicole&apos;s planning context
      </p>
    </div>
  );
}

/**
 * Utility: Convert InspirationImage to format for Nicole's API
 */
export async function prepareInspirationForAPI(images: InspirationImage[]): Promise<Array<{
  name: string;
  type: string;
  content: string;
  annotation: string;
  isLocked: boolean;
}>> {
  const prepared: Array<{
    name: string;
    type: string;
    content: string;
    annotation: string;
    isLocked: boolean;
  }> = [];

  for (const img of images) {
    if (img.isLocked) { // Only include locked (saved) images
      const base64 = await readFileAsBase64(img.file);
      prepared.push({
        name: img.file.name,
        type: img.file.type,
        content: base64,
        annotation: img.annotation,
        isLocked: img.isLocked,
      });
    }
  }

  return prepared;
}

/**
 * Utility: Read file as base64
 */
function readFileAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = (reader.result as string).split(',')[1] || '';
      resolve(base64);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
