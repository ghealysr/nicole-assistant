/**
 * Shared parsing utilities for research templates
 */

import { ResearchResponse, ResearchFinding } from '@/lib/hooks/useResearch';

export interface ParsedFinding {
  title: string;
  body: string;
}

export interface ParsedSource {
  url: string;
  title: string;
  domain: string;
  favicon: string;
}

export interface ParsedResearchData {
  title: string;
  subtitle: string;
  lead: string;
  body: string;
  findings: ParsedFinding[];
  recommendations: string[];
  bottomLine: string;
  sources: ParsedSource[];
  heroImage?: string;
  images: Array<{
    url: string;
    caption: string;
    source: string;
  }>;
  screenshots: Array<{
    url: string;
    sourceUrl: string;
    caption: string;
  }>;
  metadata: {
    date: string;
    time: string;
    model: string;
    tokens: number;
    cost: number;
    imageCount: number;
  };
  wordCount: number;
}

/**
 * Strip markdown formatting from text
 */
export function stripMarkdown(text: string): string {
  if (!text) return '';
  return text
    .replace(/#{1,6}\s*/g, '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    .replace(/^\s*>\s+/gm, '')
    .replace(/^[-*_]{3,}\s*$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/**
 * Convert to headline case
 */
export function toHeadlineCase(str: string): string {
  if (!str) return 'Research Report';
  const cleaned = str
    .replace(/^research\s+(the\s+)?/i, '')
    .replace(/^(what|how|why)\s+(is|are|do|does)\s+/i, '')
    .trim() || str;

  const lowercaseWords = new Set(['a', 'an', 'the', 'and', 'but', 'or', 'for', 'in', 'of', 'to', 'by']);
  return cleaned
    .toLowerCase()
    .split(' ')
    .map((word, i) =>
      i === 0 || !lowercaseWords.has(word)
        ? word.charAt(0).toUpperCase() + word.slice(1)
        : word
    )
    .join(' ');
}

/**
 * Parse a finding into title and body
 */
export function parseFinding(finding: ResearchFinding | string): ParsedFinding {
  if (typeof finding === 'string') {
    let cleaned = stripMarkdown(finding);
    cleaned = cleaned.replace(/^[•·\-]\s*/, '').trim();
    if (!cleaned) return { title: '', body: '' };
    const colonIdx = cleaned.indexOf(':');
    if (colonIdx > 0 && colonIdx < 80) {
      return {
        title: cleaned.slice(0, colonIdx).trim(),
        body: cleaned.slice(colonIdx + 1).trim(),
      };
    }
    return { title: '', body: cleaned };
  }
  const content = stripMarkdown(finding?.content || finding?.text || '');
  const title = stripMarkdown((finding as Record<string, unknown>)?.category as string || '');
  return { title, body: content };
}

/**
 * Get source info from URL
 */
export function getSourceInfo(url: string): ParsedSource {
  try {
    const urlObj = new URL(url);
    const hostname = urlObj.hostname.replace(/^www\./, '');
    const domain = hostname;
    const name = hostname.split('.')[0];
    const favicon = `https://www.google.com/s2/favicons?domain=${hostname}&sz=32`;
    return { url, title: name, domain, favicon };
  } catch {
    return { url, title: 'Source', domain: url, favicon: '' };
  }
}

/**
 * Parse the full research response into a standardized format for templates.
 * 
 * Now uses direct field access since backend properly stores all structured fields.
 * Falls back to nicole_synthesis JSON parsing for legacy data.
 */
export function parseResearchData(data: ResearchResponse): ParsedResearchData {
  // Parse nicole_synthesis as fallback for legacy records that don't have structured fields
  const parsedSynthesis = (() => {
    try {
      const raw = data.nicole_synthesis || '';
      if (typeof raw === 'string' && raw.startsWith('{')) {
        return JSON.parse(raw);
      }
      return typeof raw === 'object' ? raw : {};
    } catch {
      return {};
    }
  })();

  // Primary: Use direct fields from backend
  // Fallback: Parse from nicole_synthesis JSON (legacy)
  // Final fallback: Generate from query
  const title = data.article_title 
    || parsedSynthesis.article_title 
    || parsedSynthesis.articletitle 
    || toHeadlineCase(data.query);
  
  const subtitle = data.subtitle 
    || parsedSynthesis.subtitle 
    || '';
  
  const lead = stripMarkdown(
    data.lead_paragraph 
    || parsedSynthesis.lead_paragraph 
    || parsedSynthesis.leadparagraph 
    || data.executive_summary 
    || ''
  );
  
  const body = stripMarkdown(
    data.body 
    || parsedSynthesis.body 
    || ''
  );
  
  const bottomLine = data.bottom_line 
    || parsedSynthesis.bottom_line 
    || parsedSynthesis.bottomline 
    || '';

  // Get findings - prefer data.findings, then synthesis
  const rawFindings = data.findings?.length > 0 
    ? data.findings 
    : (parsedSynthesis.key_findings || parsedSynthesis.keyfindings || []);
  
  const findings = (Array.isArray(rawFindings) ? rawFindings : [])
    .map(parseFinding)
    .filter(f => f.body.length > 0);

  // Get recommendations - prefer data.recommendations, then synthesis
  const rawRecommendations = data.recommendations?.length > 0 
    ? data.recommendations 
    : (parsedSynthesis.recommendations || []);
  
  const recommendations = (Array.isArray(rawRecommendations) ? rawRecommendations : [])
    .map(r => {
      let text = stripMarkdown(typeof r === 'string' ? r : JSON.stringify(r));
      text = text.replace(/^[→➜➔►▶]\s*/, '').trim();
      return text;
    })
    .filter(r => r.length > 0);

  // Sources - prefer data.sources, then synthesis
  const rawSources = data.sources?.length > 0
    ? data.sources
    : (parsedSynthesis.sources || []);
  
  const sources: ParsedSource[] = rawSources
    .map((src: string | { url?: string; title?: string }) => {
      const url = typeof src === 'string' ? src : src?.url || '';
      if (!url) return null;
      const info = getSourceInfo(url);
      if (typeof src === 'object' && src.title) {
        info.title = src.title;
      }
      return info;
    })
    .filter((s: ParsedSource | null): s is ParsedSource => s !== null);

  // Metadata - format dates nicely
  const date = data.completed_at
    ? new Date(data.completed_at).toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      })
    : new Date().toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      });

  // Calculate word count for template selection
  const allText = [lead, body, ...findings.map(f => f.body), ...recommendations].join(' ');
  const wordCount = allText.split(/\s+/).filter(w => w.length > 0).length;

  // Parse images - from data.images or empty array
  const images = (data.images || []).map(img => ({
    url: img.url,
    caption: img.caption || '',
    source: img.source || '',
  }));

  // Parse screenshots - from data.screenshots or empty array
  const screenshots = (data.screenshots || []).map(shot => ({
    url: shot.url,
    sourceUrl: shot.source_url,
    caption: shot.caption || '',
  }));

  return {
    title,
    subtitle,
    lead,
    body,
    findings,
    recommendations,
    bottomLine,
    sources,
    heroImage: data.hero_image,
    images,
    screenshots,
    metadata: {
      date,
      time: (data.metadata?.elapsed_seconds ?? 0).toFixed(1),
      model: data.metadata?.model || 'gemini-2.5-pro',
      tokens: (data.metadata?.input_tokens ?? 0) + (data.metadata?.output_tokens ?? 0),
      cost: data.metadata?.cost_usd ?? 0,
      imageCount: (data.metadata?.screenshot_count || images.length || screenshots.length) || 0,
    },
    wordCount,
  };
}

