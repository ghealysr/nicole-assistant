'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import Image from 'next/image';
import { useImageGeneration, ImageVariant } from '@/lib/hooks/useImageGeneration';

interface AlphawaveImageStudioProps {
  isOpen: boolean;
  onClose: () => void;
  initialPrompt?: string;
  initialPreset?: string;
}

const MIN_WIDTH = 480;
const MAX_WIDTH_PERCENT = 0.5;

/**
 * Image Studio - Professional Image Generation Dashboard
 * 
 * Features:
 * - Preset selection with model-specific defaults
 * - Smart prompt enhancement toggle
 * - Batch generation (1-4 variants)
 * - Real-time SSE progress updates
 * - Variant gallery with favorites/ratings
 * - Job history sidebar
 * - Slash command integration
 */
export function AlphawaveImageStudio({ 
  isOpen, 
  onClose, 
  initialPrompt = '',
  initialPreset 
}: AlphawaveImageStudioProps) {
  const [width, setWidth] = useState(Math.min(window.innerWidth * 0.4, 600));
  const [isResizing, setIsResizing] = useState(false);
  const [activeTab, setActiveTab] = useState<'create' | 'history' | 'presets'>('create');
  
  // Generation state
  const [prompt, setPrompt] = useState(initialPrompt);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(initialPreset || null);
  const [selectedModel, setSelectedModel] = useState('recraft-v3');
  const [smartPrompt, setSmartPrompt] = useState(true);
  const [batchCount, setBatchCount] = useState(1);
  const [width_px, setWidthPx] = useState(1024);
  const [height_px, setHeightPx] = useState(1024);
  const [style, setStyle] = useState('');
  
  // Active job tracking
  const [activeJobId, setActiveJobId] = useState<number | null>(null);
  const [selectedVariant, setSelectedVariant] = useState<ImageVariant | null>(null);
  const [showEnhancedPrompt, setShowEnhancedPrompt] = useState(false);
  
  // Hooks
  const {
    jobs,
    variants,
    presets,
    models,
    progress,
    isGenerating,
    error,
    fetchJobs,
    fetchVariants,
    fetchPresets,
    fetchModels,
    createJob,
    toggleFavorite,
    rateVariant,
    startGeneration,
  } = useImageGeneration();

  const resizeRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  // Fetch initial data
  useEffect(() => {
    if (isOpen) {
      fetchPresets();
      fetchModels();
      fetchJobs();
    }
  }, [isOpen, fetchPresets, fetchModels, fetchJobs]);

  // Apply preset
  useEffect(() => {
    if (selectedPreset && presets.length > 0) {
      const preset = presets.find(p => p.id === parseInt(selectedPreset));
      if (preset) {
        setSelectedModel(preset.default_model);
        setWidthPx(preset.default_width);
        setHeightPx(preset.default_height);
        if (preset.default_style) setStyle(preset.default_style);
      }
    }
  }, [selectedPreset, presets]);

  // Handle resize
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isResizing) return;
    const diff = startXRef.current - e.clientX;
    const maxWidth = window.innerWidth * MAX_WIDTH_PERCENT;
    const newWidth = Math.max(MIN_WIDTH, Math.min(maxWidth, startWidthRef.current + diff));
    setWidth(newWidth);
  }, [isResizing]);

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
    document.body.classList.remove('resizing');
  }, []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  const startResize = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
    startXRef.current = e.clientX;
    startWidthRef.current = width;
    document.body.classList.add('resizing');
  };

  // Handle generation
  const handleGenerate = () => {
    if (!prompt.trim()) return;
    
    // Start SSE generation stream with all parameters
    startGeneration({
      prompt: prompt.trim(),
      model: selectedModel,
      width: width_px,
      height: height_px,
      style: style || undefined,
      batch_count: batchCount,
      enhance_prompt: smartPrompt,
    });
  };

  // Handle variant selection
  const handleVariantClick = (variant: ImageVariant) => {
    setSelectedVariant(variant);
  };

  // Download image
  const handleDownload = async (variant: ImageVariant) => {
    if (!variant.image_url) return;
    const link = document.createElement('a');
    link.href = variant.image_url;
    link.download = `nicole-image-${variant.id}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Get active job variants
  const activeJobVariants = activeJobId 
    ? variants.filter(v => v.job_id === activeJobId)
    : [];

  // Render aspect ratio selector
  const aspectRatios = [
    { label: '1:1', width: 1024, height: 1024 },
    { label: '16:9', width: 1920, height: 1080 },
    { label: '9:16', width: 1080, height: 1920 },
    { label: '4:3', width: 1365, height: 1024 },
    { label: '3:4', width: 1024, height: 1365 },
  ];

  return (
    <aside 
      className={`img-studio-panel ${isOpen ? 'img-studio-open' : ''}`}
      style={{ width: isOpen ? width : 0 }}
    >
      {/* Resize handle */}
      <div 
        ref={resizeRef}
        className={`img-studio-resize-handle ${isResizing ? 'img-dragging' : ''}`}
        onMouseDown={startResize}
      />
      
      <div className="img-studio-inner" style={{ width, minWidth: width }}>
        {/* Header */}
        <div className="img-studio-header">
          <div className="img-studio-header-left">
            <div className="img-studio-icon">
              <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <path d="M21 15l-5-5L5 21"/>
              </svg>
            </div>
            <div className="img-studio-titles">
              <span className="img-studio-title">Image Studio</span>
              <span className="img-studio-subtitle">
                {isGenerating ? 'Generating...' : 'Ready'}
              </span>
            </div>
          </div>
          <button className="img-studio-close-btn" onClick={onClose}>
            <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        {/* Tabs */}
        <div className="img-studio-tabs">
          {(['create', 'history', 'presets'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`img-studio-tab ${activeTab === tab ? 'img-tab-active' : ''}`}
            >
              {tab === 'create' && (
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} className="w-4 h-4">
                  <path d="M12 5v14M5 12h14"/>
                </svg>
              )}
              {tab === 'history' && (
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} className="w-4 h-4">
                  <circle cx="12" cy="12" r="10"/>
                  <polyline points="12 6 12 12 16 14"/>
                </svg>
              )}
              {tab === 'presets' && (
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2} className="w-4 h-4">
                  <rect x="3" y="3" width="7" height="7"/>
                  <rect x="14" y="3" width="7" height="7"/>
                  <rect x="14" y="14" width="7" height="7"/>
                  <rect x="3" y="14" width="7" height="7"/>
                </svg>
              )}
              <span>{tab.charAt(0).toUpperCase() + tab.slice(1)}</span>
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="img-studio-content">
          {/* Error Banner */}
          {error && (
            <div className="img-error-banner">
              <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              <span>{error}</span>
            </div>
          )}

          {/* Create Tab */}
          {activeTab === 'create' && (
            <div className="img-create-tab">
              {/* Preset Selector */}
              <div className="img-form-group">
                <label className="img-label">
                  <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                  </svg>
                  Preset
                </label>
                <select
                  value={selectedPreset || ''}
                  onChange={(e) => setSelectedPreset(e.target.value || null)}
                  className="img-select"
                >
                  <option value="">Custom</option>
                  {presets.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Model Selector */}
              <div className="img-form-group">
                <label className="img-label">
                  <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                  </svg>
                  Model
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="img-select"
                >
                  {models.map((model) => (
                    <option key={model.key} value={model.key}>
                      {model.name} (${model.cost_per_image.toFixed(3)})
                    </option>
                  ))}
                </select>
              </div>

              {/* Prompt Input */}
              <div className="img-form-group">
                <div className="img-label-row">
                  <label className="img-label">
                    <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                    Prompt
                  </label>
                  <button
                    onClick={() => setSmartPrompt(!smartPrompt)}
                    className={`img-toggle-btn ${smartPrompt ? 'img-toggle-active' : ''}`}
                    title="Smart Prompt Enhancement"
                  >
                    <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                      <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                      <path d="M2 17l10 5 10-5"/>
                      <path d="M2 12l10 5 10-5"/>
                    </svg>
                    <span>Enhance</span>
                  </button>
                </div>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe the image you want to create..."
                  className="img-textarea"
                  rows={4}
                />
                {smartPrompt && (
                  <div className="img-enhance-hint">
                    ✨ Claude will enhance your prompt for better results
                  </div>
                )}
              </div>

              {/* Aspect Ratio */}
              <div className="img-form-group">
                <label className="img-label">
                  <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                    <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
                  </svg>
                  Aspect Ratio
                </label>
                <div className="img-aspect-grid">
                  {aspectRatios.map((ratio) => (
                    <button
                      key={ratio.label}
                      onClick={() => {
                        setWidthPx(ratio.width);
                        setHeightPx(ratio.height);
                      }}
                      className={`img-aspect-btn ${
                        width_px === ratio.width && height_px === ratio.height
                          ? 'img-aspect-active'
                          : ''
                      }`}
                    >
                      {ratio.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Style (optional) */}
              <div className="img-form-group">
                <label className="img-label">
                  <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                    <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>
                  </svg>
                  Style (optional)
                </label>
                <input
                  type="text"
                  value={style}
                  onChange={(e) => setStyle(e.target.value)}
                  placeholder="e.g., photorealistic, digital_illustration, vector"
                  className="img-input"
                />
              </div>

              {/* Batch Count */}
              <div className="img-form-group">
                <label className="img-label">
                  <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                    <rect x="3" y="3" width="7" height="7"/>
                    <rect x="14" y="3" width="7" height="7"/>
                    <rect x="14" y="14" width="7" height="7"/>
                    <rect x="3" y="14" width="7" height="7"/>
                  </svg>
                  Variants
                </label>
                <div className="img-batch-grid">
                  {[1, 2, 3, 4].map((count) => (
                    <button
                      key={count}
                      onClick={() => setBatchCount(count)}
                      className={`img-batch-btn ${
                        batchCount === count ? 'img-batch-active' : ''
                      }`}
                    >
                      {count}
                    </button>
                  ))}
                </div>
              </div>

              {/* Generate Button */}
              <button
                onClick={handleGenerate}
                disabled={isGenerating || !prompt.trim()}
                className="img-generate-btn"
              >
                {isGenerating ? (
                  <>
                    <span className="img-spinner" />
                    <span>Generating...</span>
                  </>
                ) : (
                  <>
                    <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
                    </svg>
                    <span>Generate {batchCount > 1 ? `${batchCount} Images` : 'Image'}</span>
                  </>
                )}
              </button>

              {/* Progress */}
              {isGenerating && progress && (
                <div className="img-progress-card">
                  <div className="img-progress-header">
                    <span>Generating variant {progress.variant_index + 1} of {progress.total_variants}</span>
                    <span>{progress.progress}%</span>
                  </div>
                  <div className="img-progress-bar">
                    <div 
                      className="img-progress-fill" 
                      style={{ width: `${progress.progress}%` }}
                    />
                  </div>
                  <div className="img-progress-status">
                    {progress.status === 'enhancing_prompt' && '✨ Enhancing prompt...'}
                    {progress.status === 'generating' && '🎨 Creating image...'}
                    {progress.status === 'uploading' && '📤 Uploading...'}
                    {progress.status === 'complete' && '✅ Complete!'}
                    {progress.status === 'failed' && `❌ Error: ${progress.error}`}
                  </div>
                </div>
              )}

              {/* Variants Gallery */}
              {activeJobVariants.length > 0 && (
                <div className="img-variants-section">
                  <h3 className="img-section-title">Results</h3>
                  <div className="img-variants-grid">
                    {activeJobVariants.map((variant) => (
                      <div
                        key={variant.id}
                        className={`img-variant-card ${
                          selectedVariant?.id === variant.id ? 'img-variant-selected' : ''
                        }`}
                        onClick={() => handleVariantClick(variant)}
                      >
                        {variant.image_url ? (
                          <Image
                            src={variant.image_url}
                            alt={`Variant ${variant.variant_number}`}
                            className="img-variant-image"
                            fill
                            unoptimized
                          />
                        ) : variant.status === 'generating' ? (
                          <div className="img-variant-loading">
                            <span className="img-spinner-lg" />
                          </div>
                        ) : (
                          <div className="img-variant-error">
                            <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                              <circle cx="12" cy="12" r="10"/>
                              <line x1="12" y1="8" x2="12" y2="12"/>
                              <line x1="12" y1="16" x2="12.01" y2="16"/>
                            </svg>
                          </div>
                        )}
                        <div className="img-variant-actions">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleFavorite(variant.id);
                            }}
                            className={`img-action-btn ${variant.is_favorite ? 'img-favorited' : ''}`}
                            title="Favorite"
                          >
                            <svg viewBox="0 0 24 24" fill={variant.is_favorite ? 'currentColor' : 'none'} strokeWidth={2}>
                              <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                            </svg>
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDownload(variant);
                            }}
                            className="img-action-btn"
                            title="Download"
                          >
                            <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                              <polyline points="7 10 12 15 17 10"/>
                              <line x1="12" y1="15" x2="12" y2="3"/>
                            </svg>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* History Tab */}
          {activeTab === 'history' && (
            <div className="img-history-tab">
              {jobs.length === 0 ? (
                <div className="img-empty-state">
                  <svg viewBox="0 0 24 24" fill="none" strokeWidth={1.5}>
                    <rect x="3" y="3" width="18" height="18" rx="2"/>
                    <circle cx="8.5" cy="8.5" r="1.5"/>
                    <path d="M21 15l-5-5L5 21"/>
                  </svg>
                  <p>No images generated yet</p>
                  <span>Create your first image to see it here</span>
                </div>
              ) : (
                <div className="img-jobs-list">
                  {jobs.map((job) => (
                    <div
                      key={job.id}
                      className={`img-job-card ${activeJobId === job.id ? 'img-job-selected' : ''}`}
                      onClick={() => {
                        setActiveJobId(job.id);
                        fetchVariants(job.id);
                      }}
                    >
                      <div className="img-job-header">
                        <span className={`img-job-status img-status-${job.status}`}>
                          {job.status}
                        </span>
                        <span className="img-job-date">
                          {new Date(job.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="img-job-prompt">{job.original_prompt}</p>
                      <div className="img-job-meta">
                        <span>{job.model}</span>
                        <span>•</span>
                        <span>{job.width}×{job.height}</span>
                        <span>•</span>
                        <span>{job.batch_count} variant{job.batch_count > 1 ? 's' : ''}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Presets Tab */}
          {activeTab === 'presets' && (
            <div className="img-presets-tab">
              <div className="img-presets-grid">
                {presets.map((preset) => (
                  <div
                    key={preset.id}
                    className={`img-preset-card ${
                      selectedPreset === String(preset.id) ? 'img-preset-selected' : ''
                    }`}
                    onClick={() => {
                      setSelectedPreset(String(preset.id));
                      setActiveTab('create');
                    }}
                  >
                    <div className="img-preset-icon">
                      {preset.name === 'Logo' && '🎨'}
                      {preset.name === 'Hero Banner' && '🖼️'}
                      {preset.name === 'Social Post' && '📱'}
                      {preset.name === 'Poster' && '📰'}
                      {preset.name === 'Thumbnail' && '🎬'}
                      {!['Logo', 'Hero Banner', 'Social Post', 'Poster', 'Thumbnail'].includes(preset.name) && '✨'}
                    </div>
                    <div className="img-preset-info">
                      <h4>{preset.name}</h4>
                      <p>{preset.description || 'No description'}</p>
                      <span className="img-preset-spec">
                        {preset.default_width}×{preset.default_height}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="img-studio-footer">
          <div className="img-footer-stats">
            <span>Jobs: {jobs.length}</span>
            <span>•</span>
            <span>Images: {variants.length}</span>
          </div>
        </div>
      </div>

      {/* Selected Variant Modal */}
      {selectedVariant && (
        <div className="img-modal-overlay" onClick={() => setSelectedVariant(null)}>
          <div className="img-modal" onClick={(e) => e.stopPropagation()}>
            <button className="img-modal-close" onClick={() => setSelectedVariant(null)}>
              <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                <path d="M18 6L6 18M6 6l12 12"/>
              </svg>
            </button>
            {selectedVariant.image_url && (
              <Image
                src={selectedVariant.image_url}
                alt="Full size preview"
                className="img-modal-image"
                width={1024}
                height={1024}
                unoptimized
                style={{ objectFit: 'contain', maxHeight: '70vh', width: 'auto', height: 'auto' }}
              />
            )}
            <div className="img-modal-actions">
              <button
                onClick={() => toggleFavorite(selectedVariant.id)}
                className={`img-modal-btn ${selectedVariant.is_favorite ? 'img-modal-favorited' : ''}`}
              >
                <svg viewBox="0 0 24 24" fill={selectedVariant.is_favorite ? 'currentColor' : 'none'} strokeWidth={2}>
                  <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                </svg>
                <span>{selectedVariant.is_favorite ? 'Favorited' : 'Favorite'}</span>
              </button>
              <button onClick={() => handleDownload(selectedVariant)} className="img-modal-btn img-modal-download">
                <svg viewBox="0 0 24 24" fill="none" strokeWidth={2}>
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                <span>Download</span>
              </button>
              <div className="img-rating">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    onClick={() => rateVariant(selectedVariant.id, star)}
                    className={`img-star ${(selectedVariant.user_rating || 0) >= star ? 'img-star-filled' : ''}`}
                  >
                    ★
                  </button>
                ))}
              </div>
            </div>
            {selectedVariant.enhanced_prompt && (
              <div className="img-modal-enhanced">
                <button
                  onClick={() => setShowEnhancedPrompt(!showEnhancedPrompt)}
                  className="img-enhanced-toggle"
                >
                  {showEnhancedPrompt ? '▼' : '▶'} Enhanced Prompt
                </button>
                {showEnhancedPrompt && (
                  <p className="img-enhanced-text">{selectedVariant.enhanced_prompt}</p>
                )}
              </div>
            )}
            <div className="img-modal-stats">
              <span>Model: {selectedVariant.model_used}</span>
              <span>Generation: {selectedVariant.generation_time_ms}ms</span>
              <span>Cost: ${selectedVariant.cost?.toFixed(4)}</span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}

