'use client';

/**
 * Nicole's Enhanced Message Renderer
 * 
 * Parses Nicole's responses and renders them with appropriate UI components:
 * - Thinking blocks (collapsible step-by-step)
 * - Tables with styled headers
 * - Code blocks with syntax highlighting
 * - Note/suggestion cards
 * - File cards with download buttons
 * - Inline images (Cloudinary, Replicate, and other image URLs)
 * - Standard markdown formatting
 * 
 * Special block syntax (parsed from response):
 * - <thinking>...</thinking> - Renders ThinkingBox
 * - <note>...</note> - Renders NoteCard
 * - <file>...</file> - Renders FileCard
 * - Standard markdown tables - Renders StyledTable
 * - Image URLs (Cloudinary, etc.) - Renders inline images
 */

import React, { useMemo, useState } from 'react';
import Image from 'next/image';
import {
  ThinkingBox,
  FileCard,
  StyledTable,
  NoteCard,
  nicoleColors,
  type ThinkingStep,
} from './NicoleThinkingUI';

// ============================================================================
// TYPES
// ============================================================================

interface ParsedBlock {
  type: 'text' | 'thinking' | 'note' | 'file' | 'table' | 'code' | 'image';
  content: string;
  metadata?: Record<string, unknown>;
}

interface ImageBlockData {
  url: string;
  alt?: string;
  caption?: string;
}

interface ThinkingBlockData {
  steps: ThinkingStep[];
  summary?: string;
}

interface FileBlockData {
  filename: string;
  fileType: string;
  content?: string;
}

interface NoteBlockData {
  title?: string;
  iconType?: 'clock' | 'lightbulb' | 'info';
  content: string;
}

interface TableData {
  headers: string[];
  rows: string[][];
  [key: string]: unknown;
}

// ============================================================================
// PARSING FUNCTIONS
// ============================================================================

/**
 * Parse thinking block XML-like syntax
 * Format: <thinking steps="step1|step2|step3" summary="...">
 */
function parseThinkingBlock(content: string): ThinkingBlockData | null {
  const stepsMatch = content.match(/steps="([^"]+)"/);
  const summaryMatch = content.match(/summary="([^"]+)"/);
  
  if (!stepsMatch) return null;
  
  const stepTexts = stepsMatch[1].split('|');
  const steps: ThinkingStep[] = stepTexts.map((text) => ({
    description: text.trim(),
    status: 'complete' as const, // All steps complete when rendered in final response
    file: undefined,
  }));
  
  return {
    steps,
    summary: summaryMatch ? summaryMatch[1] : undefined,
  };
}

/**
 * Parse file block
 * Format: <file name="filename.ext" type="JSON">content</file>
 */
function parseFileBlock(content: string): FileBlockData | null {
  const nameMatch = content.match(/name="([^"]+)"/);
  const typeMatch = content.match(/type="([^"]+)"/);
  const contentMatch = content.match(/>([^<]*)</);
  
  if (!nameMatch) return null;
  
  return {
    filename: nameMatch[1],
    fileType: typeMatch ? typeMatch[1] : 'Text',
    content: contentMatch ? contentMatch[1].trim() : undefined,
  };
}

/**
 * Parse note block
 * Format: <note title="..." icon="lightbulb">content</note>
 */
function parseNoteBlock(content: string): NoteBlockData | null {
  const titleMatch = content.match(/title="([^"]+)"/);
  const iconMatch = content.match(/icon="([^"]+)"/);
  const contentMatch = content.match(/>([^<]*)</);
  
  return {
    title: titleMatch ? titleMatch[1] : undefined,
    iconType: iconMatch ? (iconMatch[1] as 'clock' | 'lightbulb' | 'info') : 'lightbulb',
    content: contentMatch ? contentMatch[1].trim() : content,
  };
}

/**
 * Parse markdown table
 */
