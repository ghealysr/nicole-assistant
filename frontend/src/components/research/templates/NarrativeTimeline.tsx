'use client';

/**
 * Template 5: The Narrative Timeline
 * 
 * Design Philosophy: Scrollytelling-first. Story unfolds in beats.
 * Progress visibility. Documentary revelation style.
 * 
 * Author: nhealy44
 */

import { ResearchResponse } from '@/lib/hooks/useResearch';
import { DESIGN_TOKENS } from './templateTypes';
import { parseResearchData, ParsedResearchData } from './parseUtils';

interface NarrativeTimelineProps {
  data: ResearchResponse;
}

const colors = DESIGN_TOKENS.colors.timeline;

export function NarrativeTimeline({ data }: NarrativeTimelineProps) {
  const parsed: ParsedResearchData = parseResearchData(data);
  const { title, subtitle, lead, body, findings, recommendations, bottomLine, sources, metadata } = parsed;

  const bodyParagraphs = body.split('\n\n').filter(p => p.trim());

  // Create timeline beats
  const beats = [
    { type: 'context', title: 'Setting the Scene', content: lead },
    ...bodyParagraphs.slice(0, 2).map((p, i) => ({
      type: 'story',
      title: `Chapter ${i + 1}`,
      content: p,
    })),
    ...findings.slice(0, 4).map((f, i) => ({
      type: 'discovery',
      title: f.title || `Discovery ${i + 1}`,
      content: f.body,
    })),
    ...recommendations.slice(0, 2).map((r, i) => ({
      type: 'action',
      title: `Action ${i + 1}`,
      content: r,
    })),
  ];

  return (
    <article
      style={{
        background: colors.bg,
        color: colors.text,
        fontFamily: DESIGN_TOKENS.typography.sans.geometric,
        minHeight: '100%',
        position: 'relative',
      }}
    >
      {/* Progress bar at top */}
      <div
        style={{
          position: 'sticky',
          top: 0,
          left: 0,
          right: 0,
          height: '3px',
          background: colors.border,
          zIndex: 100,
        }}
      >
        <div
          style={{
            height: '100%',
            width: '100%',
            background: `linear-gradient(90deg, ${colors.accent} 0%, #ec4899 100%)`,
            transformOrigin: 'left',
          }}
        />
      </div>

      {/* Title Card with scroll prompt */}
      <section
        style={{
          minHeight: '70vh',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: '48px 24px',
          textAlign: 'center',
          position: 'relative',
        }}
      >
        {/* Author badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            background: colors.card,
            borderRadius: '24px',
            border: `1px solid ${colors.border}`,
            marginBottom: '32px',
          }}
        >
          <div
            style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              background: `linear-gradient(135deg, ${colors.accent} 0%, #ec4899 100%)`,
            }}
          />
          <span style={{ fontSize: '13px', color: colors.muted }}>
            Reported by <strong style={{ color: colors.text }}>nhealy44</strong>
          </span>
        </div>

        <h1
          style={{
            fontFamily: DESIGN_TOKENS.typography.serif.elegant,
            fontSize: 'clamp(36px, 6vw, 56px)',
            fontWeight: 700,
            lineHeight: 1.1,
            letterSpacing: '-0.02em',
            color: colors.text,
            margin: '0 0 24px',
            maxWidth: '800px',
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
              margin: '0 0 32px',
              maxWidth: '600px',
            }}
          >
            {subtitle}
          </p>
        )}

        {/* Metadata pills */}
        <div
          style={{
            display: 'flex',
            gap: '12px',
            flexWrap: 'wrap',
            justifyContent: 'center',
          }}
        >
          <span
            style={{
              padding: '6px 12px',
              background: colors.card,
              borderRadius: '4px',
              fontSize: '12px',
              color: colors.muted,
            }}
          >
            {metadata.date}
          </span>
          <span
            style={{
              padding: '6px 12px',
              background: colors.card,
              borderRadius: '4px',
              fontSize: '12px',
              color: colors.muted,
            }}
          >
            {beats.length} beats
          </span>
          <span
            style={{
              padding: '6px 12px',
              background: colors.accent,
              borderRadius: '4px',
              fontSize: '12px',
              color: '#fff',
            }}
          >
            {sources.length} sources
          </span>
        </div>

        {/* Scroll prompt */}
        <div
          style={{
            position: 'absolute',
            bottom: '32px',
            left: '50%',
            transform: 'translateX(-50%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '8px',
            color: colors.muted,
            animation: 'pulse 2s infinite',
          }}
        >
          <span style={{ fontSize: '11px', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Scroll to explore
          </span>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14M5 12l7 7 7-7" />
          </svg>
        </div>
      </section>

      {/* Timeline spine and beats */}
      <div
        style={{
          position: 'relative',
          paddingLeft: '48px',
          marginLeft: '24px',
        }}
      >
        {/* Vertical timeline line */}
        <div
          style={{
            position: 'absolute',
            left: '12px',
            top: '0',
            bottom: '0',
            width: '2px',
            background: `linear-gradient(180deg, ${colors.accent} 0%, ${colors.border} 50%, ${colors.accent} 100%)`,
          }}
        />

        {/* Beats */}
        {beats.map((beat, i) => (
          <div
            key={i}
            style={{
              position: 'relative',
              paddingBottom: '64px',
            }}
          >
            {/* Timeline node */}
            <div
              style={{
                position: 'absolute',
                left: '-42px',
                top: '4px',
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                background: beat.type === 'discovery' || beat.type === 'action'
                  ? `linear-gradient(135deg, ${colors.accent} 0%, #ec4899 100%)`
                  : colors.card,
                border: `2px solid ${colors.accent}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <span style={{ fontSize: '10px', fontWeight: 700, color: beat.type === 'discovery' || beat.type === 'action' ? '#fff' : colors.accent }}>
                {i + 1}
              </span>
            </div>

            {/* Beat content card */}
            <div
              style={{
                background: colors.card,
                borderRadius: DESIGN_TOKENS.borderRadius.lg,
                padding: '24px',
                border: `1px solid ${colors.border}`,
                maxWidth: '600px',
              }}
            >
              {/* Beat type label */}
              <div
                style={{
                  fontSize: '10px',
                  fontWeight: 600,
                  letterSpacing: '0.15em',
                  textTransform: 'uppercase',
                  color: beat.type === 'discovery' ? colors.accent : beat.type === 'action' ? '#22c55e' : colors.muted,
                  marginBottom: '8px',
                }}
              >
                {beat.type === 'discovery' ? '✦ Discovery' : beat.type === 'action' ? '→ Action' : beat.type === 'context' ? 'Context' : 'Narrative'}
              </div>

              <h3
                style={{
                  fontFamily: DESIGN_TOKENS.typography.serif.humanist,
                  fontSize: '18px',
                  fontWeight: 600,
                  color: colors.text,
                  margin: '0 0 12px',
                }}
              >
                {beat.title}
              </h3>

              <p
                style={{
                  fontSize: '15px',
                  lineHeight: 1.7,
                  color: colors.muted,
                  margin: 0,
                }}
              >
                {beat.content}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Turning point - Full-bleed impact statement */}
      {bottomLine && (
        <section
          style={{
            background: `linear-gradient(135deg, ${colors.accent} 0%, #7c3aed 50%, #ec4899 100%)`,
            padding: '80px 24px',
            textAlign: 'center',
            position: 'relative',
          }}
        >
          {/* Cinematic bars */}
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: '24px',
              background: 'black',
            }}
          />
          <div
            style={{
              position: 'absolute',
              bottom: 0,
              left: 0,
              right: 0,
              height: '24px',
              background: 'black',
            }}
          />

          <div
            style={{
              fontSize: '10px',
              fontWeight: 600,
              letterSpacing: '0.2em',
              textTransform: 'uppercase',
              color: 'rgba(255,255,255,0.7)',
              marginBottom: '16px',
            }}
          >
            The Bottom Line
          </div>
          <p
            style={{
              fontFamily: DESIGN_TOKENS.typography.serif.elegant,
              fontSize: 'clamp(24px, 4vw, 36px)',
              fontWeight: 600,
              lineHeight: 1.3,
              color: '#fff',
              margin: '0 auto',
              maxWidth: '700px',
            }}
          >
            {bottomLine}
          </p>
        </section>
      )}

      {/* Resolution and sources */}
      <section
        style={{
          padding: '64px 24px',
        }}
      >
        <div
          style={{
            maxWidth: '600px',
            margin: '0 auto',
          }}
        >
          {/* Sources */}
          <div
            style={{
              marginBottom: '48px',
            }}
          >
            <div
              style={{
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
                color: colors.muted,
                marginBottom: '16px',
              }}
            >
              Sources & References
            </div>
            <div style={{ display: 'grid', gap: '8px' }}>
              {sources.map((src, i) => (
                <a
                  key={i}
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '12px 16px',
                    background: colors.card,
                    borderRadius: DESIGN_TOKENS.borderRadius.md,
                    border: `1px solid ${colors.border}`,
                    textDecoration: 'none',
                    transition: 'border-color 0.2s',
                  }}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={src.favicon} alt="" width={20} height={20} style={{ borderRadius: '4px' }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '14px', color: colors.text }}>{src.title || src.domain}</div>
                    <div style={{ fontSize: '12px', color: colors.muted }}>{src.domain}</div>
                  </div>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={colors.muted} strokeWidth="2">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                    <polyline points="15 3 21 3 21 9" />
                    <line x1="10" y1="14" x2="21" y2="3" />
                  </svg>
                </a>
              ))}
            </div>
          </div>

          {/* Continue exploring prompt */}
          <div
            style={{
              textAlign: 'center',
              padding: '32px',
              background: colors.card,
              borderRadius: DESIGN_TOKENS.borderRadius.lg,
              border: `1px solid ${colors.border}`,
            }}
          >
            <div
              style={{
                fontSize: '11px',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                color: colors.muted,
                marginBottom: '8px',
              }}
            >
              Research Complete
            </div>
            <div
              style={{
                fontSize: '14px',
                color: colors.text,
                marginBottom: '16px',
              }}
            >
              Compiled in {metadata.time}s by AlphaWave Research
            </div>
            <div
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 24px',
                background: `linear-gradient(135deg, ${colors.accent} 0%, #ec4899 100%)`,
                borderRadius: '24px',
                color: '#fff',
                fontSize: '14px',
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              Continue Exploring ↗
            </div>
          </div>
        </div>
      </section>

      {/* Footer credit */}
      <footer
        style={{
          textAlign: 'center',
          padding: '24px',
          borderTop: `1px solid ${colors.border}`,
        }}
      >
        <div style={{ fontSize: '12px', color: colors.muted }}>
          Reported by <strong>nhealy44</strong> · Powered by AlphaWave Research
        </div>
      </footer>
    </article>
  );
}

export default NarrativeTimeline;

