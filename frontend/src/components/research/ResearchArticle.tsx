'use client';

/**
 * ResearchArticle - Editorial-quality research presentation
 * 
 * Inspired by:
 * - New Yorker's elegant typography and spacing
 * - Time Magazine's use of imagery
 * - Medium's clean reading experience
 * 
 * Presents research as a curated article, not raw data.
 */

import { ResearchResponse } from '@/lib/hooks/useResearch';

interface ResearchArticleProps {
  data: ResearchResponse;
}

export function ResearchArticle({ data }: ResearchArticleProps) {
  // Convert query to proper headline case
  const toHeadlineCase = (str: string): string => {
    if (!str) return '';
    
    // Words that should remain lowercase (unless first word)
    const lowercaseWords = new Set([
      'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'on', 'at', 
      'to', 'by', 'in', 'of', 'up', 'as', 'is', 'it', 'so', 'be'
    ]);
    
    // Clean up the string - remove "research" prefix patterns
    let cleaned = str
      .replace(/^research\s+(the\s+)?/i, '')
      .replace(/^(what|how|why|when|where|who)\s+(is|are|do|does|can|could|would|should)\s+/i, '')
      .trim();
    
    if (!cleaned) cleaned = str;
    
    return cleaned
      .toLowerCase()
      .split(' ')
      .map((word, index) => {
        if (index === 0 || !lowercaseWords.has(word)) {
          return word.charAt(0).toUpperCase() + word.slice(1);
        }
        return word;
      })
      .join(' ');
  };

  // Format date nicely
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return new Date().toLocaleDateString('en-US', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
    return new Date(dateStr).toLocaleDateString('en-US', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  // Get research type label
  const getTypeLabel = (type?: string) => {
    const labels: Record<string, string> = {
      general: 'Research Report',
      vibe_inspiration: 'Design Inspiration',
      competitor: 'Competitor Analysis',
      technical: 'Technical Deep Dive',
    };
    return labels[type || 'general'] || 'Research Report';
  };

  // Extract lead paragraph (first 2 sentences)
  const getLeadParagraph = (text: string) => {
    if (!text) return '';
    const sentences = text.split(/(?<=[.!?])\s+/).slice(0, 2);
    return sentences.join(' ');
  };

  // Get remaining paragraphs
  const getBodyParagraphs = (text: string) => {
    if (!text) return '';
    const sentences = text.split(/(?<=[.!?])\s+/);
    if (sentences.length <= 2) return '';
    return sentences.slice(2).join(' ');
  };

  // Parse finding to extract content
  const parseFinding = (finding: unknown): { title: string; body: string } => {
    // If it's a string
    if (typeof finding === 'string') {
      // Check for title:body pattern
      const colonIndex = finding.indexOf(':');
      if (colonIndex > 0 && colonIndex < 60) {
        return {
          title: finding.slice(0, colonIndex).trim(),
          body: finding.slice(colonIndex + 1).trim()
        };
      }
      return { title: '', body: finding };
    }
    
    // If it's an object
    if (typeof finding === 'object' && finding !== null) {
      const obj = finding as Record<string, unknown>;
      
      // Try common field patterns
      const content = obj.content || obj.text || obj.finding || obj.summary || '';
      const title = obj.title || obj.category || obj.insight || '';
      
      if (typeof content === 'string' && content) {
        return { 
          title: typeof title === 'string' ? title : '', 
          body: content 
        };
      }
      
      // If no content field, try to extract meaningful text
      if (obj.action && typeof obj.action === 'string') {
        return {
          title: (obj.category || obj.insight || '') as string,
          body: obj.action
        };
      }
    }
    
    return { title: '', body: '' };
  };

  // Parse recommendation
  const parseRecommendation = (rec: unknown): string => {
    if (typeof rec === 'string') return rec;
    
    if (typeof rec === 'object' && rec !== null) {
      const obj = rec as Record<string, unknown>;
      
      // Try to build a readable recommendation
      if (obj.action && typeof obj.action === 'string') {
        const category = obj.category ? `${obj.category}: ` : '';
        return `${category}${obj.action}`;
      }
      
      // Fallback to content/text fields
      const content = obj.content || obj.text || obj.recommendation || '';
      if (typeof content === 'string') return content;
    }
    
    return '';
  };

  // Get favicon URL for a domain
  const getFaviconUrl = (url: string): string => {
    try {
      const domain = new URL(url).hostname;
      // Use Google's favicon service - reliable and fast
      return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
    } catch {
      return '';
    }
  };

  // Get display info for a source
  const getSourceInfo = (url: string): { domain: string; displayName: string } => {
    try {
      const urlObj = new URL(url);
      const hostname = urlObj.hostname.replace(/^www\./, '');
      
      // Map common domains to friendly names
      const domainNames: Record<string, string> = {
        'medium.com': 'Medium',
        'newyorker.com': 'The New Yorker',
        'time.com': 'TIME',
        'nytimes.com': 'The New York Times',
        'washingtonpost.com': 'Washington Post',
        'theguardian.com': 'The Guardian',
        'bbc.com': 'BBC',
        'forbes.com': 'Forbes',
        'wired.com': 'WIRED',
        'techcrunch.com': 'TechCrunch',
        'arstechnica.com': 'Ars Technica',
        'theverge.com': 'The Verge',
        'wikipedia.org': 'Wikipedia',
        'github.com': 'GitHub',
        'stackoverflow.com': 'Stack Overflow',
        'dev.to': 'DEV',
        'linkedin.com': 'LinkedIn',
        'twitter.com': 'Twitter/X',
        'x.com': 'X',
        'youtube.com': 'YouTube',
        'reddit.com': 'Reddit',
      };
      
      const displayName = domainNames[hostname] || 
        hostname.split('.').slice(-2, -1)[0]?.charAt(0).toUpperCase() + 
        hostname.split('.').slice(-2, -1)[0]?.slice(1) || hostname;
      
      return { domain: hostname, displayName };
    } catch {
      return { domain: url, displayName: 'Source' };
    }
  };

  // Filter out empty findings
  const validFindings = (data.findings || [])
    .map(parseFinding)
    .filter(f => f.body.length > 0);

  // Filter out empty recommendations
  const validRecommendations = (data.recommendations || [])
    .map(parseRecommendation)
    .filter(r => r.length > 0);

  return (
    <article className="research-article">
      {/* Article Header */}
      <header className="research-article-header">
        <div className="research-article-category">
          {getTypeLabel(data.research_type)}
        </div>
        <h1 className="research-article-title">
          {toHeadlineCase(data.query || '')}
        </h1>
        <p className="research-article-subtitle">
          {getLeadParagraph(data.executive_summary || '')}
        </p>
        <div className="research-article-meta">
          <div className="research-article-byline">
            <div className="research-article-avatar">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
                <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/>
              </svg>
            </div>
            <div className="research-article-author">
              <span className="author-name">Nicole</span>
              <span className="author-role">AI Research Assistant</span>
            </div>
          </div>
          <time className="research-article-date">{formatDate(data.completed_at)}</time>
        </div>
      </header>

      {/* Article Body */}
      <div className="research-article-body">
        {/* Executive Summary continuation */}
        {data.executive_summary && getBodyParagraphs(data.executive_summary) && (
          <p className="research-article-lead">
            {getBodyParagraphs(data.executive_summary)}
          </p>
        )}

        {/* Nicole's Synthesis - The Heart of the Article */}
        {data.nicole_synthesis && (
          <section className="research-article-section">
            <p className="research-article-text">
              {data.nicole_synthesis}
            </p>
          </section>
        )}

        {/* Key Findings as Structured Content */}
        {validFindings.length > 0 && (
          <section className="research-article-section">
            <h2 className="research-article-section-title">Key Findings</h2>
            <div className="research-article-findings">
              {validFindings.map((finding, i) => (
                <div key={i} className="research-finding-card">
                  {finding.title && (
                    <h3 className="research-finding-title">{finding.title}</h3>
                  )}
                  <p className="research-finding-text">{finding.body}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Recommendations as Action Items */}
        {validRecommendations.length > 0 && (
          <section className="research-article-section">
            <h2 className="research-article-section-title">Recommendations</h2>
            <ul className="research-article-recommendations">
              {validRecommendations.map((rec, i) => (
                <li key={i}>{rec}</li>
              ))}
            </ul>
          </section>
        )}

        {/* Sources as References with Favicons */}
        {data.sources && data.sources.length > 0 && (
          <section className="research-article-sources">
            <h3 className="research-sources-title">Sources</h3>
            <div className="research-sources-list">
              {data.sources.map((source, i) => {
                const url = typeof source === 'string' ? source : source?.url;
                const title = typeof source === 'object' ? source?.title : null;
                if (!url) return null;
                
                const { domain, displayName } = getSourceInfo(url);
                const faviconUrl = getFaviconUrl(url);
                
                return (
                  <a
                    key={i}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="research-source-link"
                  >
                    <span className="source-favicon">
                      {faviconUrl ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img 
                          src={faviconUrl} 
                          alt="" 
                          width={16} 
                          height={16}
                          onError={(e) => {
                            // Fallback to generic icon on error
                            e.currentTarget.style.display = 'none';
                            e.currentTarget.nextElementSibling?.classList.remove('hidden');
                          }}
                        />
                      ) : null}
                      <svg 
                        viewBox="0 0 24 24" 
                        fill="none" 
                        stroke="currentColor" 
                        strokeWidth={2} 
                        className={faviconUrl ? 'hidden' : ''}
                        width={16}
                        height={16}
                      >
                        <circle cx="12" cy="12" r="10"/>
                        <line x1="2" y1="12" x2="22" y2="12"/>
                        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                      </svg>
                    </span>
                    <span className="source-info">
                      <span className="source-title">{title || displayName}</span>
                      <span className="source-domain">{domain}</span>
                    </span>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="source-icon">
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                      <polyline points="15 3 21 3 21 9"/>
                      <line x1="10" y1="14" x2="21" y2="3"/>
                    </svg>
                  </a>
                );
              })}
            </div>
          </section>
        )}
      </div>

      {/* Article Footer */}
      <footer className="research-article-footer">
        <div className="research-article-stats">
          <span className="stat">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
            {(data.metadata?.elapsed_seconds ?? 0).toFixed(1)}s research time
          </span>
          <span className="stat">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
            {data.sources?.length || 0} sources analyzed
          </span>
          <span className="stat cost">
            Powered by Gemini 3 Pro
          </span>
        </div>
      </footer>
    </article>
  );
}

export default ResearchArticle;
