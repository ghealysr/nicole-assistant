/**
 * Research Article Templates - Type Definitions
 * 
 * 5 Editorial Templates:
 * 1. Immersive Longform - Kinfolk meets The New Yorker
 * 2. Bento Intelligence Brief - Bloomberg meets dashboard
 * 3. Editorial Scrapbook - Handmade collage aesthetic
 * 4. Magazine Spread - Print editorial adapted for digital
 * 5. Narrative Timeline - Scrollytelling documentary style
 */

import { ResearchResponse } from '@/lib/hooks/useResearch';

// Template identifiers
export type TemplateId = 
  | 'immersive-longform'
  | 'bento-brief'
  | 'editorial-scrapbook'
  | 'magazine-spread'
  | 'narrative-timeline';

// Template author personas
export type AuthorPersona = 'Purpchicka' | 'Pasta Fazool' | 'Mrs. Healy' | 'nhealy44' | 'Nicole';

// Template metadata
export interface TemplateInfo {
  id: TemplateId;
  name: string;
  description: string;
  author: AuthorPersona;
  mood: string;
  bestFor: string[];
  // Content weights for selection algorithm
  weights: {
    dataHeavy: number;      // Lots of stats/metrics
    narrative: number;      // Story-driven content
    visual: number;         // Image-rich content
    analytical: number;     // Analysis/recommendations focus
    exploratory: number;    // Discovery/research style
  };
}

// Content analysis result
export interface ContentAnalysis {
  wordCount: number;
  statCount: number;
  quoteCount: number;
  findingsCount: number;
  recommendationsCount: number;
  sourcesCount: number;
  hasImages: boolean;
  hasTimeline: boolean;
  primaryTone: 'narrative' | 'analytical' | 'exploratory' | 'investigative';
  dataRichness: number;  // 0-1 score
}

// Design tokens shared across templates
export const DESIGN_TOKENS = {
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
    xxl: '48px',
    xxxl: '64px',
  },
  maxWidth: {
    narrow: '55ch',
    body: '65ch',
    wide: '75ch',
    full: '100%',
  },
  borderRadius: {
    sm: '4px',
    md: '8px',
    lg: '12px',
    xl: '16px',
    round: '50%',
  },
  animation: {
    timing: 'cubic-bezier(0.4, 0, 0.2, 1)',
    duration: {
      fast: '150ms',
      normal: '300ms',
      slow: '500ms',
      reveal: '800ms',
    },
  },
  colors: {
    // Template 1: Immersive Longform - Warm, contemplative
    longform: {
      bg: '#faf8f5',
      text: '#1a1816',
      accent: '#8b7355',
      muted: '#a89b8c',
      border: '#e8e4de',
    },
    // Template 2: Bento Brief - Cool, professional
    bento: {
      bg: '#f8f9fb',
      text: '#0f172a',
      accent: '#3b82f6',
      muted: '#64748b',
      border: '#e2e8f0',
      card: '#ffffff',
    },
    // Template 3: Scrapbook - Warm, organic
    scrapbook: {
      bg: '#f5f0e8',
      text: '#2d2a26',
      accent: '#c4785c',
      muted: '#8b8378',
      border: '#d9d2c6',
      paper: '#fffef9',
    },
    // Template 4: Magazine - Classic, sophisticated
    magazine: {
      bg: '#ffffff',
      text: '#1a1a1a',
      accent: '#c41e3a',
      muted: '#6b6b6b',
      border: '#e5e5e5',
      folio: '#999999',
    },
    // Template 5: Timeline - Dark, cinematic
    timeline: {
      bg: '#0c0c0c',
      text: '#f5f5f5',
      accent: '#a855f7',
      muted: '#737373',
      border: '#262626',
      card: '#171717',
    },
  },
  typography: {
    // Serif families for editorial content
    serif: {
      elegant: '"Playfair Display", Georgia, serif',
      humanist: '"Lora", Georgia, serif',
      classic: '"Libre Baskerville", Georgia, serif',
      condensed: '"Freight Big Pro", "Times New Roman", serif',
    },
    // Sans-serif for UI and labels
    sans: {
      geometric: '"Inter", -apple-system, sans-serif',
      humanist: '"Source Sans Pro", -apple-system, sans-serif',
      condensed: '"Barlow Condensed", -apple-system, sans-serif',
    },
    // Monospace for annotations
    mono: '"JetBrains Mono", "SF Mono", monospace',
  },
};

