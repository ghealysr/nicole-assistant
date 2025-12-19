"use client";

import { useState, useCallback, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { useImageGeneration } from '@/lib/hooks/useImageGeneration';
import { X, Upload, Sparkles, Image as ImageIcon, Trash2, Eye, Download, RefreshCw } from 'lucide-react';
import Image from 'next/image';

interface ReferenceImage {
  id: string;
  file: File;
  preview: string;
  inspirationNotes: string;
}

interface ModelSelection {
  slot: number;
  model: string;
}

interface ImageVariant {
  id: string;
  image_url?: string;
}

interface AlphawaveImageStudioProps {
  isOpen: boolean;
  onClose: () => void;
  initialPrompt?: string;
  initialPreset?: string;
}

export default function AlphawaveImageStudio({ 
  isOpen, 
  onClose, 
  initialPrompt = '',
  initialPreset // eslint-disable-line @typescript-eslint/no-unused-vars
}: AlphawaveImageStudioProps) {
  // State management
  const [prompt, setPrompt] = useState(initialPrompt);
  
  // TODO: Implement preset loading from initialPreset prop
  // This will load predefined generation configurations
  const [referenceImages, setReferenceImages] = useState<ReferenceImage[]>([]);
  const [imageCount, setImageCount] = useState(1);
  const [multiModelMode, setMultiModelMode] = useState(false);
  const [modelSlots, setModelSlots] = useState<ModelSelection[]>([
    { slot: 1, model: 'gemini_3_pro_image' }
  ]);
  const [singleModel, setSingleModel] = useState('gemini_3_pro_image');
  const [aspectRatio, setAspectRatio] = useState('16:9');
  const [resolution, setResolution] = useState('2K');
  const [nicoleInsights, setNicoleInsights] = useState<string | null>(null);
  const [selectedTab, setSelectedTab] = useState<'create' | 'history' | 'presets'>('create');
  
  const { 
    startGeneration, 
    isGenerating, 
    jobs, 
    models,
    fetchModels,
    fetchPresets,
    fetchJobs
  } = useImageGeneration();
  
  // Fetch data on mount
  useEffect(() => {
    fetchModels();
    fetchPresets();
    fetchJobs();
  }, [fetchModels, fetchPresets, fetchJobs]);
  
  // Reference image drag-and-drop
  const onDrop = useCallback((acceptedFiles: File[]) => {
    // Limit to 10 images total
    const remaining = 10 - referenceImages.length;
    const filesToAdd = acceptedFiles.slice(0, remaining);
    
    const newImages = filesToAdd.map(file => ({
      id: Math.random().toString(36).substring(7),
      file,
      preview: URL.createObjectURL(file),
      inspirationNotes: ''
    }));
    
    setReferenceImages(prev => [...prev, ...newImages]);
  }, [referenceImages.length]);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.webp', '.gif']
    },
    maxFiles: 10,
    multiple: true,
    disabled: referenceImages.length >= 10
  });
  
  // Remove reference image
  const removeReferenceImage = (id: string) => {
    setReferenceImages(prev => {
      const removed = prev.find(img => img.id === id);
      if (removed) URL.revokeObjectURL(removed.preview);
      return prev.filter(img => img.id !== id);
    });
  };
  
  // Update inspiration notes
  const updateInspirationNotes = (id: string, notes: string) => {
    setReferenceImages(prev =>
      prev.map(img => img.id === id ? { ...img, inspirationNotes: notes } : img)
    );
  };
  
  // Handle image count change
  const handleImageCountChange = (count: number) => {
    setImageCount(count);
    
    // Adjust model slots if in multi-model mode
    if (multiModelMode) {
      const newSlots: ModelSelection[] = [];
      for (let i = 1; i <= count; i++) {
        const existing = modelSlots.find(s => s.slot === i);
        newSlots.push(existing || { slot: i, model: 'gemini_3_pro_image' });
      }
      setModelSlots(newSlots);
    }
  };
  
  // Handle model slot change
  const updateModelSlot = (slot: number, model: string) => {
    setModelSlots(prev =>
      prev.map(s => s.slot === slot ? { ...s, model } : s)
    );
  };
  
  // Get Nicole's prompt improvement suggestions
  const getPromptSuggestions = async () => {
    // This would call Nicole's API to analyze the prompt and reference images
    // For now, show a placeholder
    setNicoleInsights("Analyzing your request and reference images to suggest improvements...");
    
    // Simulate API call
    setTimeout(() => {
      setNicoleInsights(
        "💡 **Nicole's Suggestions:**\n\n" +
        "1. Your prompt could be more specific about lighting. Consider adding 'soft natural lighting' or 'dramatic shadows'.\n" +
        "2. Based on your reference images, I detect a warm color palette. Mentioning 'warm sunset tones' would help.\n" +
        "3. For best text rendering, specify the exact text you want and the font style.\n" +
        "4. Consider requesting a specific resolution (2K or 4K) for professional use."
      );
    }, 2000);
  };
  
  // Convert aspect ratio and resolution to width/height
  const getImageDimensions = (aspectRatio: string, resolution: string): { width: number; height: number } => {
    const resolutionMap: Record<string, number> = {
      '1K': 1024,
      '2K': 2048,
      '4K': 4096
    };
    
    const baseSize = resolutionMap[resolution] || 2048;
    
    const ratios: Record<string, [number, number]> = {
      '1:1': [1, 1],
      '16:9': [16, 9],
      '9:16': [9, 16],
      '4:3': [4, 3],
      '3:4': [3, 4],
      '21:9': [21, 9]
    };
    
    const [w, h] = ratios[aspectRatio] || [1, 1];
    const scale = Math.sqrt((baseSize * baseSize) / (w * h));
    
    return {
      width: Math.round(w * scale),
      height: Math.round(h * scale)
    };
  };
  
  // Handle generation
  const handleGenerate = async () => {
    if (!prompt.trim()) {
      alert('Please enter a prompt');
      return;
    }
    
    try {
      const { width, height } = getImageDimensions(aspectRatio, resolution);
      
      // For now, use single model mode
      // TODO: Implement multi-model generation
      const params = {
        prompt,
        model: multiModelMode ? modelSlots[0].model : singleModel,
        width,
        height,
        batch_count: imageCount,
        enhance_prompt: true
      };
      
      // TODO: Handle reference images upload and inclusion
      // Reference images need to be uploaded to backend first
      
      await startGeneration(params);
      
    } catch (error) {
      console.error('[IMAGE_STUDIO] Generation failed:', error);
      alert('Generation failed. Please try again.');
    }
  };
  
  // Don't render if not open
  if (!isOpen) return null;
  
  return (
    <div className="h-full flex flex-col bg-[#0a0a0a] overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-[#333] bg-[#1a1a1a] px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-purple-400" />
              Advanced Image Studio
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              Multi-agent system • Gemini 3 Pro • GPT Image • FLUX • Ideogram • Seedream • Recraft
            </p>
          </div>
          
          {/* Tab Navigation and Close Button */}
          <div className="flex items-center gap-3">
            <div className="flex gap-2">
            {(['create', 'history', 'presets'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setSelectedTab(tab)}
                className={`px-4 py-2 rounded-lg font-medium transition-all ${
                  selectedTab === tab
                    ? 'bg-purple-600 text-white'
                    : 'bg-[#2a2a2a] text-gray-400 hover:bg-[#333] hover:text-white'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
            </div>
            
            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-[#2a2a2a] text-gray-400 hover:bg-red-600 hover:text-white transition-all"
              title="Close Image Studio"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
      
      {/* Main Content - Fully Scrollable */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-6 py-6 space-y-6">
          
          {selectedTab === 'create' && (
            <>
              {/* Prompt Input Section */}
              <div className="bg-[#1a1a1a] rounded-xl p-6 border border-[#333]">
                <label className="block text-sm font-medium text-gray-300 mb-3">
                  Describe what you want to create
                </label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="A cinematic scene of a futuristic city at sunset, with neon lights reflecting off wet streets..."
                  className="w-full bg-[#0a0a0a] border border-[#444] rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                  rows={4}
                />
                
                {/* Nicole's Insights */}
                {nicoleInsights && (
                  <div className="mt-4 bg-purple-900/20 border border-purple-500/30 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                      <Sparkles className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
                      <div className="flex-1">
                        <div className="text-sm text-gray-300 whitespace-pre-wrap">
                          {nicoleInsights}
                        </div>
                      </div>
                      <button
                        onClick={() => setNicoleInsights(null)}
                        className="text-gray-500 hover:text-white transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                )}
                
                {/* Ask Nicole Button */}
                <div className="mt-4 flex justify-end">
                  <button
                    onClick={getPromptSuggestions}
                    disabled={!prompt.trim() || isGenerating}
                    className="px-4 py-2 bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    <Sparkles className="w-4 h-4" />
                    Ask Nicole to Improve My Prompt
                  </button>
                </div>
              </div>
              
              {/* Reference Images Section */}
              <div className="bg-[#1a1a1a] rounded-xl p-6 border border-[#333]">
                <div className="flex items-center justify-between mb-4">
                  <label className="block text-sm font-medium text-gray-300">
                    Reference Images (Optional - Up to 10)
                  </label>
                  <span className="text-xs text-gray-500">
                    {referenceImages.length}/10 images
                  </span>
                </div>
                
                {/* Dropzone */}
                {referenceImages.length < 10 && (
                  <div
                    {...getRootProps()}
                    className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all ${
                      isDragActive
                        ? 'border-purple-500 bg-purple-500/10'
                        : 'border-[#444] hover:border-[#555] bg-[#0a0a0a]'
                    }`}
                  >
                    <input {...getInputProps()} />
                    <Upload className="w-12 h-12 text-gray-500 mx-auto mb-3" />
                    <p className="text-gray-400 mb-1">
                      {isDragActive ? 'Drop images here...' : 'Drag & drop images, or click to browse'}
                    </p>
                    <p className="text-xs text-gray-600">
                      PNG, JPG, WEBP up to 10MB each
                    </p>
                  </div>
                )}
                
                {/* Reference Image Grid */}
                {referenceImages.length > 0 && (
                  <div className="grid grid-cols-2 gap-4 mt-4">
                    {referenceImages.map((img, index) => (
                      <div
                        key={img.id}
                        className="bg-[#0a0a0a] border border-[#444] rounded-lg p-4 space-y-3"
                      >
                        {/* Image Preview */}
                        <div className="relative aspect-video rounded-lg overflow-hidden bg-[#1a1a1a]">
                          <Image
                            src={img.preview}
                            alt={`Reference ${index + 1}`}
                            fill
                            className="object-cover"
                          />
                          <button
                            onClick={() => removeReferenceImage(img.id)}
                            className="absolute top-2 right-2 bg-red-600 hover:bg-red-700 text-white rounded-full p-1.5 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                          <div className="absolute bottom-2 left-2 bg-black/70 text-white text-xs px-2 py-1 rounded">
                            Reference {index + 1}
                          </div>
                        </div>
                        
                        {/* Inspiration Notes */}
                        <div>
                          <label className="block text-xs font-medium text-gray-400 mb-2">
                            What should I take from this image?
                          </label>
                          <textarea
                            value={img.inspirationNotes}
                            onChange={(e) => updateInspirationNotes(img.id, e.target.value)}
                            placeholder="E.g., 'Use this color palette', 'Match this lighting style', 'Incorporate this composition'..."
                            className="w-full bg-[#1a1a1a] border border-[#555] rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-purple-500 resize-none"
                            rows={3}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              {/* Generation Settings */}
              <div className="bg-[#1a1a1a] rounded-xl p-6 border border-[#333] space-y-6">
                <h3 className="text-lg font-semibold text-white mb-4">Generation Settings</h3>
                
                {/* Image Count */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-3">
                    Number of Images
                  </label>
                  <div className="flex gap-2">
                    {[1, 2, 3, 4].map(count => (
                      <button
                        key={count}
                        onClick={() => handleImageCountChange(count)}
                        className={`flex-1 py-3 rounded-lg font-medium transition-all ${
                          imageCount === count
                            ? 'bg-purple-600 text-white'
                            : 'bg-[#2a2a2a] text-gray-400 hover:bg-[#333] hover:text-white'
                        }`}
                      >
                        {count}
                      </button>
                    ))}
                  </div>
                </div>
                
                {/* Multi-Model Toggle */}
                <div>
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={multiModelMode}
                      onChange={(e) => setMultiModelMode(e.target.checked)}
                      className="w-5 h-5 rounded bg-[#2a2a2a] border-[#444] text-purple-600 focus:ring-purple-500"
                    />
                    <span className="text-sm text-gray-300">
                      Use different model for each image (for testing/comparison)
                    </span>
                  </label>
                </div>
                
                {/* Model Selection */}
                {!multiModelMode ? (
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-3">
                      Model
                    </label>
                    <select
                      value={singleModel}
                      onChange={(e) => setSingleModel(e.target.value)}
                      className="w-full bg-[#2a2a2a] border border-[#444] rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                    >
                      {models.map(model => (
                        <option key={model.key} value={model.key}>
                          {model.name}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <label className="block text-sm font-medium text-gray-300 mb-3">
                      Model per Slot
                    </label>
                    {modelSlots.slice(0, imageCount).map(slot => (
                      <div key={slot.slot} className="flex items-center gap-3">
                        <span className="text-sm text-gray-400 w-16">Slot {slot.slot}:</span>
                        <select
                          value={slot.model}
                          onChange={(e) => updateModelSlot(slot.slot, e.target.value)}
                          className="flex-1 bg-[#2a2a2a] border border-[#444] rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                        >
                          {models.map(model => (
                            <option key={model.key} value={model.key}>
                              {model.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    ))}
                  </div>
                )}
                
                {/* Aspect Ratio & Resolution (for Gemini) */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-3">
                      Aspect Ratio
                    </label>
                    <select
                      value={aspectRatio}
                      onChange={(e) => setAspectRatio(e.target.value)}
                      className="w-full bg-[#2a2a2a] border border-[#444] rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="1:1">1:1 (Square)</option>
                      <option value="16:9">16:9 (Widescreen)</option>
                      <option value="9:16">9:16 (Portrait)</option>
                      <option value="4:3">4:3 (Standard)</option>
                      <option value="3:2">3:2 (Photo)</option>
                      <option value="21:9">21:9 (Ultrawide)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-3">
                      Resolution (Gemini only)
                    </label>
                    <select
                      value={resolution}
                      onChange={(e) => setResolution(e.target.value)}
                      className="w-full bg-[#2a2a2a] border border-[#444] rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                    >
                      <option value="1K">1K (Fast)</option>
                      <option value="2K">2K (Balanced)</option>
                      <option value="4K">4K (Maximum Quality)</option>
                    </select>
                  </div>
                </div>
              </div>
              
              {/* Generate Button */}
              <button
                onClick={handleGenerate}
                disabled={!prompt.trim() || isGenerating}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 disabled:from-gray-600 disabled:to-gray-700 text-white font-semibold py-4 rounded-xl transition-all disabled:cursor-not-allowed flex items-center justify-center gap-3"
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-5 h-5" />
                    Generate {imageCount > 1 ? `${imageCount} Images` : 'Image'}
                  </>
                )}
              </button>
              
              {/* Generation Results */}
              {jobs.length > 0 && jobs[0].status === 'completed' && (
                <div className="bg-[#1a1a1a] rounded-xl p-6 border border-[#333]">
                  <h3 className="text-lg font-semibold text-white mb-4">Generated Images</h3>
                  
                  <div className={`grid gap-4 ${
                    imageCount === 1 ? 'grid-cols-1' :
                    imageCount === 2 ? 'grid-cols-2' :
                    'grid-cols-2'
                  }`}>
                    {jobs[0].variants?.slice(0, imageCount).map((variant: ImageVariant, index: number) => (
                      <div
                        key={variant.id}
                        className="relative group rounded-lg overflow-hidden bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-500/30 p-1"
                      >
                        <div className="relative aspect-video bg-[#0a0a0a] rounded-lg overflow-hidden">
                          {variant.image_url ? (
                            <Image
                              src={variant.image_url}
                              alt={`Generated ${index + 1}`}
                              fill
                              className="object-contain"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <ImageIcon className="w-16 h-16 text-gray-700" />
                            </div>
                          )}
                          
                          {/* Overlay on Hover */}
                          <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                            <button className="bg-white/20 hover:bg-white/30 backdrop-blur-sm text-white rounded-lg p-3 transition-all">
                              <Eye className="w-5 h-5" />
                            </button>
                            <button className="bg-white/20 hover:bg-white/30 backdrop-blur-sm text-white rounded-lg p-3 transition-all">
                              <Download className="w-5 h-5" />
                            </button>
                          </div>
                        </div>
                        
                        {/* Model Badge */}
                        {multiModelMode && modelSlots[index] && (
                          <div className="absolute top-3 left-3 bg-black/70 backdrop-blur-sm text-white text-xs px-2 py-1 rounded">
                            {models.find(m => m.key === modelSlots[index].model)?.name || modelSlots[index].model}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
          
          {selectedTab === 'history' && (
            <div className="bg-[#1a1a1a] rounded-xl p-6 border border-[#333]">
              <h3 className="text-lg font-semibold text-white mb-4">Generation History</h3>
              {jobs.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <ImageIcon className="w-16 h-16 mx-auto mb-3 text-gray-700" />
                  <p>No generations yet</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {jobs.map(job => (
                    <div key={job.id} className="bg-[#0a0a0a] border border-[#444] rounded-lg p-4 hover:border-purple-500/50 transition-colors cursor-pointer">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <p className="text-white font-medium mb-1">{job.prompt}</p>
                          <p className="text-xs text-gray-500">
                            {new Date(job.created_at).toLocaleString()} • {job.model}
                          </p>
                        </div>
                        <div className={`px-2 py-1 rounded text-xs font-medium ${
                          job.status === 'completed' ? 'bg-green-900/30 text-green-400' :
                          job.status === 'failed' ? 'bg-red-900/30 text-red-400' :
                          'bg-yellow-900/30 text-yellow-400'
                        }`}>
                          {job.status}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          
          {selectedTab === 'presets' && (
            <div className="bg-[#1a1a1a] rounded-xl p-6 border border-[#333]">
              <h3 className="text-lg font-semibold text-white mb-4">Generation Presets</h3>
              <div className="text-center py-12 text-gray-500">
                <Sparkles className="w-16 h-16 mx-auto mb-3 text-gray-700" />
                <p>Presets coming soon</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