function parseMarkdownTable(content: string): TableData | null {
  const lines = content.trim().split('\n');
  if (lines.length < 2) return null;
  
  // Check if it's a valid table (has | separators)
  if (!lines[0].includes('|')) return null;
  
  const parseRow = (line: string): string[] => {
    return line
      .split('|')
      .map(cell => cell.trim())
      .filter(cell => cell.length > 0);
  };
  
  const headers = parseRow(lines[0]);
  
  // Skip separator line (|---|---|)
  const dataStartIndex = lines[1].includes('-') ? 2 : 1;
  
  const rows = lines.slice(dataStartIndex).map(parseRow);
  
  return { headers, rows };
}

/**
 * Detect if a URL is an image URL
 * Supports: Cloudinary, Replicate, common image extensions
 */
function isImageUrl(url: string): boolean {
  // Cloudinary URLs
  if (url.includes('res.cloudinary.com')) return true;
  // Replicate delivery URLs
  if (url.includes('replicate.delivery')) return true;
  // Common image extensions
  if (/\.(png|jpg|jpeg|gif|webp|svg|bmp)(\?.*)?$/i.test(url)) return true;
  // Image CDNs
  if (url.includes('images.unsplash.com')) return true;
  if (url.includes('i.imgur.com')) return true;
  return false;
}

/**
 * Extract image URLs from text content
 * Returns array of {url, start, end} for each image URL found
 */
function extractImageUrls(content: string): Array<{ url: string; start: number; end: number }> {
  const urlRegex = /https?:\/\/[^\s<>"')\]]+/gi;
  const images: Array<{ url: string; start: number; end: number }> = [];
  
  let match;
  while ((match = urlRegex.exec(content)) !== null) {
    const url = match[0];
    // Clean trailing punctuation that might be part of sentence
    const cleanUrl = url.replace(/[.,;:!?)]+$/, '');
    if (isImageUrl(cleanUrl)) {
      images.push({
        url: cleanUrl,
        start: match.index,
        end: match.index + cleanUrl.length,
      });
    }
  }
  
  return images;
}

/**
 * Parse the full message content into blocks
 */
function parseMessageContent(content: string): ParsedBlock[] {
  const blocks: ParsedBlock[] = [];
  
  // Regex patterns for special blocks
  const patterns = [
    { type: 'thinking' as const, regex: /<thinking[^>]*>[\s\S]*?<\/thinking>/g },
    { type: 'note' as const, regex: /<note[^>]*>[\s\S]*?<\/note>/g },
    { type: 'file' as const, regex: /<file[^>]*>[\s\S]*?<\/file>/g },
    { type: 'code' as const, regex: /```[\s\S]*?```/g },
  ];
  
  // Find all special blocks and their positions
  interface BlockMatch {
    type: ParsedBlock['type'];
    content: string;
    start: number;
    end: number;
  }
  
  const matches: BlockMatch[] = [];
  
  for (const { type, regex } of patterns) {
    let match;
    const regexCopy = new RegExp(regex.source, regex.flags);
    while ((match = regexCopy.exec(content)) !== null) {
      matches.push({
        type,
        content: match[0],
        start: match.index,
        end: match.index + match[0].length,
      });
    }
  }
  
  // Sort by position
  matches.sort((a, b) => a.start - b.start);
  
  // Build blocks
  let lastEnd = 0;
  
  /**
   * Helper to process text content - extracts images and tables
   */
  const processTextContent = (textContent: string) => {
    if (!textContent.trim()) return;
    
    // Check for images in this text segment
    const imageUrls = extractImageUrls(textContent);
    
    if (imageUrls.length > 0) {
      // Split text around images
      let lastImageEnd = 0;
      
      for (const img of imageUrls) {
        // Text before the image
        if (img.start > lastImageEnd) {
          const beforeText = textContent.slice(lastImageEnd, img.start).trim();
          if (beforeText) {
            const tableData = parseMarkdownTable(beforeText);
            if (tableData && tableData.headers.length > 0) {
              blocks.push({ type: 'table', content: beforeText, metadata: tableData });
            } else {
              blocks.push({ type: 'text', content: beforeText });
            }
          }
        }
        
        // The image itself
        blocks.push({ 
          type: 'image', 
          content: img.url,
          metadata: { url: img.url } as ImageBlockData
        });
        
        lastImageEnd = img.end;
      }
      
      // Text after the last image
      if (lastImageEnd < textContent.length) {
        const afterText = textContent.slice(lastImageEnd).trim();
        if (afterText) {
          const tableData = parseMarkdownTable(afterText);
          if (tableData && tableData.headers.length > 0) {
            blocks.push({ type: 'table', content: afterText, metadata: tableData });
          } else {
            blocks.push({ type: 'text', content: afterText });
          }
        }
      }
    } else {
      // No images, check for table or add as text
      const tableData = parseMarkdownTable(textContent);
      if (tableData && tableData.headers.length > 0) {
        blocks.push({ type: 'table', content: textContent, metadata: tableData });
      } else {
        blocks.push({ type: 'text', content: textContent });
      }
    }
  };

  for (const match of matches) {
    // Add text block before this match
    if (match.start > lastEnd) {
      const textContent = content.slice(lastEnd, match.start).trim();
      processTextContent(textContent);
    }
    
    // Add the special block
    blocks.push({ type: match.type, content: match.content });
    lastEnd = match.end;
  }
  
  // Add remaining text
  if (lastEnd < content.length) {
    const textContent = content.slice(lastEnd).trim();
    processTextContent(textContent);
  }
  
  // If no blocks found, treat entire content as text (may still have images)
  if (blocks.length === 0 && content.trim()) {
    processTextContent(content.trim());
  }
  
  return blocks;
}

