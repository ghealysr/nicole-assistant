'use client';

import { useState, useRef, useEffect } from 'react';

/**
 * Props for AlphawaveChatInput.
 */
interface AlphawaveChatInputProps {
  onSendMessage: (content: string) => void;
  isLoading: boolean;
}

type ModelType = 'Sonnet 4.5' | 'Opus 4.5' | 'Haiku 4.5';

/**
 * Chat input component for Nicole V7.
 * Matches the HTML design with tool buttons, model selector, and rounded input box.
 */
export function AlphawaveChatInput({ onSendMessage, isLoading }: AlphawaveChatInputProps) {
  const [content, setContent] = useState('');
  const [selectedModel, setSelectedModel] = useState<ModelType>('Sonnet 4.5');
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<Array<{id: string, name: string}>>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const modelMenuRef = useRef<HTMLDivElement>(null);

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
   * Handles form submission to send the message.
   */
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (content.trim() && !isLoading) {
      onSendMessage(content.trim());
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
   * Simulates adding a file (placeholder).
   */
  const addFile = () => {
    if (pendingFiles.length >= 5) return;
    setPendingFiles([...pendingFiles, { 
      id: Date.now().toString(), 
      name: `document-${pendingFiles.length + 1}.pdf` 
    }]);
  };

  /**
   * Removes a pending file.
   */
  const removeFile = (id: string) => {
    setPendingFiles(pendingFiles.filter(f => f.id !== id));
  };

  return (
    <div className="bg-[#F5F4ED] px-6 py-4 pb-6 shrink-0">
      <div className="max-w-[800px] mx-auto">
        {/* Pending files */}
        {pendingFiles.length > 0 && (
          <div className="flex gap-2 flex-wrap mb-3">
            {pendingFiles.map(file => (
              <div key={file.id} className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#d8d7cc] bg-white text-sm text-[#374151]">
                <span>📄</span>
                <span>{file.name}</span>
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
        
        {/* Input box */}
        <form onSubmit={handleSubmit} className="input-box">
          <textarea
            ref={textareaRef}
            className="input-textarea"
            placeholder="Message Nicole..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
          />
          
          <div className="flex items-center justify-between mt-3">
            {/* Tool buttons */}
            <div className="flex gap-1">
              <button type="button" className="tool-btn" onClick={addFile} title="Attach file">
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
                disabled={!content.trim() || isLoading}
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
