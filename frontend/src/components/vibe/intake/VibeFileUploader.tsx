import React, { useCallback, useState } from 'react';
import { useDropzone, type DropzoneOptions } from 'react-dropzone';
import { UploadCloud, X, Loader2 } from 'lucide-react';

interface VibeFileUploaderProps {
  onUploadComplete: (fileData: { url: string; filename: string; type: string; size: number; mimeType: string }) => void;
  maxFiles?: number;
  acceptedFileTypes?: Record<string, string[]>;
}

export function VibeFileUploader({ 
  onUploadComplete, 
  maxFiles = 5,
  acceptedFileTypes = {
    'image/*': ['.png', '.jpg', '.jpeg', '.webp', '.svg'],
    'application/pdf': ['.pdf'],
    'text/plain': ['.txt', '.md']
  }
}: VibeFileUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setError(null);
    if (acceptedFiles.length === 0) return;

    setUploading(true);
    
    // Process files sequentially
    for (const file of acceptedFiles) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('upload_preset', 'unsigned_preset'); // Replace with actual preset or use backend signing

        // NOTE: For Phase 1, without a secure backend proxy or signature endpoint,
        // we are mocking the upload success if no Cloudinary config is present on client.
        // In production, this MUST use a signed request or a backend proxy.
        
        const cloudName = process.env.NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME;
        if (!cloudName) {
           // Mock upload for dev/demo if config missing
           await new Promise(resolve => setTimeout(resolve, 1000));
           onUploadComplete({
             url: URL.createObjectURL(file), // Local preview URL
             filename: file.name,
             type: file.type.startsWith('image/') ? 'image' : 'document',
             size: file.size,
             mimeType: file.type
           });
           continue;
        }

        const response = await fetch(
          `https://api.cloudinary.com/v1_1/${cloudName}/auto/upload`,
          {
            method: 'POST',
            body: formData,
          }
        );

        if (!response.ok) {
          throw new Error('Upload failed');
        }

        const data = await response.json();
        
        onUploadComplete({
          url: data.secure_url,
          filename: file.name,
          type: data.resource_type,
          size: data.bytes,
          mimeType: file.type
        });

      } catch (err) {
        console.error('Upload error:', err);
        setError(`Failed to upload ${file.name}`);
      }
    }
    
    setUploading(false);
  }, [onUploadComplete]);

  const dropzoneOptions: DropzoneOptions = {
    onDrop,
    accept: acceptedFileTypes,
    maxFiles,
    disabled: uploading
  };
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone(dropzoneOptions);

  return (
    <div className="vibe-uploader">
      <div 
        {...getRootProps()} 
        className={`vibe-dropzone ${isDragActive ? 'active' : ''} ${uploading ? 'uploading' : ''}`}
      >
        <input {...getInputProps()} />
        
        {uploading ? (
          <div className="vibe-dropzone-content">
            <Loader2 className="animate-spin text-purple-500 mb-2" size={32} />
            <p>Uploading...</p>
          </div>
        ) : (
          <div className="vibe-dropzone-content">
            <UploadCloud className="text-gray-400 mb-2" size={32} />
            <p className="text-sm font-medium">Click to upload or drag and drop</p>
            <p className="text-xs text-gray-500 mt-1">
              Images, PDFs, or Text (max {maxFiles} files)
            </p>
          </div>
        )}
      </div>
      
      {error && (
        <div className="text-xs text-red-500 mt-2 flex items-center">
          <X size={12} className="mr-1" />
          {error}
        </div>
      )}
    </div>
  );
}