// Template definitions
export const TEMPLATES: Record<TemplateId, TemplateInfo> = {
  'immersive-longform': {
    id: 'immersive-longform',
    name: 'The Immersive Longform',
    description: 'Kinfolk meets The New Yorker. Slow, deliberate reading experience.',
    author: 'Mrs. Healy',
    mood: 'Contemplative, authoritative, unhurried',
    bestFor: ['narrative research', 'in-depth analysis', 'personal topics'],
    weights: {
      dataHeavy: 0.3,
      narrative: 1.0,
      visual: 0.7,
      analytical: 0.6,
      exploratory: 0.8,
    },
  },
  'bento-brief': {
    id: 'bento-brief',
    name: 'The Bento Intelligence Brief',
    description: 'Bloomberg Businessweek meets dashboard UI. Information-dense but navigable.',
    author: 'Pasta Fazool',
    mood: 'Efficient, credible, scannable',
    bestFor: ['data analysis', 'market research', 'technical reports'],
    weights: {
      dataHeavy: 1.0,
      narrative: 0.2,
      visual: 0.5,
      analytical: 0.9,
      exploratory: 0.4,
    },
  },
  'editorial-scrapbook': {
    id: 'editorial-scrapbook',
    name: 'The Editorial Scrapbook',
    description: 'Intentional imperfection. Layered, collage aesthetic. Human craft visible.',
    author: 'Purpchicka',
    mood: 'Personal, curated, artistic',
    bestFor: ['creative research', 'design inspiration', 'personal projects'],
    weights: {
      dataHeavy: 0.2,
      narrative: 0.7,
      visual: 1.0,
      analytical: 0.3,
      exploratory: 0.9,
    },
  },
  'magazine-spread': {
    id: 'magazine-spread',
    name: 'The Magazine Spread',
    description: 'Print editorial logic adapted for digital. Classic hierarchy.',
    author: 'Nicole',
    mood: 'Sophisticated, curated, deliberate',
    bestFor: ['feature articles', 'interviews', 'reviews'],
    weights: {
      dataHeavy: 0.5,
      narrative: 0.8,
      visual: 0.8,
      analytical: 0.6,
      exploratory: 0.5,
    },
  },
  'narrative-timeline': {
    id: 'narrative-timeline',
    name: 'The Narrative Timeline',
    description: 'Scrollytelling-first. Story unfolds in beats. Documentary revelation.',
    author: 'nhealy44',
    mood: 'Cinematic, investigative, building tension',
    bestFor: ['historical research', 'investigations', 'process documentation'],
    weights: {
      dataHeavy: 0.6,
      narrative: 0.9,
      visual: 0.7,
      analytical: 0.5,
      exploratory: 0.7,
    },
  },
};

/**
 * Analyze research content to determine best template match
 */
