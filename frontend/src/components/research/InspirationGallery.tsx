'use client';

/**
 * InspirationGallery - Design inspiration grid with feedback system
 * 
 * For Vibe mode - displays website design inspirations with:
 * - Screenshot previews
 * - Color palette extraction
 * - Design element tags
 * - Like/dislike feedback per element
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { InspirationImage, ImageFeedback } from '@/lib/hooks/useResearch';

interface InspirationGalleryProps {
  images: InspirationImage[];
  onFeedback: (feedback: ImageFeedback) => void;
}

interface InspirationDetailProps {
  image: InspirationImage;
  onClose: () => void;
  onFeedback: (feedback: ImageFeedback) => void;
}

// Element feedback row
const ElementFeedbackRow = ({
  element,
  status,
  onStatusChange,
}: {
  element: string;
  status: 'neutral' | 'liked' | 'disliked';
  onStatusChange: (status: 'neutral' | 'liked' | 'disliked') => void;
}) => (
  <div className="inspiration-element-row">
    <span className="element-name">{element}</span>
    <div className="element-actions">
      <button
        className={`element-btn like ${status === 'liked' ? 'active' : ''}`}
        onClick={() => onStatusChange(status === 'liked' ? 'neutral' : 'liked')}
        title="Like this element"
      >
        <svg viewBox="0 0 24 24" fill={status === 'liked' ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={2}>
          <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
        </svg>
      </button>
      <button
        className={`element-btn dislike ${status === 'disliked' ? 'active' : ''}`}
        onClick={() => onStatusChange(status === 'disliked' ? 'neutral' : 'disliked')}
        title="Dislike this element"
      >
        <svg viewBox="0 0 24 24" fill={status === 'disliked' ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={2}>
          <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
        </svg>
      </button>
    </div>
  </div>
);

// Inspiration Card
const InspirationCard = ({
  image,
  onClick,
}: {
  image: InspirationImage;
  onClick: () => void;
}) => (
  <motion.div
    className="inspiration-card"
    whileHover={{ scale: 1.02, y: -4 }}
    whileTap={{ scale: 0.98 }}
    onClick={onClick}
    layout
  >
    <div className="inspiration-card-image">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={image.screenshot_url || image.url}
        alt={`Inspiration from ${image.source_site || 'website'}`}
        loading="lazy"
      />
      <div className="inspiration-card-overlay">
        <span className="inspiration-view-btn">View Details</span>
      </div>
    </div>
    
    <div className="inspiration-card-info">
      <h4 className="inspiration-card-site">{image.source_site || image.title || 'Design'}</h4>
      <p className="inspiration-card-pattern">{image.design_elements?.layout_pattern || 'Website'}</p>
      
      {/* Color palette preview */}
      <div className="inspiration-card-colors">
        {(image.design_elements?.colors || []).slice(0, 5).map((color, i) => (
          <div
            key={i}
            className="inspiration-color-dot"
            style={{ backgroundColor: color }}
            title={color}
          />
        ))}
      </div>
    </div>
  </motion.div>
);

