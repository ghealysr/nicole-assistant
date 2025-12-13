'use client';

/**
 * ResearchArticle - Editorial-quality research presentation
 * Simplified with inline styles for reliability
 */

import { ResearchResponse, ResearchFinding } from '@/lib/hooks/useResearch';

interface ResearchArticleProps {
  data: ResearchResponse;
}

// Inline styles for guaranteed rendering
const styles = {
  article: {
    background: '#ffffff',
    color: '#1a1a1a',
    fontFamily: 'Georgia, "Times New Roman", serif',
    borderRadius: '12px',
    overflow: 'hidden',
  },
  header: {
    padding: '32px 28px 24px',
    borderBottom: '1px solid #e5e5e5',
  },
  category: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontSize: '11px',
    fontWeight: 600,
    letterSpacing: '0.12em',
    textTransform: 'uppercase' as const,
    color: '#8B5CF6',
    marginBottom: '12px',
  },
  title: {
    fontFamily: 'Georgia, "Times New Roman", serif',
    fontSize: '26px',
    fontWeight: 700,
    lineHeight: 1.25,
    color: '#1a1a1a',
    margin: '0 0 16px 0',
  },
  subtitle: {
    fontFamily: 'Georgia, "Times New Roman", serif',
    fontSize: '16px',
    lineHeight: 1.6,
    color: '#666666',
    margin: '0 0 20px 0',
  },
  meta: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    paddingTop: '16px',
    borderTop: '1px solid #f0f0f0',
  },
  avatar: {
    width: '36px',
    height: '36px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #8B5CF6 0%, #A78BFA 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
  },
  authorName: {
    fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
    fontSize: '14px',
    fontWeight: 600,
    color: '#1a1a1a',
  },
  authorRole: {
    fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
    fontSize: '12px',
    color: '#999999',
  },
  body: {
    padding: '28px',
  },
  text: {
    fontFamily: 'Georgia, "Times New Roman", serif',
    fontSize: '16px',
    lineHeight: 1.8,
    color: '#1a1a1a',
    margin: '0 0 24px 0',
  },
  sectionTitle: {
    fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
    fontSize: '12px',
    fontWeight: 600,
    letterSpacing: '0.08em',
    textTransform: 'uppercase' as const,
    color: '#8B5CF6',
    margin: '32px 0 16px 0',
    paddingBottom: '8px',
    borderBottom: '2px solid #8B5CF6',
    display: 'inline-block',
  },
  findingCard: {
    background: '#f8f8f8',
    borderLeft: '3px solid #8B5CF6',
    padding: '16px 20px',
    borderRadius: '0 8px 8px 0',
    marginBottom: '12px',
  },
  findingTitle: {
    fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
    fontSize: '14px',
    fontWeight: 600,
    color: '#1a1a1a',
    margin: '0 0 6px 0',
  },
  findingText: {
    fontFamily: 'Georgia, serif',
    fontSize: '14px',
    lineHeight: 1.7,
    color: '#444444',
    margin: 0,
  },
  recommendation: {
    fontFamily: 'Georgia, serif',
    fontSize: '15px',
    lineHeight: 1.7,
    color: '#1a1a1a',
    margin: '0 0 12px 0',
    paddingLeft: '24px',
    position: 'relative' as const,
  },
  sourceLink: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 16px',
    background: '#f8f8f8',
    borderRadius: '8px',
    textDecoration: 'none',
    marginBottom: '8px',
    border: '1px solid transparent',
    transition: 'all 0.2s',
  },
  sourceFavicon: {
    width: '24px',
    height: '24px',
    borderRadius: '4px',
    background: '#fff',
    border: '1px solid #e5e5e5',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    flexShrink: 0,
  },
  sourceTitle: {
    fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
    fontSize: '14px',
    fontWeight: 500,
    color: '#1a1a1a',
  },
  sourceDomain: {
    fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
    fontSize: '12px',
    color: '#666666',
  },
  footer: {
    padding: '20px 28px',
    background: '#f8f8f8',
    borderTop: '1px solid #e5e5e5',
    display: 'flex',
    alignItems: 'center',
    gap: '20px',
    flexWrap: 'wrap' as const,
  },
  stat: {
    fontFamily: '-apple-system, BlinkMacSystemFont, sans-serif',
    fontSize: '12px',
    color: '#999999',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
};

