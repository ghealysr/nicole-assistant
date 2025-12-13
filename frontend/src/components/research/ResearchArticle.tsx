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

  // Extract first paragraph for lead
  const getLeadParagraph = (text: string) => {
    const sentences = text.split('. ').slice(0, 2);
    return sentences.join('. ') + (sentences.length > 0 ? '.' : '');
  };

  // Get remaining paragraphs
  const getBodyParagraphs = (text: string) => {
    const sentences = text.split('. ');
    if (sentences.length <= 2) return [];
    return sentences.slice(2).join('. ');
  };

  return (
    <article className="research-article">
      {/* Article Header */}
      <header className="research-article-header">
        <div className="research-article-category">
          {getTypeLabel(data.research_type)}
        </div>
        <h1 className="research-article-title">
          {data.query}
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
        {/* Executive Summary as Lead */}
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
        {data.findings && data.findings.length > 0 && (
          <section className="research-article-section">
            <h2 className="research-article-section-title">Key Findings</h2>
            <div className="research-article-findings">
              {data.findings.map((finding, i) => {
                const content = typeof finding === 'string' 
                  ? finding 
                  : (finding?.content || finding?.text || '');
                
                // Check if it looks like a structured finding with a title
                const hasTitle = content.includes(':') && content.indexOf(':') < 50;
                const [title, ...rest] = hasTitle ? content.split(':') : ['', content];
                const body = hasTitle ? rest.join(':').trim() : content;

                return (
                  <div key={i} className="research-finding-card">
                    {hasTitle && title && (
                      <h3 className="research-finding-title">{title}</h3>
                    )}
                    <p className="research-finding-text">{body}</p>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Recommendations as Action Items */}
        {data.recommendations && data.recommendations.length > 0 && (
          <section className="research-article-section">
            <h2 className="research-article-section-title">Recommendations</h2>
            <ul className="research-article-recommendations">
              {data.recommendations.map((rec, i) => (
                <li key={i}>{typeof rec === 'string' ? rec : JSON.stringify(rec)}</li>
              ))}
            </ul>
          </section>
        )}

        {/* Sources as References */}
        {data.sources && data.sources.length > 0 && (
          <section className="research-article-sources">
            <h3 className="research-sources-title">Sources</h3>
            <div className="research-sources-list">
              {data.sources.map((source, i) => {
                const url = typeof source === 'string' ? source : source?.url;
                const title = typeof source === 'object' ? source?.title : null;
                if (!url) return null;
                
                return (
                  <a
                    key={i}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="research-source-link"
                  >
                    <span className="source-number">{i + 1}</span>
                    <span className="source-title">{title || new URL(url).hostname}</span>
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