// Detail Modal
const InspirationDetail = ({ image, onClose, onFeedback }: InspirationDetailProps) => {
  const [feedback, setFeedback] = useState<Partial<ImageFeedback>>({
    imageId: image.id || image.url,
    likedElements: [],
    dislikedElements: [],
    comments: '',
  });

  const designElements = [
    ...(image.design_elements?.notable_features || []),
    image.design_elements?.typography_style,
    image.design_elements?.layout_pattern,
  ].filter(Boolean) as string[];

  const getElementStatus = (element: string): 'neutral' | 'liked' | 'disliked' => {
    if (feedback.likedElements?.includes(element)) return 'liked';
    if (feedback.dislikedElements?.includes(element)) return 'disliked';
    return 'neutral';
  };

  const handleElementStatus = (element: string, status: 'neutral' | 'liked' | 'disliked') => {
    setFeedback(prev => {
      const newLiked = (prev.likedElements || []).filter(e => e !== element);
      const newDisliked = (prev.dislikedElements || []).filter(e => e !== element);
      
      if (status === 'liked') newLiked.push(element);
      if (status === 'disliked') newDisliked.push(element);
      
      return {
        ...prev,
        likedElements: newLiked,
        dislikedElements: newDisliked,
      };
    });
  };

  const handleSubmit = (liked: boolean) => {
    onFeedback({
      image_url: image.url,
      liked,
      notes: feedback.comments || '',
    });
    onClose();
  };

  return (
    <motion.div
      className="inspiration-detail-backdrop"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.div
        className="inspiration-detail-modal"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Image side */}
        <div className="inspiration-detail-image">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={image.screenshot_url || image.url}
            alt={`Design from ${image.source_site || 'website'}`}
          />
        </div>

        {/* Feedback side */}
        <div className="inspiration-detail-content">
          <h3 className="inspiration-detail-title">{image.source_site || image.title || 'Design'}</h3>
          
          <a
            href={image.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inspiration-detail-link"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
            View original
          </a>

          <p className="inspiration-detail-notes">{image.relevance_notes}</p>

          {/* Color palette */}
          <div className="inspiration-detail-section">
            <h4>Color Palette</h4>
            <div className="inspiration-detail-colors">
              {image.design_elements.colors.map((color, i) => (
                <div key={i} className="inspiration-color-chip">
                  <div
                    className="color-swatch"
                    style={{ backgroundColor: color }}
                  />
                  <span className="color-code">{color}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Element feedback */}
          <div className="inspiration-detail-section">
            <h4>What do you think of these elements?</h4>
            <div className="inspiration-elements-list">
              {designElements.map((element) => (
                <ElementFeedbackRow
                  key={element}
                  element={element}
                  status={getElementStatus(element)}
                  onStatusChange={(status) => handleElementStatus(element, status)}
                />
              ))}
            </div>
          </div>

          {/* Comments */}
          <div className="inspiration-detail-section">
            <h4>Additional thoughts</h4>
            <textarea
              value={feedback.comments}
              onChange={(e) => setFeedback(prev => ({ ...prev, comments: e.target.value }))}
              placeholder="What specifically catches your eye? What would you change?"
              className="inspiration-comments"
            />
          </div>

          {/* Actions */}
          <div className="inspiration-detail-actions">
            <button
              className="inspiration-action-btn dismiss"
              onClick={() => handleSubmit(false)}
            >
              Not for this project
            </button>
            <button
              className="inspiration-action-btn save"
              onClick={() => handleSubmit(true)}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z" />
              </svg>
              Save inspiration
            </button>
          </div>
        </div>

        {/* Close button */}
        <button className="inspiration-detail-close" onClick={onClose}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </motion.div>
    </motion.div>
  );
};

export function InspirationGallery({ images, onFeedback }: InspirationGalleryProps) {
  const [selectedImage, setSelectedImage] = useState<InspirationImage | null>(null);

  if (!images || images.length === 0) {
    return (
      <div className="inspiration-empty">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
          <circle cx="8.5" cy="8.5" r="1.5" />
          <polyline points="21 15 16 10 5 21" />
        </svg>
        <p>No design inspirations found. Try a different search.</p>
      </div>
    );
  }

  return (
    <>
      <motion.div
        className="inspiration-gallery"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        {images.map((image, index) => (
          <motion.div
            key={image.id || index}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <InspirationCard
              image={image}
              onClick={() => setSelectedImage(image)}
            />
          </motion.div>
        ))}
      </motion.div>

      <AnimatePresence>
        {selectedImage && (
          <InspirationDetail
            image={selectedImage}
            onClose={() => setSelectedImage(null)}
            onFeedback={onFeedback}
          />
        )}
      </AnimatePresence>
    </>
  );
}

export default InspirationGallery;

