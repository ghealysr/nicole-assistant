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
 * - Standard markdown formatting
 * 
 * Special block syntax (parsed from response):
 * - <thinking>...</thinking> - Renders ThinkingBox
 * - <note>...</note> - Renders NoteCard
 * - <file>...</file> - Renders FileCard
 * - Standard markdown tables - Renders StyledTable
 */

import React, { useMemo } from 'react';
import {
  ThinkingBox,
  FileCard,
  StyledTable,
  NoteCard,
  FileBadge,
  nicoleColors,
  type ThinkingStep,
} from './NicoleThinkingUI';

// ============================================================================
// TYPES
// ============================================================================

interface ParsedBlock {
  type: 'text' | 'thinking' | 'note' | 'file' | 'table' | 'code';
  content: string;
  metadata?: Record<string, unknown>;
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
  const steps: ThinkingStep[] = stepTexts.map((text, index) => ({
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
  const contentMatch = content.match(/>([^<]*)</s);
  
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
  const contentMatch = content.match(/>([^<]*)</s);
  
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
 * Parse the full message content into blocks
 */
function parseMessageContent(content: string): ParsedBlock[] {
  const blocks: ParsedBlock[] = [];
  let remaining = content;
  
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
  
  for (const match of matches) {
    // Add text block before this match
    if (match.start > lastEnd) {
      const textContent = content.slice(lastEnd, match.start).trim();
      if (textContent) {
        // Check if this text contains a markdown table
        const tableData = parseMarkdownTable(textContent);
        if (tableData && tableData.headers.length > 0) {
          blocks.push({ type: 'table', content: textContent, metadata: tableData });
        } else {
          blocks.push({ type: 'text', content: textContent });
        }
      }
    }
    
    // Add the special block
    blocks.push({ type: match.type, content: match.content });
    lastEnd = match.end;
  }
  
  // Add remaining text
  if (lastEnd < content.length) {
    const textContent = content.slice(lastEnd).trim();
    if (textContent) {
      // Check for table in remaining content
      const tableData = parseMarkdownTable(textContent);
      if (tableData && tableData.headers.length > 0) {
        blocks.push({ type: 'table', content: textContent, metadata: tableData });
      } else {
        blocks.push({ type: 'text', content: textContent });
      }
    }
  }
  
  // If no blocks found, treat entire content as text
  if (blocks.length === 0 && content.trim()) {
    blocks.push({ type: 'text', content: content.trim() });
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