export function analyzeContent(data: ResearchResponse): ContentAnalysis {
  const synthesis = typeof data.nicole_synthesis === 'string' 
    ? data.nicole_synthesis 
    : JSON.stringify(data.nicole_synthesis || '');
  
  const allText = [
    data.executive_summary || '',
    synthesis,
    ...(data.findings?.map(f => typeof f === 'string' ? f : f.content || '') || []),
    ...(data.recommendations || []),
  ].join(' ');

  // Count stats (numbers, percentages, currencies)
  const statMatches = allText.match(/\d+(?:\.\d+)?(?:%|x|X|k|K|M|B|\$|€|£)?|\$[\d,]+/g) || [];
  
  // Count quotes (text in quotation marks)
  const quoteMatches = allText.match(/"[^"]+"|'[^']+'/g) || [];
  
  // Determine tone based on keywords
  const narrativeKeywords = /story|journey|experience|felt|remember|through|began|ended/gi;
  const analyticalKeywords = /analysis|data|statistics|findings|research|study|evidence/gi;
  const exploratoryKeywords = /explore|discover|investigate|understand|learn|find/gi;
  const investigativeKeywords = /uncovered|revealed|exposed|hidden|secret|behind/gi;

  const narrativeScore = (allText.match(narrativeKeywords) || []).length;
  const analyticalScore = (allText.match(analyticalKeywords) || []).length;
  const exploratoryScore = (allText.match(exploratoryKeywords) || []).length;
  const investigativeScore = (allText.match(investigativeKeywords) || []).length;

  const scores = { 
    narrative: narrativeScore, 
    analytical: analyticalScore, 
    exploratory: exploratoryScore, 
    investigative: investigativeScore 
  };
  const primaryTone = (Object.entries(scores).sort((a, b) => b[1] - a[1])[0][0]) as ContentAnalysis['primaryTone'];

  const wordCount = allText.split(/\s+/).filter(w => w.length > 0).length;
  const findingsCount = data.findings?.length || 0;
  const recommendationsCount = data.recommendations?.length || 0;
  const sourcesCount = data.sources?.length || 0;

  // Data richness is high if lots of stats relative to word count
  const dataRichness = Math.min(1, (statMatches.length / Math.max(100, wordCount)) * 10);

  return {
    wordCount,
    statCount: statMatches.length,
    quoteCount: quoteMatches.length,
    findingsCount,
    recommendationsCount,
    sourcesCount,
    hasImages: false, // Would need to check for image URLs in data
    hasTimeline: investigativeScore > 3 || allText.includes('timeline'),
    primaryTone,
    dataRichness,
  };
}

/**
 * Select the best template based on content analysis
 */
export function selectTemplate(
  data: ResearchResponse, 
  lastUsed?: TemplateId
): TemplateId {
  const analysis = analyzeContent(data);
  
  // Score each template based on content analysis
  const scores: Record<TemplateId, number> = {} as Record<TemplateId, number>;
  
  for (const [id, template] of Object.entries(TEMPLATES)) {
    const templateId = id as TemplateId;
    let score = 0;
    
    // Weight by data richness
    score += template.weights.dataHeavy * analysis.dataRichness * 2;
    
    // Weight by tone match
    if (analysis.primaryTone === 'narrative') score += template.weights.narrative * 2;
    if (analysis.primaryTone === 'analytical') score += template.weights.analytical * 2;
    if (analysis.primaryTone === 'exploratory') score += template.weights.exploratory * 2;
    if (analysis.primaryTone === 'investigative') score += template.weights.narrative * 1.5; // Timeline is good for investigative
    
    // Bonus for stat-heavy content
    if (analysis.statCount > 5) score += template.weights.dataHeavy;
    
    // Bonus for quote-heavy content (scrapbook loves quotes)
    if (analysis.quoteCount > 2) score += templateId === 'editorial-scrapbook' ? 1.5 : 0.5;
    
    // Word count considerations
    if (analysis.wordCount > 1000 && templateId === 'immersive-longform') score += 1;
    if (analysis.wordCount < 500 && templateId === 'bento-brief') score += 1;
    
    // Penalize if same as last used (encourage variety)
    if (templateId === lastUsed) score -= 0.5;
    
    scores[templateId] = score;
  }
  
  // Find the highest scoring template
  const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  
  // If scores are very close (within 0.5), add randomness
  const topScore = sorted[0][1];
  const closeContenders = sorted.filter(([, score]) => topScore - score < 0.5);
  
  if (closeContenders.length > 1) {
    // Randomly select from close contenders
    const randomIndex = Math.floor(Math.random() * closeContenders.length);
    return closeContenders[randomIndex][0] as TemplateId;
  }
  
  return sorted[0][0] as TemplateId;
}

/**
 * Get random template (for variety mode)
 */
export function getRandomTemplate(exclude?: TemplateId): TemplateId {
  const ids = Object.keys(TEMPLATES).filter(id => id !== exclude) as TemplateId[];
  return ids[Math.floor(Math.random() * ids.length)];
}


