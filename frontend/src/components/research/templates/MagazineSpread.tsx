'use client';

/**
 * Template 4: The Magazine Spread
 * 
 * Design Philosophy: Print editorial logic adapted for digital.
 * Horizontal sections that feel like turning pages. Drop caps, gutters, classic hierarchy.
 * 
 * Author: Nicole
 */

import { ResearchResponse } from '@/lib/hooks/useResearch';
import { DESIGN_TOKENS } from './templateTypes';
import { parseResearchData, ParsedResearchData } from './parseUtils';

interface MagazineSpreadProps {
  data: ResearchResponse;
}

const colors = DESIGN_TOKENS.colors.magazine;

export function MagazineSpread({ data }: MagazineSpreadProps) {
  const parsed: ParsedResearchData = parseResearchData(data);
  const { title, subtitle, lead, body, findings, recommendations, bottomLine, sources, metadata, heroImage, images } = parsed;

  const bodyParagraphs = body.split('\n\n').filter(p => p.trim());

  return (
    <article
      style={{
        background: colors.bg,
        color: colors.text,
        fontFamily: DESIGN_TOKENS.typography.serif.classic,
        minHeight: '100%',
      }}
    >
      {/* Spread 1: Cover - Title + Hero area */}
      <section
        style={{
          minHeight: '60vh',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          borderBottom: `1px solid ${colors.border}`,
        }}
      >
        {/* Left: Title area */}
        <div
          style={{
            padding: '48px 32px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            borderRight: `1px solid ${colors.border}`,
          }}
        >
          {/* Department label */}
          <div
            style={{
              fontFamily: DESIGN_TOKENS.typography.sans.geometric,
              fontSize: '11px',
              fontWeight: 600,
              letterSpacing: '0.15em',
              textTransform: 'uppercase',
              color: colors.accent,
              marginBottom: '24px',
              paddingBottom: '8px',
              borderBottom: `2px solid ${colors.accent}`,
              display: 'inline-block',
              alignSelf: 'flex-start',
            }}
          >
            Research
          </div>

          <h1
            style={{
              fontFamily: DESIGN_TOKENS.typography.serif.elegant,
              fontSize: 'clamp(32px, 4vw, 48px)',
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: '-0.02em',
              color: colors.text,
              margin: '0 0 24px',
            }}
          >
            {title}
          </h1>

          {subtitle && (
            <p
              style={{
                fontSize: '18px',
                lineHeight: 1.5,
                color: colors.muted,
                fontStyle: 'italic',
                margin: 0,
              }}
            >
              {subtitle}
            </p>
          )}

          {/* Byline */}
          <div
            style={{
              marginTop: 'auto',
              paddingTop: '32px',
            }}
          >
            <div style={{ fontStyle: 'italic', fontSize: '14px', color: colors.muted }}>
              By <span style={{ color: colors.text, fontWeight: 500 }}>Nicole</span>
            </div>
            <div
              style={{
                fontFamily: DESIGN_TOKENS.typography.sans.geometric,
                fontSize: '12px',
                color: colors.muted,
                marginTop: '4px',
              }}
            >
              {metadata.date}
            </div>
          </div>
        </div>

        {/* Right: Hero image or abstract gradient fallback */}
        <div
          style={{
            background: heroImage
              ? `url(${heroImage})`
              : `linear-gradient(135deg, ${colors.accent}15 0%, ${colors.accent}05 50%, #f0f0f0 100%)`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: heroImage ? '0' : '48px',
            position: 'relative',
          }}
        >
          {!heroImage && (
            <div
              style={{
                background: colors.bg,
                padding: '32px',
                maxWidth: '360px',
                boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
              }}
            >
              <p
                style={{
                  fontSize: '16px',
                  lineHeight: 1.7,
                  fontStyle: 'italic',
                  color: colors.text,
                  margin: 0,
                  textAlign: 'center',
                }}
              >
                &ldquo;{lead.slice(0, 200)}{lead.length > 200 ? '...' : ''}&rdquo;
              </p>
            </div>
          )}
        </div>
      </section>

      {/* Spread 2: Opener - Lede with drop cap */}
      <section
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          borderBottom: `1px solid ${colors.border}`,
        }}
      >
        {/* Left: Lead paragraph with drop cap */}
        <div
          style={{
            padding: '48px 32px',
            borderRight: `1px solid ${colors.border}`,
          }}
        >
          <p
            style={{
              fontSize: '17px',
              lineHeight: 1.8,
              color: colors.text,
              margin: 0,
            }}
          >
            <span
              style={{
                float: 'left',
                fontSize: '72px',
                lineHeight: 0.8,
                fontFamily: DESIGN_TOKENS.typography.serif.elegant,
                fontWeight: 700,
                marginRight: '12px',
                marginTop: '8px',
                color: colors.accent,
              }}
            >
              {lead.charAt(0)}
            </span>
            {lead.slice(1)}
          </p>
        </div>

        {/* Right: Key metrics/stats box */}
        <div
          style={{
            padding: '48px 32px',
            background: '#fafafa',
          }}
        >
          <div
            style={{
              fontFamily: DESIGN_TOKENS.typography.sans.geometric,
              fontSize: '10px',
              fontWeight: 600,
              letterSpacing: '0.15em',
              textTransform: 'uppercase',
              color: colors.accent,
              marginBottom: '24px',
            }}
          >
            At a Glance
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
            <div>
              <div style={{ fontSize: '36px', fontWeight: 700, color: colors.accent }}>{findings.length}</div>
              <div style={{ fontSize: '12px', color: colors.muted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Key Findings</div>
            </div>
            <div>
              <div style={{ fontSize: '36px', fontWeight: 700, color: colors.text }}>{sources.length}</div>
              <div style={{ fontSize: '12px', color: colors.muted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Sources</div>
            </div>
            <div>
              <div style={{ fontSize: '36px', fontWeight: 700, color: colors.text }}>{recommendations.length}</div>
              <div style={{ fontSize: '12px', color: colors.muted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Recommendations</div>
            </div>
            <div>
              <div style={{ fontSize: '36px', fontWeight: 700, color: colors.muted }}>{metadata.time}s</div>
              <div style={{ fontSize: '12px', color: colors.muted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Research Time</div>
            </div>
          </div>
        </div>
      </section>

      {/* Inline Images - displayed between spreads */}
      {images && images.length > 0 && (
        <section
          style={{
            padding: '48px 32px',
            borderBottom: `1px solid ${colors.border}`,
            background: '#fafafa',
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: images.length === 1 ? '1fr' : '1fr 1fr',
              gap: '32px',
            }}
          >
            {images.slice(0, 2).map((img, idx) => (
              <figure key={idx} style={{ margin: 0 }}>
                <img
                  src={img.url}
                  alt={img.caption || `Research image ${idx + 1}`}
                  style={{
                    width: '100%',
                    height: 'auto',
                    display: 'block',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
                  }}
                />
                {img.caption && (
                  <figcaption
                    style={{
                      fontFamily: DESIGN_TOKENS.typography.sans.geometric,
                      fontSize: '12px',
                      color: colors.muted,
                      marginTop: '12px',
                      fontStyle: 'italic',
                      lineHeight: 1.5,
                    }}
                  >
                    {img.caption}
                  </figcaption>
                )}
              </figure>
            ))}
          </div>
        </section>
      )}

      {/* Spread 3: Body text in 2-column layout */}
      <section
        style={{
          padding: '48px 32px',
          borderBottom: `1px solid ${colors.border}`,
        }}
      >
        <div
          style={{
            columns: '2',
            columnGap: '48px',
            columnRule: `1px solid ${colors.border}`,
          }}
        >
          {bodyParagraphs.map((para, i) => (
            <p
              key={i}
              style={{
                fontSize: '15px',
                lineHeight: 1.8,
                marginBottom: '20px',
                breakInside: 'avoid',
              }}
            >
              {para}
            </p>
          ))}
        </div>

        {/* Folio-style page marker */}
        <div
          style={{
            textAlign: 'center',
            marginTop: '32px',
            fontFamily: DESIGN_TOKENS.typography.sans.geometric,
            fontSize: '11px',
            color: colors.folio,
          }}
        >
          — 2 —
        </div>
      </section>

      {/* Spread 4: Findings */}
      {findings.length > 0 && (
        <section
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            borderBottom: `1px solid ${colors.border}`,
          }}
        >
          {/* Left: Section header */}
          <div
            style={{
              padding: '48px 32px',
              borderRight: `1px solid ${colors.border}`,
              background: '#fafafa',
            }}
          >
            <div
              style={{
                fontFamily: DESIGN_TOKENS.typography.sans.geometric,
                fontSize: '11px',
                fontWeight: 600,
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
                color: colors.accent,
                marginBottom: '16px',
              }}
            >
              Key Findings
            </div>
            <h2
              style={{
                fontFamily: DESIGN_TOKENS.typography.serif.elegant,
                fontSize: '28px',
                fontWeight: 700,
                lineHeight: 1.2,
                color: colors.text,
                margin: 0,
              }}
            >
              What We Discovered
            </h2>
          </div>

          {/* Right: Findings list */}
          <div
            style={{
              padding: '48px 32px',
            }}
          >
            {findings.map((f, i) => (
              <div
                key={i}
                style={{
                  marginBottom: '24px',
                  paddingBottom: '24px',
                  borderBottom: i < findings.length - 1 ? `1px solid ${colors.border}` : 'none',
                }}
              >
                {f.title && (
                  <div
                    style={{
                      fontFamily: DESIGN_TOKENS.typography.sans.geometric,
                      fontSize: '12px',
                      fontWeight: 600,
                      color: colors.accent,
                      marginBottom: '8px',
                    }}
                  >
                    {f.title}
                  </div>
                )}
                <p
                  style={{
                    fontSize: '15px',
                    lineHeight: 1.7,
                    color: colors.text,
                    margin: 0,
                  }}
                >
                  {f.body}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Spread 5: Recommendations */}
      {recommendations.length > 0 && (
        <section
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            borderBottom: `1px solid ${colors.border}`,
          }}
        >
          {/* Left: Recommendations */}
          <div
            style={{
              padding: '48px 32px',
              borderRight: `1px solid ${colors.border}`,
            }}
          >
            <div
              style={{
                fontFamily: DESIGN_TOKENS.typography.sans.geometric,
                fontSize: '11px',
                fontWeight: 600,
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
                color: colors.accent,
                marginBottom: '24px',
              }}
            >
              Recommendations
            </div>
            {recommendations.map((r, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  gap: '16px',
                  marginBottom: '20px',
                }}
              >
                <span
                  style={{
                    fontFamily: DESIGN_TOKENS.typography.serif.elegant,
                    fontSize: '24px',
                    fontWeight: 700,
                    color: colors.accent,
                    lineHeight: 1,
                  }}
                >
                  {i + 1}
                </span>
                <p
                  style={{
                    fontSize: '15px',
                    lineHeight: 1.6,
                    color: colors.text,
                    margin: 0,
                  }}
                >
                  {r}
                </p>
              </div>
            ))}
          </div>

          {/* Right: Bottom Line */}
          <div
            style={{
              padding: '48px 32px',
              background: `linear-gradient(135deg, ${colors.accent}10 0%, ${colors.accent}05 100%)`,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
            }}
          >
            {bottomLine && (
              <>
                <div
                  style={{
                    fontFamily: DESIGN_TOKENS.typography.sans.geometric,
                    fontSize: '10px',
                    fontWeight: 600,
                    letterSpacing: '0.15em',
                    textTransform: 'uppercase',
                    color: colors.accent,
                    marginBottom: '16px',
                  }}
                >
                  The Bottom Line
                </div>
                <p
                  style={{
                    fontFamily: DESIGN_TOKENS.typography.serif.elegant,
                    fontSize: '22px',
                    fontWeight: 500,
                    lineHeight: 1.4,
                    color: colors.text,
                    margin: 0,
                  }}
                >
                  {bottomLine}
                </p>
              </>
            )}
          </div>
        </section>
      )}

      {/* Closer: Sources & Credits */}
      <footer
        style={{
          padding: '48px 32px',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '2fr 1fr',
            gap: '48px',
          }}
        >
          {/* Sources */}
          <div>
            <div
              style={{
                fontFamily: DESIGN_TOKENS.typography.sans.geometric,
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
                color: colors.muted,
                marginBottom: '16px',
              }}
            >
              Sources
            </div>
            <div
              style={{
                columns: '2',
                columnGap: '24px',
              }}
            >
              {sources.map((src, i) => (
                <a
                  key={i}
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '12px',
                    color: colors.text,
                    textDecoration: 'none',
                    marginBottom: '8px',
                    breakInside: 'avoid',
                  }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={src.favicon} alt="" width={14} height={14} />
                  <span style={{ textDecoration: 'underline' }}>{src.title || src.domain}</span>
                </a>
              ))}
            </div>
          </div>

          {/* End mark */}
          <div
            style={{
              textAlign: 'right',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'flex-end',
            }}
          >
            <div
              style={{
                fontFamily: DESIGN_TOKENS.typography.serif.elegant,
                fontSize: '32px',
                fontWeight: 700,
                color: colors.accent,
                marginBottom: '8px',
              }}
            >
              ■
            </div>
            <div
              style={{
                fontSize: '11px',
                color: colors.muted,
              }}
            >
              Powered by AlphaWave Research
            </div>
          </div>
        </div>
      </footer>
    </article>
  );
}

export default MagazineSpread;

