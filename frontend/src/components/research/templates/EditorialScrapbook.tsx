'use client';

/**
 * Template 3: The Editorial Scrapbook
 * 
 * Design Philosophy: Intentional imperfection. Layered, collage aesthetic.
 * Human craft visible. Anti-AI positioning through handmade feel.
 * 
 * Author: Purpchicka
 */

import { ResearchResponse } from '@/lib/hooks/useResearch';
import { DESIGN_TOKENS } from './templateTypes';
import { parseResearchData, ParsedResearchData } from './parseUtils';

interface EditorialScrapbookProps {
  data: ResearchResponse;
}

const colors = DESIGN_TOKENS.colors.scrapbook;

// Random rotation helper for scattered effect
function getRotation(index: number): string {
  const rotations = [-2, 1.5, -1, 2, -0.5, 1];
  return `${rotations[index % rotations.length]}deg`;
}

export function EditorialScrapbook({ data }: EditorialScrapbookProps) {
  const parsed: ParsedResearchData = parseResearchData(data);
  const { title, subtitle, lead, body, findings, recommendations, bottomLine, sources, metadata, images } = parsed;

  return (
    <article
      style={{
        background: colors.bg,
        backgroundImage: `url("data:image/svg+xml,%3Csvg width='100' height='100' viewBox='0 0 100 100' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='%239C92AC' fill-opacity='0.03'%3E%3Ccircle cx='50' cy='50' r='1'/%3E%3C/g%3E%3C/svg%3E")`,
        color: colors.text,
        fontFamily: DESIGN_TOKENS.typography.serif.classic,
        minHeight: '100%',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Title Card - Angled with annotation feel */}
      <header
        style={{
          padding: '48px 32px',
          position: 'relative',
        }}
      >
        {/* Decorative tape element */}
        <div
          style={{
            position: 'absolute',
            top: '24px',
            left: '50%',
            transform: 'translateX(-50%) rotate(2deg)',
            width: '80px',
            height: '24px',
            background: 'linear-gradient(90deg, rgba(196, 120, 92, 0.3) 0%, rgba(196, 120, 92, 0.15) 100%)',
            borderRadius: '2px',
          }}
        />

        {/* Main title card */}
        <div
          style={{
            background: colors.paper,
            padding: '32px',
            transform: `rotate(${getRotation(0)})`,
            boxShadow: '4px 6px 12px rgba(0,0,0,0.08)',
            maxWidth: '600px',
            margin: '24px auto 0',
            position: 'relative',
          }}
        >
          <h1
            style={{
              fontFamily: DESIGN_TOKENS.typography.serif.condensed,
              fontSize: 'clamp(28px, 5vw, 42px)',
              fontWeight: 700,
              lineHeight: 1.1,
              letterSpacing: '-0.02em',
              color: colors.text,
              margin: 0,
            }}
          >
            {title}
          </h1>

          {subtitle && (
            <p
              style={{
                fontFamily: DESIGN_TOKENS.typography.mono,
                fontSize: '14px',
                color: colors.muted,
                marginTop: '16px',
                paddingTop: '12px',
                borderTop: `1px dashed ${colors.border}`,
              }}
            >
              {subtitle}
            </p>
          )}

          {/* Handwritten-style byline */}
          <div
            style={{
              position: 'absolute',
              bottom: '-20px',
              right: '24px',
              transform: 'rotate(-3deg)',
              fontFamily: 'cursive, Georgia, serif',
              fontSize: '14px',
              color: colors.accent,
            }}
          >
            — Purpchicka ♥
          </div>
        </div>

        {/* Date annotation */}
        <div
          style={{
            marginTop: '32px',
            textAlign: 'center',
            fontFamily: DESIGN_TOKENS.typography.mono,
            fontSize: '11px',
            color: colors.muted,
            letterSpacing: '0.1em',
          }}
        >
          {metadata.date}
        </div>
      </header>

      {/* Lead paragraph as a clipping */}
      <div
        style={{
          maxWidth: '580px',
          margin: '16px auto 32px',
          padding: '0 24px',
        }}
      >
        <div
          style={{
            background: colors.paper,
            padding: '24px',
            transform: `rotate(${getRotation(1)})`,
            boxShadow: '3px 4px 8px rgba(0,0,0,0.06)',
            borderLeft: `4px solid ${colors.accent}`,
          }}
        >
          <p
            style={{
              fontSize: '17px',
              lineHeight: 1.8,
              fontStyle: 'italic',
              color: colors.text,
              margin: 0,
            }}
          >
            &ldquo;{lead}&rdquo;
          </p>
        </div>
      </div>

      {/* Scattered Polaroid Images */}
      {images && images.length > 0 && (
        <div
          style={{
            padding: '0 24px',
            maxWidth: '640px',
            margin: '24px auto',
            position: 'relative',
            minHeight: '200px',
          }}
        >
          {images.map((img, i) => (
            <div
              key={i}
              style={{
                position: 'relative',
                display: 'inline-block',
                margin: '16px',
                transform: `rotate(${getRotation(i + 2)})`,
              }}
            >
              <div
                style={{
                  background: colors.paper,
                  padding: '12px 12px 48px 12px',
                  boxShadow: '4px 6px 12px rgba(0,0,0,0.12)',
                }}
              >
                <img
                  src={img.url}
                  alt={img.caption}
                  style={{
                    width: '240px',
                    height: '180px',
                    objectFit: 'cover',
                    display: 'block',
                  }}
                />
                <div
                  style={{
                    marginTop: '8px',
                    fontFamily: 'cursive, Georgia, serif',
                    fontSize: '12px',
                    color: colors.muted,
                    textAlign: 'center',
                  }}
                >
                  {img.caption}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Body with varied column widths */}
      <div
        style={{
          padding: '24px',
          maxWidth: '640px',
          margin: '0 auto',
        }}
      >
        {body.split('\n\n').map((para, i) => (
          <div
            key={i}
            style={{
              marginLeft: i % 2 === 0 ? '0' : '24px',
              marginRight: i % 2 === 0 ? '24px' : '0',
              marginBottom: '24px',
            }}
          >
            <p
              style={{
                fontSize: '16px',
                lineHeight: 1.85,
                color: colors.text,
                margin: 0,
              }}
            >
              {para}
            </p>
          </div>
        ))}
      </div>

      {/* Findings as scattered paper clippings */}
      {findings.length > 0 && (
        <div
          style={{
            padding: '32px 24px',
            position: 'relative',
          }}
        >
          {/* Organic section break */}
          <div
            style={{
              textAlign: 'center',
              margin: '0 0 32px',
            }}
          >
            <span
              style={{
                fontFamily: 'cursive, Georgia, serif',
                fontSize: '18px',
                color: colors.accent,
              }}
            >
              ✦ discoveries ✦
            </span>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
              gap: '24px',
              maxWidth: '700px',
              margin: '0 auto',
            }}
          >
            {findings.map((f, i) => (
              <div
                key={i}
                style={{
                  background: colors.paper,
                  padding: '20px',
                  transform: `rotate(${getRotation(i + 2)})`,
                  boxShadow: '2px 3px 8px rgba(0,0,0,0.07)',
                  position: 'relative',
                }}
              >
                {/* Pin decoration */}
                <div
                  style={{
                    position: 'absolute',
                    top: '-6px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    background: colors.accent,
                    boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                  }}
                />
                {f.title && (
                  <div
                    style={{
                      fontSize: '12px',
                      fontWeight: 600,
                      color: colors.accent,
                      marginBottom: '8px',
                      textDecoration: 'underline',
                      textUnderlineOffset: '3px',
                    }}
                  >
                    {f.title}
                  </div>
                )}
                <p
                  style={{
                    fontSize: '14px',
                    lineHeight: 1.6,
                    color: colors.text,
                    margin: 0,
                  }}
                >
                  {f.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Highlighted quote card for recommendations */}
      {recommendations.length > 0 && (
        <div
          style={{
            padding: '32px 24px',
            maxWidth: '500px',
            margin: '0 auto',
          }}
        >
          <div
            style={{
              background: `linear-gradient(135deg, ${colors.paper} 0%, #fff9f0 100%)`,
              padding: '28px',
              transform: 'rotate(-1deg)',
              boxShadow: '4px 6px 12px rgba(0,0,0,0.08)',
              border: `2px solid ${colors.accent}`,
            }}
          >
            <div
              style={{
                fontFamily: 'cursive, Georgia, serif',
                fontSize: '14px',
                color: colors.accent,
                marginBottom: '16px',
              }}
            >
              ★ what to do next:
            </div>
            {recommendations.map((r, i) => (
              <p
                key={i}
                style={{
                  fontSize: '15px',
                  lineHeight: 1.6,
                  color: colors.text,
                  marginBottom: '12px',
                  paddingLeft: '16px',
                  position: 'relative',
                }}
              >
                <span
                  style={{
                    position: 'absolute',
                    left: 0,
                    color: colors.accent,
                  }}
                >
                  →
                </span>
                {r}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Bottom Line as signature card */}
      {bottomLine && (
        <div
          style={{
            padding: '32px 24px',
            maxWidth: '520px',
            margin: '0 auto',
          }}
        >
          <div
            style={{
              background: colors.paper,
              padding: '24px',
              transform: 'rotate(1deg)',
              boxShadow: '3px 5px 10px rgba(0,0,0,0.08)',
              borderTop: `4px solid ${colors.accent}`,
            }}
          >
            <div
              style={{
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
                color: colors.muted,
                marginBottom: '12px',
              }}
            >
              THE BOTTOM LINE
            </div>
            <p
              style={{
                fontFamily: DESIGN_TOKENS.typography.serif.elegant,
                fontSize: '18px',
                lineHeight: 1.5,
                fontWeight: 500,
                color: colors.text,
                margin: 0,
              }}
            >
              {bottomLine}
            </p>
          </div>
        </div>
      )}

      {/* Sources as paper scraps */}
      {sources.length > 0 && (
        <div
          style={{
            padding: '24px',
            maxWidth: '600px',
            margin: '0 auto',
          }}
        >
          <div
            style={{
              fontFamily: DESIGN_TOKENS.typography.mono,
              fontSize: '10px',
              letterSpacing: '0.1em',
              color: colors.muted,
              marginBottom: '16px',
              textTransform: 'uppercase',
            }}
          >
            research notes ({sources.length})
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
            {sources.map((src, i) => (
              <a
                key={i}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 12px',
                  background: colors.paper,
                  transform: `rotate(${getRotation(i + 3)})`,
                  boxShadow: '1px 2px 4px rgba(0,0,0,0.05)',
                  fontSize: '12px',
                  color: colors.text,
                  textDecoration: 'none',
                  fontFamily: DESIGN_TOKENS.typography.mono,
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={src.favicon} alt="" width={12} height={12} style={{ opacity: 0.8 }} />
                {src.domain}
              </a>
            ))}
          </div>
        </div>
      )}

      {/* Closing signature */}
      <footer
        style={{
          textAlign: 'center',
          padding: '48px 24px',
          borderTop: `1px dashed ${colors.border}`,
          marginTop: '32px',
        }}
      >
        <div
          style={{
            fontFamily: 'cursive, Georgia, serif',
            fontSize: '18px',
            color: colors.accent,
            marginBottom: '8px',
          }}
        >
          xoxo, Purpchicka
        </div>
        <div
          style={{
            fontSize: '11px',
            color: colors.muted,
          }}
        >
          crafted with ♥ by AlphaWave Research · {metadata.time}s
        </div>
      </footer>
    </article>
  );
}

export default EditorialScrapbook;