export function ResearchArticle({ data }: ResearchArticleProps) {
  // Strip markdown
  const stripMarkdown = (text: string): string => {
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
  };

  // Headline case
  const toHeadlineCase = (str: string): string => {
    if (!str) return 'Research Report';
    const cleaned = str
      .replace(/^research\s+(the\s+)?/i, '')
      .replace(/^(what|how|why)\s+(is|are|do|does)\s+/i, '')
      .trim() || str;
    
    const lowercaseWords = new Set(['a', 'an', 'the', 'and', 'but', 'or', 'for', 'in', 'of', 'to', 'by']);
    return cleaned
      .toLowerCase()
      .split(' ')
      .map((word, i) => (i === 0 || !lowercaseWords.has(word)) 
        ? word.charAt(0).toUpperCase() + word.slice(1) 
        : word)
      .join(' ');
  };

  // Format date
  const formatDate = (dateStr?: string) => {
    const date = dateStr ? new Date(dateStr) : new Date();
    return date.toLocaleDateString('en-US', { 
      weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' 
    });
  };

  // Parse finding
  const parseFinding = (finding: ResearchFinding | string): { title: string; body: string } => {
    if (typeof finding === 'string') {
      const cleaned = stripMarkdown(finding);
      const colonIdx = cleaned.indexOf(':');
      if (colonIdx > 0 && colonIdx < 60) {
        return { title: cleaned.slice(0, colonIdx).trim(), body: cleaned.slice(colonIdx + 1).trim() };
      }
      return { title: '', body: cleaned };
    }
    const content = stripMarkdown(finding?.content || finding?.text || '');
    const title = stripMarkdown((finding as Record<string, unknown>)?.category as string || '');
    return { title, body: content };
  };

  // Get favicon
  const getFavicon = (url: string) => {
    try {
      return `https://www.google.com/s2/favicons?domain=${new URL(url).hostname}&sz=32`;
    } catch { return ''; }
  };

  // Get source info
  const getSourceInfo = (url: string) => {
    try {
      const hostname = new URL(url).hostname.replace(/^www\./, '');
      return { domain: hostname, name: hostname.split('.')[0] };
    } catch { return { domain: url, name: 'Source' }; }
  };

  // Get content
  const executiveSummary = stripMarkdown(data.executive_summary || '');
  const synthesis = stripMarkdown(data.nicole_synthesis || '');
  const findings = (data.findings || []).map(parseFinding).filter(f => f.body.length > 0);
  const recommendations = (data.recommendations || [])
    .map(r => stripMarkdown(typeof r === 'string' ? r : JSON.stringify(r)))
    .filter(r => r.length > 0);
  const sources = data.sources || [];

  // If no structured content, split synthesis into paragraphs
  const hasSummary = executiveSummary.length > 0;
  const displaySummary = hasSummary ? executiveSummary : synthesis.slice(0, 300);
  const displayBody = hasSummary ? synthesis : synthesis.slice(300);

  return (
    <article style={styles.article}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.category}>Research Report</div>
        <h1 style={styles.title}>{toHeadlineCase(data.query)}</h1>
        {displaySummary && (
          <p style={styles.subtitle}>{displaySummary}</p>
        )}
        <div style={styles.meta}>
          <div style={styles.avatar}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} width={20} height={20}>
              <path d="M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5"/>
            </svg>
          </div>
          <div>
            <div style={styles.authorName}>Nicole</div>
            <div style={styles.authorRole}>AI Research Assistant</div>
          </div>
        </div>
      </header>

      {/* Body */}
      <div style={styles.body}>
        {displayBody && (
          <p style={styles.text}>{displayBody}</p>
        )}

        {/* Findings */}
        {findings.length > 0 && (
          <section>
            <h2 style={styles.sectionTitle}>Key Findings</h2>
            {findings.map((f, i) => (
              <div key={i} style={styles.findingCard}>
                {f.title && <h3 style={styles.findingTitle}>{f.title}</h3>}
                <p style={styles.findingText}>{f.body}</p>
              </div>
            ))}
          </section>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <section>
            <h2 style={styles.sectionTitle}>Recommendations</h2>
            {recommendations.map((r, i) => (
              <p key={i} style={styles.recommendation}>→ {r}</p>
            ))}
          </section>
        )}

        {/* Sources */}
        {sources.length > 0 && (
          <section style={{ marginTop: '32px', paddingTop: '24px', borderTop: '1px solid #e5e5e5' }}>
            <h3 style={{ ...styles.sectionTitle, color: '#999', borderColor: '#999' }}>Sources</h3>
            {sources.map((source, i) => {
              const url = typeof source === 'string' ? source : source?.url;
              const title = typeof source === 'object' ? source?.title : null;
              if (!url) return null;
              const { domain, name } = getSourceInfo(url);
              return (
                <a key={i} href={url} target="_blank" rel="noopener noreferrer" style={styles.sourceLink}>
                  <span style={styles.sourceFavicon}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={getFavicon(url)} alt="" width={16} height={16} style={{ objectFit: 'contain' }} />
                  </span>
                  <span style={{ flex: 1, minWidth: 0 }}>
                    <div style={styles.sourceTitle}>{title || name}</div>
                    <div style={styles.sourceDomain}>{domain}</div>
                  </span>
                  <svg viewBox="0 0 24 24" fill="none" stroke="#999" strokeWidth={2} width={14} height={14}>
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                    <polyline points="15 3 21 3 21 9"/>
                    <line x1="10" y1="14" x2="21" y2="3"/>
                  </svg>
                </a>
              );
            })}
          </section>
        )}
      </div>

      {/* Footer */}
      <footer style={styles.footer}>
        <span style={styles.stat}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} width={14} height={14}>
            <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
          </svg>
          {(data.metadata?.elapsed_seconds ?? 0).toFixed(1)}s
        </span>
        <span style={styles.stat}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} width={14} height={14}>
            <path d="M12 2L2 7l10 5 10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
          </svg>
          {sources.length} sources
        </span>
        <span style={{ ...styles.stat, marginLeft: 'auto', color: '#8B5CF6' }}>
          Powered by AlphaWave Research
        </span>
      </footer>
    </article>
  );
}

export default ResearchArticle;
