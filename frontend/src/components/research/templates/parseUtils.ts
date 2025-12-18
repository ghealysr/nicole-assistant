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
  metadata: {
    date: string;
    time: string;
    model: string;
    tokens: number;
    cost: number;
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
 * Parse the full research response into a standardized format
 */
export function parseResearchData(data: ResearchResponse): ParsedResearchData {
  // Parse nicole_synthesis JSON if it's a string
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

  // Extract structured content
  const title = data.article_title || parsedSynthesis.article_title || parsedSynthesis.articletitle || toHeadlineCase(data.query);
  const subtitle = data.subtitle || parsedSynthesis.subtitle || '';
  const lead = stripMarkdown(parsedSynthesis.lead_paragraph || parsedSynthesis.leadparagraph || data.executive_summary || '');
  const body = stripMarkdown(parsedSynthesis.body || '');
  const bottomLine = data.bottom_line || parsedSynthesis.bottom_line || parsedSynthesis.bottomline || '';

  // Get findings
  const rawFindings = parsedSynthesis.key_findings || parsedSynthesis.keyfindings || data.findings || [];
  const findings = (Array.isArray(rawFindings) ? rawFindings : [])
    .map(parseFinding)
    .filter(f => f.body.length > 0);

  // Get recommendations
  const rawRecommendations = parsedSynthesis.recommendations || data.recommendations || [];
  const recommendations = (Array.isArray(rawRecommendations) ? rawRecommendations : [])
    .map(r => {
      let text = stripMarkdown(typeof r === 'string' ? r : JSON.stringify(r));
      text = text.replace(/^[→➜➔►▶]\s*/, '').trim();
      return text;
    })
    .filter(r => r.length > 0);

  // Sources
  const rawSources = data.sources && data.sources.length > 0
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
    .filter((s): s is ParsedSource => s !== null);

  // Metadata
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

  const allText = [lead, body, ...findings.map(f => f.body), ...recommendations].join(' ');
  const wordCount = allText.split(/\s+/).filter(w => w.length > 0).length;

  return {
    title,
    subtitle,
    lead,
    body,
    findings,
    recommendations,
    bottomLine,
    sources,
    metadata: {
      date,
      time: (data.metadata?.elapsed_seconds ?? 0).toFixed(1),
      model: data.metadata?.model || 'gemini-3-pro',
      tokens: (data.metadata?.input_tokens ?? 0) + (data.metadata?.output_tokens ?? 0),
      cost: data.metadata?.cost_usd ?? 0,
    },
    wordCount,
  };
}