// ============================================================================
// MARKDOWN PARSER (Enhanced)
// ============================================================================

/**
 * Enhanced markdown parser with Nicole's styling
 */
function parseMarkdown(text: string): string {
  let html = text;
  
  // Escape HTML
  html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');
  
  // Italic
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/_(.+?)_/g, '<em>$1</em>');
  
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code class="nicole-inline-code">$1</code>');
  
  // Headers
  html = html.replace(/^### (.+)$/gm, '<h3 class="nicole-h3">$1</h3>');
  html = html.replace(/^## (.+)$/gm, '<h2 class="nicole-h2">$1</h2>');
  html = html.replace(/^# (.+)$/gm, '<h1 class="nicole-h1">$1</h1>');
  
  // Lists - improved handling
  const lines = html.split('\n');
  let inList = false;
  let listType: 'ul' | 'ol' | null = null;
  const processedLines: string[] = [];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const unorderedMatch = line.match(/^[-*]\s+(.+)$/);
    const orderedMatch = line.match(/^(\d+)\.\s+(.+)$/);
    
    if (unorderedMatch) {
      if (!inList || listType !== 'ul') {
        if (inList) processedLines.push(listType === 'ol' ? '</ol>' : '</ul>');
        processedLines.push('<ul class="nicole-list">');
        inList = true;
        listType = 'ul';
      }
      processedLines.push(`<li>${unorderedMatch[1]}</li>`);
    } else if (orderedMatch) {
      if (!inList || listType !== 'ol') {
        if (inList) processedLines.push(listType === 'ol' ? '</ol>' : '</ul>');
        processedLines.push('<ol class="nicole-list nicole-list-ordered">');
        inList = true;
        listType = 'ol';
      }
      processedLines.push(`<li>${orderedMatch[2]}</li>`);
    } else {
      if (inList && line.trim() === '') {
        processedLines.push(listType === 'ol' ? '</ol>' : '</ul>');
        inList = false;
        listType = null;
      }
      processedLines.push(line);
    }
  }
  
  if (inList) {
    processedLines.push(listType === 'ol' ? '</ol>' : '</ul>');
  }
  
  html = processedLines.join('\n');
  
  // Paragraphs
  html = html.split(/\n\n+/).map(p => {
    const trimmed = p.trim();
    if (!trimmed) return '';
    if (trimmed.startsWith('<h') || trimmed.startsWith('<ul') || 
        trimmed.startsWith('<ol') || trimmed.startsWith('<pre') ||
        trimmed.startsWith('<div') || trimmed.startsWith('<table')) {
      return trimmed;
    }
    return `<p>${trimmed}</p>`;
  }).join('');
  
  // Line breaks within paragraphs
  html = html.replace(/\n/g, '<br/>');
  html = html.replace(/<\/li><br\/>/g, '</li>');
  html = html.replace(/<br\/><li>/g, '<li>');
  html = html.replace(/<br\/><\/ul>/g, '</ul>');
  html = html.replace(/<br\/><\/ol>/g, '</ol>');
  
  return html;
}

// ============================================================================
// IMAGE BLOCK RENDERER
// ============================================================================

interface ImageBlockProps {
  url: string;
  alt?: string;
}

const ImageBlock: React.FC<ImageBlockProps> = ({ url, alt }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  
  if (hasError) {
    return (
      <div 
        className="my-4 p-4 rounded-xl border flex items-center gap-3"
        style={{ 
          borderColor: nicoleColors.border,
          backgroundColor: nicoleColors.lavenderLight 
        }}
      >
        <svg className="w-6 h-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
            d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" 
          />
        </svg>
        <div>
          <div className="text-sm font-medium" style={{ color: nicoleColors.textSecondary }}>
            Image could not be loaded
          </div>
          <a 
            href={url} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-xs hover:underline"
            style={{ color: nicoleColors.lavender }}
          >
            Open original link
          </a>
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Inline Image */}
      <div className="my-4 relative group">
        <div 
          className="relative overflow-hidden rounded-xl border cursor-pointer transition-all hover:shadow-lg"
          style={{ borderColor: nicoleColors.border }}
          onClick={() => setIsExpanded(true)}
        >
          {isLoading && (
            <div 
              className="absolute inset-0 flex items-center justify-center"
              style={{ backgroundColor: nicoleColors.lavenderLight }}
            >
              <div className="w-8 h-8 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
            </div>
          )}
          <Image
            src={url}
            alt={alt || 'Screenshot captured by Nicole'}
            width={800}
            height={600}
            className="w-full h-auto max-h-96 object-contain"
            onLoad={() => setIsLoading(false)}
            onError={() => {
              setIsLoading(false);
              setHasError(true);
            }}
            unoptimized // Allow external URLs
          />
          
          {/* Hover Overlay */}
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
            <div className="bg-black/60 backdrop-blur-sm text-white px-3 py-1.5 rounded-lg text-sm flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
              </svg>
              Click to expand
            </div>
          </div>
        </div>
        
        {/* Source indicator */}
        {url.includes('cloudinary.com') && (
          <div className="mt-1 flex items-center gap-1 text-xs" style={{ color: nicoleColors.textTertiary }}>
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            Screenshot captured by Nicole
          </div>
        )}
      </div>

      {/* Lightbox Modal */}
      {isExpanded && (
        <div 
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={() => setIsExpanded(false)}
        >
          <button
            className="absolute top-4 right-4 text-white/70 hover:text-white p-2 rounded-full bg-white/10 hover:bg-white/20 transition-colors"
            onClick={() => setIsExpanded(false)}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          
          <div className="max-w-6xl max-h-[90vh] relative" onClick={e => e.stopPropagation()}>
            <Image
              src={url}
              alt={alt || 'Screenshot captured by Nicole'}
              width={1920}
              height={1080}
              className="max-w-full max-h-[90vh] object-contain rounded-lg"
              unoptimized
            />
            
            {/* Download button */}
            <a
              href={url}
              download
              target="_blank"
              rel="noopener noreferrer"
              className="absolute bottom-4 right-4 bg-white/20 hover:bg-white/30 backdrop-blur-sm text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
              onClick={e => e.stopPropagation()}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download
            </a>
          </div>
        </div>
      )}
    </>
  );
};

// ============================================================================
// CODE BLOCK RENDERER
// ============================================================================

interface CodeBlockProps {
  content: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({ content }) => {
  // Extract language and code
  const match = content.match(/```(\w+)?\n?([\s\S]*?)```/);
  const language = match?.[1] || 'text';
  const code = match?.[2]?.trim() || content.replace(/```/g, '').trim();
  
  const [copied, setCopied] = React.useState(false);
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  return (
    <div className="my-4 rounded-xl overflow-hidden border" style={{ borderColor: nicoleColors.border }}>
      {/* Header */}
      <div 
        className="px-4 py-2 flex items-center justify-between"
        style={{ backgroundColor: nicoleColors.lavenderLight }}
      >
        <span className="text-xs font-medium" style={{ color: nicoleColors.lavenderDark }}>
          {language.toUpperCase()}
        </span>
        <button
          onClick={handleCopy}
          className="text-xs px-2 py-1 rounded hover:bg-white/50 transition-colors"
          style={{ color: nicoleColors.lavenderDark }}
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      
      {/* Code */}
      <pre 
        className="p-4 overflow-x-auto text-sm"
        style={{ backgroundColor: '#1e1e1e', color: '#d4d4d4' }}
      >
        <code>{code}</code>
      </pre>
    </div>
  );
};

// ============================================================================
// BLOCK RENDERER
// ============================================================================

interface BlockRendererProps {
  block: ParsedBlock;
}

const BlockRenderer: React.FC<BlockRendererProps> = ({ block }) => {
  switch (block.type) {
    case 'thinking': {
      const data = parseThinkingBlock(block.content);
      if (!data) return null;
      return <ThinkingBox steps={data.steps} summary={data.summary} />;
    }
    
    case 'note': {
      const data = parseNoteBlock(block.content);
      if (!data) return null;
      return (
        <NoteCard title={data.title} iconType={data.iconType}>
          <div dangerouslySetInnerHTML={{ __html: parseMarkdown(data.content) }} />
        </NoteCard>
      );
    }
    
    case 'file': {
      const data = parseFileBlock(block.content);
      if (!data) return null;
      return (
        <FileCard
          filename={data.filename}
          fileType={data.fileType}
          content={data.content}
          iconType="code"
        />
      );
    }
    
    case 'image': {
      const imageData = block.metadata as ImageBlockData | undefined;
      const url = imageData?.url || block.content;
      return <ImageBlock url={url} alt={imageData?.alt} />;
    }
    
    case 'table': {
      const tableData = block.metadata as TableData | undefined;
      if (!tableData) return null;
      
      const columns = tableData.headers.map((header, i) => ({
        header,
        key: `col${i}` as keyof Record<string, string>,
        render: i === tableData.headers.length - 1 
          ? (val: string) => <span className="italic" style={{ color: nicoleColors.textTertiary }}>{val}</span>
          : undefined,
      }));
      
      const data = tableData.rows.map(row => {
        const obj: Record<string, string> = {};
        row.forEach((cell, i) => {
          obj[`col${i}`] = cell;
        });
        return obj;
      });
      
      return <StyledTable columns={columns} data={data} />;
    }
    
    case 'code':
      return <CodeBlock content={block.content} />;
    
    case 'text':
    default:
      return (
        <div 
          className="nicole-message-text"
          dangerouslySetInnerHTML={{ __html: parseMarkdown(block.content) }}
        />
      );
  }
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

interface NicoleMessageRendererProps {
  content: string;
  className?: string;
}

export const NicoleMessageRenderer: React.FC<NicoleMessageRendererProps> = ({ 
  content,
  className = ''
}) => {
  const blocks = useMemo(() => parseMessageContent(content), [content]);
  
  return (
    <div className={`nicole-message ${className}`}>
      {blocks.map((block, index) => (
        <BlockRenderer key={index} block={block} />
      ))}
    </div>
  );
};

export default NicoleMessageRenderer;

