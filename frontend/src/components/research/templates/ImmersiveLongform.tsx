'use client';

/**
 * Template 1: The Immersive Longform
 * 
 * Design Philosophy: Kinfolk meets The New Yorker digital.
 * Slow, deliberate reading experience. Documentary photography aesthetic.
 * 
 * Author: Mrs. Healy
 */

import { ResearchResponse } from '@/lib/hooks/useResearch';
import { DESIGN_TOKENS } from './templateTypes';
import { parseResearchData, ParsedResearchData } from './parseUtils';

interface ImmersiveLongformProps {
  data: ResearchResponse;
}

const colors = DESIGN_TOKENS.colors.longform;

export function ImmersiveLongform({ data }: ImmersiveLongformProps) {
  const parsed: ParsedResearchData = parseResearchData(data);
  const { title, subtitle, lead, body, findings, recommendations, bottomLine, sources, metadata, heroImage, images } = parsed;

  return (
    <article
      style={{
        background: colors.bg,
        color: colors.text,
        fontFamily: DESIGN_TOKENS.typography.serif.humanist,
        minHeight: '100%',
        position: 'relative',
      }}
    >
      {/* Hero Section - Full viewport feel */}
      <header
        style={{
          padding: '64px 32px 48px',
          borderBottom: `1px solid ${colors.border}`,
          position: 'relative',
        }}
      >
        {/* Chapter marker */}
        <div
          style={{
            fontFamily: DESIGN_TOKENS.typography.serif.elegant,
            fontSize: '12px',
            letterSpacing: '0.2em',
            color: colors.muted,
            marginBottom: '24px',
            textTransform: 'uppercase',
          }}
        >
          I. Research Report
        </div>

        {/* Title - Bottom-left aligned, high contrast */}
        <h1
          style={{
            fontFamily: DESIGN_TOKENS.typography.serif.elegant,
            fontSize: 'clamp(32px, 5vw, 48px)',
            fontWeight: 700,
            lineHeight: 1.15,
            color: colors.text,
            margin: 0,
            maxWidth: '85%',
          }}
        >
          {title}
        </h1>

        {subtitle && (
          <p
            style={{
              fontFamily: DESIGN_TOKENS.typography.serif.humanist,
              fontSize: '18px',
              lineHeight: 1.5,
              color: colors.muted,
              marginTop: '16px',
              fontStyle: 'italic',
              maxWidth: '70ch',
            }}
          >
            {subtitle}
          </p>
        )}

        {/* Byline */}
        <div
          style={{
            marginTop: '32px',
            paddingTop: '16px',
            borderTop: `1px solid ${colors.border}`,
            display: 'flex',
            alignItems: 'center',
            gap: '16px',
          }}
        >
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: '50%',
              background: `linear-gradient(135deg, ${colors.accent} 0%, ${colors.muted} 100%)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <span style={{ color: '#fff', fontSize: '16px', fontWeight: 600 }}>MH</span>
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: '14px' }}>Mrs. Healy</div>
            <div style={{ fontSize: '13px', color: colors.muted }}>
              {metadata.date} · {Math.ceil(parsed.wordCount / 200)} min read
            </div>
          </div>
        </div>
      </header>

      {/* Hero Image - Full bleed with desaturation */}
      {heroImage && (
        <div
          style={{
            width: '100%',
            height: '60vh',
            minHeight: '400px',
            maxHeight: '600px',
            position: 'relative',
            overflow: 'hidden',
            marginBottom: '48px',
          }}
        >
          <img
            src={heroImage}
            alt={title}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              filter: 'saturate(0.9) brightness(0.95)',
            }}
          />
          {/* Vignette overlay */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'radial-gradient(circle at center, transparent 40%, rgba(0,0,0,0.15) 100%)',
            }}
          />
        </div>
      )}

      {/* Body - 65ch max-width centered */}
      <div
        style={{
          maxWidth: '65ch',
          margin: '0 auto',
          padding: '48px 24px',
        }}
      >
        {/* Lead paragraph - slightly larger with drop cap effect */}
        {lead && (
          <p
            style={{
              fontSize: '20px',
              lineHeight: 1.8,
              color: colors.text,
              marginBottom: '32px',
            }}
          >
            <span
              style={{
                float: 'left',
                fontSize: '56px',
                lineHeight: 1,
                fontFamily: DESIGN_TOKENS.typography.serif.elegant,
                fontWeight: 700,
                marginRight: '8px',
                marginTop: '4px',
                color: colors.accent,
              }}
            >
              {lead.charAt(0)}
            </span>
            {lead.slice(1)}
          </p>
        )}

        {/* Body paragraphs with image breaks */}
        {body.split('\n\n').map((para, i) => (
          <div key={i}>
            <p
              style={{
                fontSize: '18px',
                lineHeight: 1.8,
                marginBottom: '24px',
                color: colors.text,
              }}
            >
              {para}
            </p>
            
            {/* Insert image after every 2nd paragraph if available */}
            {images && images.length > 0 && (i + 1) % 2 === 0 && images[Math.floor((i + 1) / 2) - 1] && (
              <figure
                style={{
                  margin: '48px -24px',
                  width: 'calc(100% + 48px)',
                }}
              >
                <img
                  src={images[Math.floor((i + 1) / 2) - 1].url}
                  alt={images[Math.floor((i + 1) / 2) - 1].caption}
                  style={{
                    width: '100%',
                    height: 'auto',
                    display: 'block',
                    filter: 'saturate(0.9)',
                  }}
                />
                <figcaption
                  style={{
                    marginTop: '12px',
                    fontSize: '13px',
                    fontFamily: DESIGN_TOKENS.typography.sans.geometric,
                    letterSpacing: '0.05em',
                    textTransform: 'uppercase',
                    color: colors.muted,
                    textAlign: 'left',
                  }}
                >
                  {images[Math.floor((i + 1) / 2) - 1].caption}
                </figcaption>
              </figure>
            )}
          </div>
        ))}

        {/* Horizontal rule as design breather */}
        <hr
          style={{
            border: 'none',
            height: '1px',
            background: colors.border,
            margin: '48px 0',
          }}
        />

        {/* Pull quote style findings */}
        {findings.length > 0 && (
          <>
            <div
              style={{
                fontFamily: DESIGN_TOKENS.typography.serif.elegant,
                fontSize: '12px',
                letterSpacing: '0.15em',
                color: colors.muted,
                textTransform: 'uppercase',
                marginBottom: '24px',
              }}
            >
              II. Key Findings
            </div>

            {findings.map((f, i) => (
              <div
                key={i}
                style={{
                  margin: '32px 0',
                  paddingLeft: '24px',
                  borderLeft: `3px solid ${colors.accent}`,
                }}
              >
                {f.title && (
                  <div
                    style={{
                      fontSize: '14px',
                      fontWeight: 600,
                      color: colors.accent,
                      marginBottom: '8px',
                      fontFamily: DESIGN_TOKENS.typography.sans.geometric,
                    }}
                  >
                    {f.title}
                  </div>
                )}
                <p
                  style={{
                    fontSize: '17px',
                    lineHeight: 1.7,
                    color: colors.text,
                    margin: 0,
                  }}
                >
                  {f.body}
                </p>
              </div>
            ))}
          </>
        )}

        {/* Recommendations as asymmetric pull quotes */}
        {recommendations.length > 0 && (
          <>
            <hr
              style={{
                border: 'none',
                height: '1px',
                background: colors.border,
                margin: '48px 0',
              }}
            />

            <div
              style={{
                fontFamily: DESIGN_TOKENS.typography.serif.elegant,
                fontSize: '12px',
                letterSpacing: '0.15em',
                color: colors.muted,
                textTransform: 'uppercase',
                marginBottom: '24px',
              }}
            >
              III. Recommendations
            </div>

            {recommendations.map((r, i) => (
              <blockquote
                key={i}
                style={{
                  fontFamily: DESIGN_TOKENS.typography.serif.elegant,
                  fontSize: '22px',
                  fontStyle: 'italic',
                  lineHeight: 1.5,
                  color: `${colors.accent}cc`,
                  margin: '24px 0',
                  padding: '0 0 0 16px',
                  borderLeft: 'none',
                }}
              >
                → {r}
              </blockquote>
            ))}
          </>
        )}

        {/* Bottom Line */}
        {bottomLine && (
          <div
            style={{
              marginTop: '48px',
              padding: '32px',
              background: `linear-gradient(135deg, ${colors.bg} 0%, #f0ebe4 100%)`,
              borderRadius: '4px',
              position: 'relative',
            }}
          >
            <div
              style={{
                position: 'absolute',
                top: '-12px',
                left: '24px',
                background: colors.accent,
                color: '#fff',
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
                padding: '4px 12px',
                borderRadius: '2px',
              }}
            >
              The Bottom Line
            </div>
            <p
              style={{
                fontFamily: DESIGN_TOKENS.typography.serif.elegant,
                fontSize: '18px',
                fontWeight: 500,
                lineHeight: 1.6,
                color: colors.text,
                margin: 0,
              }}
            >
              {bottomLine}
            </p>
          </div>
        )}
      </div>

      {/* Sources - editorial credits style */}
      {sources.length > 0 && (
        <div
          style={{
            maxWidth: '65ch',
            margin: '0 auto',
            padding: '0 24px 48px',
          }}
        >
          <div
            style={{
              fontFamily: DESIGN_TOKENS.typography.sans.geometric,
              fontSize: '11px',
              letterSpacing: '0.1em',
              color: colors.muted,
              textTransform: 'uppercase',
              marginBottom: '16px',
            }}
          >
            Sources & References
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {sources.map((src, i) => (
              <a
                key={i}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  fontSize: '14px',
                  color: colors.accent,
                  textDecoration: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                }}
              >
                <span style={{ color: colors.muted }}>{i + 1}.</span>
                <span style={{ textDecoration: 'underline' }}>{src.title || src.domain}</span>
                <span style={{ color: colors.muted, fontSize: '12px' }}>↗</span>
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Footer - subtle END marker */}
      <footer
        style={{
          textAlign: 'center',
          padding: '32px',
          borderTop: `1px solid ${colors.border}`,
        }}
      >
        <div
          style={{
            fontFamily: DESIGN_TOKENS.typography.serif.elegant,
            fontSize: '12px',
            letterSpacing: '0.3em',
            color: colors.muted,
          }}
        >
          — END —
        </div>
        <div
          style={{
            marginTop: '16px',
            fontSize: '12px',
            color: colors.muted,
          }}
        >
          Powered by AlphaWave Research · {metadata.time}s
        </div>
      </footer>
    </article>
  );
}

export default ImmersiveLongform;

