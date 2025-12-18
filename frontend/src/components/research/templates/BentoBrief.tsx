'use client';

/**
 * Template 2: The Bento Intelligence Brief
 * 
 * Design Philosophy: Bloomberg Businessweek meets dashboard UI.
 * Information-dense but navigable. Perfect for data-heavy research.
 * 
 * Author: Pasta Fazool
 */

import { ResearchResponse } from '@/lib/hooks/useResearch';
import { DESIGN_TOKENS } from './templateTypes';
import { parseResearchData, ParsedResearchData } from './parseUtils';

interface BentoBriefProps {
  data: ResearchResponse;
}

const colors = DESIGN_TOKENS.colors.bento;

export function BentoBrief({ data }: BentoBriefProps) {
  const parsed: ParsedResearchData = parseResearchData(data);
  const { title, lead, body, findings, recommendations, bottomLine, sources, metadata, heroImage, images } = parsed;

  // Extract stats from findings for stat cards
  const statCards = findings.slice(0, 3).map((f, i) => ({
    label: f.title || `Finding ${i + 1}`,
    value: f.body.slice(0, 60) + (f.body.length > 60 ? '...' : ''),
  }));

  return (
    <article
      style={{
        background: colors.bg,
        color: colors.text,
        fontFamily: DESIGN_TOKENS.typography.sans.geometric,
        minHeight: '100%',
      }}
    >
      {/* Compact Header Bar */}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '16px 24px',
          borderBottom: `1px solid ${colors.border}`,
          background: colors.card,
        }}
      >
        <div>
          <h1
            style={{
              fontSize: '20px',
              fontWeight: 600,
              margin: 0,
              color: colors.text,
            }}
          >
            {title}
          </h1>
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
            fontSize: '12px',
            color: colors.muted,
          }}
        >
          <span>By <strong style={{ color: colors.accent }}>Pasta Fazool</strong></span>
          <span>|</span>
          <span>{metadata.date}</span>
          <span>|</span>
          <span>{sources.length} sources</span>
        </div>
      </header>

      {/* Bento Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(12, 1fr)',
          gap: '16px',
          padding: '24px',
        }}
      >
        {/* Hero Visual Card - full width if image exists */}
        {heroImage && (
          <div
            style={{
              gridColumn: 'span 12',
              background: colors.card,
              borderRadius: DESIGN_TOKENS.borderRadius.lg,
              overflow: 'hidden',
              border: `1px solid ${colors.border}`,
              boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
            }}
          >
            <img
              src={heroImage}
              alt={title}
              style={{
                width: '100%',
                height: '300px',
                objectFit: 'cover',
                display: 'block',
              }}
            />
          </div>
        )}

        {/* Hero Insight Card - spans 8 columns */}
        <div
          style={{
            gridColumn: 'span 8',
            background: colors.card,
            borderRadius: DESIGN_TOKENS.borderRadius.lg,
            padding: '24px',
            border: `1px solid ${colors.border}`,
            boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
          }}
        >
          <div
            style={{
              fontSize: '10px',
              fontWeight: 600,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: colors.accent,
              marginBottom: '12px',
            }}
          >
            Executive Summary
          </div>
          <p
            style={{
              fontSize: '16px',
              lineHeight: 1.6,
              color: colors.text,
              margin: 0,
            }}
          >
            {lead}
          </p>
        </div>

        {/* Stat Cards - 4 columns (2 stacked) */}
        <div
          style={{
            gridColumn: 'span 4',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          {statCards.slice(0, 2).map((stat, i) => (
            <div
              key={i}
              style={{
                background: i === 0 ? colors.accent : colors.card,
                borderRadius: DESIGN_TOKENS.borderRadius.md,
                padding: '20px',
                border: i === 0 ? 'none' : `1px solid ${colors.border}`,
                color: i === 0 ? '#fff' : colors.text,
              }}
            >
              <div
                style={{
                  fontSize: '10px',
                  fontWeight: 600,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  opacity: 0.8,
                  marginBottom: '8px',
                }}
              >
                {stat.label}
              </div>
              <div
                style={{
                  fontSize: '14px',
                  fontWeight: 500,
                  lineHeight: 1.4,
                }}
              >
                {stat.value}
              </div>
            </div>
          ))}
          
          {/* Image Thumbnails - compact cards */}
          {images && images.slice(1, 3).map((img, i) => (
            <div
              key={`img-${i}`}
              style={{
                background: colors.card,
                borderRadius: DESIGN_TOKENS.borderRadius.md,
                overflow: 'hidden',
                border: `1px solid ${colors.border}`,
              }}
            >
              <img
                src={img.url}
                alt={img.caption}
                style={{
                  width: '100%',
                  height: '120px',
                  objectFit: 'cover',
                  display: 'block',
                }}
              />
            </div>
          ))}
        </div>

        {/* Analysis Body - 8 columns */}
        <div
          style={{
            gridColumn: 'span 8',
            background: colors.card,
            borderRadius: DESIGN_TOKENS.borderRadius.lg,
            padding: '24px',
            border: `1px solid ${colors.border}`,
          }}
        >
          <div
            style={{
              fontSize: '10px',
              fontWeight: 600,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: colors.muted,
              marginBottom: '16px',
              paddingBottom: '8px',
              borderBottom: `2px solid ${colors.accent}`,
              display: 'inline-block',
            }}
          >
            Analysis
          </div>
          <div style={{ fontSize: '14px', lineHeight: 1.7, color: colors.text }}>
            {body.split('\n\n').map((para, i) => (
              <p key={i} style={{ marginBottom: '16px' }}>
                {para}
              </p>
            ))}
          </div>
        </div>

        {/* Key Takeaways Sidebar - 4 columns, sticky feel */}
        <div
          style={{
            gridColumn: 'span 4',
            background: colors.card,
            borderRadius: DESIGN_TOKENS.borderRadius.lg,
            padding: '20px',
            border: `1px solid ${colors.border}`,
            alignSelf: 'start',
          }}
        >
          <div
            style={{
              fontSize: '10px',
              fontWeight: 600,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: colors.accent,
              marginBottom: '16px',
            }}
          >
            Key Takeaways
          </div>
          <ul
            style={{
              margin: 0,
              padding: 0,
              listStyle: 'none',
            }}
          >
            {findings.slice(0, 5).map((f, i) => (
              <li
                key={i}
                style={{
                  fontSize: '13px',
                  lineHeight: 1.5,
                  padding: '12px 0',
                  borderBottom: i < findings.length - 1 ? `1px solid ${colors.border}` : 'none',
                  display: 'flex',
                  gap: '12px',
                }}
              >
                <span
                  style={{
                    width: '20px',
                    height: '20px',
                    borderRadius: '50%',
                    background: colors.accent,
                    color: '#fff',
                    fontSize: '11px',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  {i + 1}
                </span>
                <span>{f.body.slice(0, 100)}{f.body.length > 100 ? '...' : ''}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Recommendations Row - full width */}
        {recommendations.length > 0 && (
          <div
            style={{
              gridColumn: 'span 12',
              display: 'grid',
              gridTemplateColumns: `repeat(${Math.min(recommendations.length, 3)}, 1fr)`,
              gap: '16px',
            }}
          >
            {recommendations.slice(0, 3).map((r, i) => (
              <div
                key={i}
                style={{
                  background: colors.card,
                  borderRadius: DESIGN_TOKENS.borderRadius.md,
                  padding: '20px',
                  border: `1px solid ${colors.border}`,
                  borderTop: `3px solid ${colors.accent}`,
                }}
              >
                <div
                  style={{
                    fontSize: '10px',
                    fontWeight: 600,
                    letterSpacing: '0.08em',
                    textTransform: 'uppercase',
                    color: colors.accent,
                    marginBottom: '8px',
                  }}
                >
                  Recommendation {i + 1}
                </div>
                <p
                  style={{
                    fontSize: '14px',
                    lineHeight: 1.5,
                    margin: 0,
                    color: colors.text,
                  }}
                >
                  {r}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Bottom Line Card */}
        {bottomLine && (
          <div
            style={{
              gridColumn: 'span 12',
              background: `linear-gradient(135deg, ${colors.accent} 0%, #2563eb 100%)`,
              borderRadius: DESIGN_TOKENS.borderRadius.lg,
              padding: '24px 32px',
              color: '#fff',
            }}
          >
            <div
              style={{
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
                opacity: 0.8,
                marginBottom: '8px',
              }}
            >
              Bottom Line
            </div>
            <p
              style={{
                fontSize: '18px',
                fontWeight: 500,
                lineHeight: 1.5,
                margin: 0,
              }}
            >
              {bottomLine}
            </p>
          </div>
        )}
      </div>

      {/* Source Attribution Footer */}
      <footer
        style={{
          padding: '24px',
          borderTop: `1px solid ${colors.border}`,
          background: colors.card,
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
          }}
        >
          <div>
            <div
              style={{
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                color: colors.muted,
                marginBottom: '12px',
              }}
            >
              Sources ({sources.length})
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {sources.slice(0, 6).map((src, i) => (
                <a
                  key={i}
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    padding: '6px 12px',
                    background: colors.bg,
                    borderRadius: DESIGN_TOKENS.borderRadius.sm,
                    border: `1px solid ${colors.border}`,
                    fontSize: '12px',
                    color: colors.text,
                    textDecoration: 'none',
                  }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={src.favicon} alt="" width={14} height={14} />
                  {src.domain}
                </a>
              ))}
            </div>
          </div>
          <div
            style={{
              textAlign: 'right',
              fontSize: '11px',
              color: colors.muted,
            }}
          >
            <div>Research completed in {metadata.time}s</div>
            <div style={{ marginTop: '4px', color: colors.accent }}>
              Powered by AlphaWave Research
            </div>
          </div>
        </div>
      </footer>
    </article>
  );
}

export default BentoBrief;

