'use client';

import React, { memo, useMemo } from 'react';

/**
 * Nicole's Orb Thinking Animation
 * 
 * A stunning, world-class thinking indicator featuring mystical glowing orbs
 * with lotus/mandala patterns. The animation includes:
 * 
 * 1. Pulsing glow effect on the central orb
 * 2. Sequential lighting of satellite orbs
 * 3. Rotating inner mandala patterns
 * 4. Floating particle effects
 * 5. Energy flow connections between orbs
 * 
 * Used as Nicole's premium thinking indicator during processing.
 */

// ============================================================================
// FLOATING PARTICLES - Ambient energy around the orbs
// ============================================================================

interface ParticleProps {
  index: number;
  totalParticles: number;
}

const FloatingParticle = memo(function FloatingParticle({ index, totalParticles }: ParticleProps) {
  // Deterministic positioning based on index
  const angle = (index / totalParticles) * 360;
  const radius = 35 + (index % 3) * 15;
  const size = 2 + (index % 3);
  const duration = 3 + (index % 5) * 0.5;
  const delay = (index % 8) * 0.25;
  
  // Color based on position - purple to cyan gradient
  const hue = 260 + (index / totalParticles) * 60;
  
  return (
    <div
      className="absolute rounded-full"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        left: '50%',
        top: '50%',
        backgroundColor: `hsl(${hue}, 80%, 70%)`,
        boxShadow: `0 0 ${size * 2}px hsl(${hue}, 80%, 70%)`,
        transform: `rotate(${angle}deg) translateX(${radius}px) translateY(-50%)`,
        animation: `orbFloat ${duration}s ease-in-out ${delay}s infinite`,
        opacity: 0.7,
      }}
    />
  );
});

// ============================================================================
// ENERGY RING - Glowing ring around the orbs
// ============================================================================

interface EnergyRingProps {
  isActive: boolean;
  size: number;
  delay: number;
}

const EnergyRing = memo(function EnergyRing({ isActive, size, delay }: EnergyRingProps) {
  if (!isActive) return null;
  
  return (
    <div
      className="absolute left-1/2 top-1/2 rounded-full pointer-events-none"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        transform: 'translate(-50%, -50%)',
        border: '1px solid rgba(147, 112, 219, 0.4)',
        boxShadow: `
          0 0 10px rgba(147, 112, 219, 0.3),
          inset 0 0 10px rgba(147, 112, 219, 0.1)
        `,
        animation: `energyPulse 2s ease-in-out ${delay}s infinite`,
      }}
    />
  );
});

// ============================================================================
// MAIN ORB COMPONENT - Single glowing orb with mandala
// ============================================================================

interface OrbProps {
  isActive: boolean;
  isPrimary?: boolean;
  index?: number;
  totalOrbs?: number;
}

const GlowingOrb = memo(function GlowingOrb({ 
  isActive, 
  isPrimary = false,
  index = 0,
  totalOrbs = 1
}: OrbProps) {
  const size = isPrimary ? 64 : 40;
  const glowIntensity = isPrimary ? 20 : 12;
  const animationDelay = isPrimary ? 0 : (index * 0.15);
  
  return (
    <div
      className="relative flex-shrink-0"
      style={{
        width: `${size}px`,
        height: `${size}px`,
      }}
    >
      {/* Outer glow ring */}
      <div
        className="absolute inset-0 rounded-full"
        style={{
          background: isActive 
            ? `radial-gradient(circle, rgba(147, 112, 219, 0.4) 0%, rgba(100, 149, 237, 0.2) 50%, transparent 70%)`
            : 'none',
          transform: 'scale(1.5)',
          animation: isActive ? `orbGlow 2s ease-in-out ${animationDelay}s infinite` : 'none',
        }}
      />
      
      {/* Outer rim glow - pink/purple ring like the image */}
      <div
        className="absolute rounded-full"
        style={{
          inset: '-3px',
          background: isActive ? `
            conic-gradient(from 0deg at 50% 50%,
              rgba(255,100,200,0.8) 0deg,
              rgba(200,150,255,0.9) 45deg,
              rgba(147,112,219,0.7) 90deg,
              rgba(100,149,237,0.8) 135deg,
              rgba(147,112,219,0.7) 180deg,
              rgba(200,150,255,0.9) 225deg,
              rgba(255,100,200,0.8) 270deg,
              rgba(200,150,255,0.9) 315deg,
              rgba(255,100,200,0.8) 360deg
            )
          ` : 'rgba(147,112,219,0.3)',
          filter: isActive ? 'blur(2px)' : 'none',
          animation: isActive ? `orbRotate 6s linear infinite` : 'none',
          opacity: isActive ? 0.8 : 0.4,
        }}
      />

      {/* Inner rotating mandala glow */}
      <div
        className="absolute inset-0 rounded-full overflow-hidden"
        style={{
          boxShadow: isActive 
            ? `
              0 0 ${glowIntensity}px rgba(147, 112, 219, 0.6),
              0 0 ${glowIntensity * 2}px rgba(100, 149, 237, 0.4),
              0 0 ${glowIntensity * 3}px rgba(147, 112, 219, 0.2),
              inset 0 0 ${glowIntensity / 2}px rgba(255, 255, 255, 0.3)
            `
            : `0 0 ${glowIntensity / 2}px rgba(147, 112, 219, 0.3)`,
          animation: isActive ? `orbPulse 1.5s ease-in-out ${animationDelay}s infinite` : 'none',
        }}
      >
        {/* The orb - rendered as CSS for stunning effect */}
        <div
          className="w-full h-full rounded-full"
          style={{
            animation: isActive ? `orbRotate 8s linear infinite` : 'none',
            animationDelay: `${animationDelay}s`,
            background: `
              radial-gradient(ellipse at 30% 30%, rgba(255,255,255,0.4) 0%, transparent 40%),
              radial-gradient(ellipse at 70% 70%, rgba(100,149,237,0.3) 0%, transparent 50%),
              conic-gradient(from 0deg at 50% 50%, 
                rgba(147,112,219,0.9) 0deg, 
                rgba(100,149,237,0.8) 60deg, 
                rgba(147,112,219,0.9) 120deg,
                rgba(100,149,237,0.8) 180deg,
                rgba(147,112,219,0.9) 240deg,
                rgba(100,149,237,0.8) 300deg,
                rgba(147,112,219,0.9) 360deg
              ),
              radial-gradient(circle at 50% 50%, 
                rgba(30,20,50,0.9) 0%, 
                rgba(20,10,40,0.95) 50%,
                rgba(10,5,30,1) 100%
              )
            `,
            boxShadow: isActive ? `
              inset 0 0 ${size/4}px rgba(147,112,219,0.5),
              inset 0 0 ${size/8}px rgba(255,255,255,0.2)
            ` : 'none',
          }}
        >
          {/* Inner lotus/mandala pattern */}
          <svg 
            viewBox="0 0 100 100" 
            className="w-full h-full"
            style={{ 
              opacity: 0.7,
              filter: 'drop-shadow(0 0 2px rgba(147,112,219,0.5))',
            }}
          >
            {/* Center glow */}
            <defs>
              <radialGradient id="centerGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="rgba(200,180,255,0.8)" />
                <stop offset="50%" stopColor="rgba(147,112,219,0.4)" />
                <stop offset="100%" stopColor="transparent" />
              </radialGradient>
              <linearGradient id="petalGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="rgba(100,149,237,0.9)" />
                <stop offset="50%" stopColor="rgba(147,112,219,0.8)" />
                <stop offset="100%" stopColor="rgba(200,180,255,0.9)" />
              </linearGradient>
            </defs>
            
            {/* Lotus petals */}
            {[0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330].map((angle, i) => (
              <path
                key={i}
                d={`M50,50 Q${50 + Math.cos((angle - 15) * Math.PI / 180) * 25},${50 + Math.sin((angle - 15) * Math.PI / 180) * 25} ${50 + Math.cos(angle * Math.PI / 180) * 40},${50 + Math.sin(angle * Math.PI / 180) * 40} Q${50 + Math.cos((angle + 15) * Math.PI / 180) * 25},${50 + Math.sin((angle + 15) * Math.PI / 180) * 25} 50,50`}
                fill="url(#petalGradient)"
                opacity={0.6 + (i % 2) * 0.2}
                style={{
                  filter: 'drop-shadow(0 0 3px rgba(147,112,219,0.5))',
                }}
              />
            ))}
            
            {/* Inner ring */}
            <circle cx="50" cy="50" r="15" fill="none" stroke="url(#petalGradient)" strokeWidth="0.5" opacity="0.5" />
            <circle cx="50" cy="50" r="10" fill="url(#centerGlow)" />
            
            {/* Center sparkle */}
            <circle cx="50" cy="50" r="3" fill="rgba(255,255,255,0.9)" />
          </svg>
        </div>
      </div>
      
      {/* Center light point */}
      {isPrimary && isActive && (
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
          style={{
            width: '8px',
            height: '8px',
            background: 'radial-gradient(circle, rgba(255,255,255,0.9) 0%, rgba(200,180,255,0.6) 50%, transparent 70%)',
            animation: 'centerGlow 1s ease-in-out infinite',
          }}
        />
      )}
    </div>
  );
});

// ============================================================================
// CONNECTING ENERGY BEAMS - Between orbs
// ============================================================================

interface EnergyBeamProps {
  isActive: boolean;
  fromIndex: number;
  toIndex: number;
}

const EnergyBeam = memo(function EnergyBeam({ isActive, fromIndex, toIndex }: EnergyBeamProps) {
  if (!isActive) return null;
  
  const delay = (fromIndex + toIndex) * 0.1;
  
  return (
    <div
      className="absolute h-[2px] pointer-events-none"
      style={{
        width: '20px',
        background: 'linear-gradient(90deg, transparent, rgba(147, 112, 219, 0.5), transparent)',
        animation: `beamFlow 1s ease-in-out ${delay}s infinite`,
        opacity: 0.6,
      }}
    />
  );
});

// ============================================================================
// FULL ANIMATION CONTAINER
// ============================================================================

export interface NicoleOrbAnimationProps {
  /** Whether the animation is active */
  isActive: boolean;
  /** Size variant */
  size?: 'small' | 'medium' | 'large';
  /** Show single orb or multiple */
  variant?: 'single' | 'triple' | 'full';
  /** Optional className */
  className?: string;
  /** Show particles */
  showParticles?: boolean;
}

export const NicoleOrbAnimation = memo(function NicoleOrbAnimation({
  isActive,
  size = 'medium',
  variant = 'single',
  className = '',
  showParticles = true,
}: NicoleOrbAnimationProps) {
  // Size configurations
  const sizeConfig = {
    small: { container: 48, orbSize: 32 },
    medium: { container: 80, orbSize: 48 },
    large: { container: 120, orbSize: 64 },
  };
  
  const config = sizeConfig[size];
  const particleCount = size === 'small' ? 8 : size === 'medium' ? 12 : 20;
  
  // Memoize particles to prevent recreation
  const particles = useMemo(() => {
    if (!showParticles || !isActive) return null;
    return Array.from({ length: particleCount }, (_, i) => (
      <FloatingParticle key={i} index={i} totalParticles={particleCount} />
    ));
  }, [showParticles, isActive, particleCount]);
  
  return (
    <div 
      className={`relative flex items-center justify-center ${className}`}
      style={{
        width: variant === 'full' ? '200px' : `${config.container}px`,
        height: `${config.container}px`,
      }}
    >
      {/* CSS Animations */}
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes orbGlow {
          0%, 100% { transform: scale(1.5); opacity: 0.6; }
          50% { transform: scale(1.8); opacity: 1; }
        }
        
        @keyframes orbPulse {
          0%, 100% { 
            box-shadow: 
              0 0 20px rgba(147, 112, 219, 0.6),
              0 0 40px rgba(100, 149, 237, 0.4),
              0 0 60px rgba(147, 112, 219, 0.2),
              inset 0 0 10px rgba(255, 255, 255, 0.3);
          }
          50% { 
            box-shadow: 
              0 0 30px rgba(147, 112, 219, 0.8),
              0 0 60px rgba(100, 149, 237, 0.5),
              0 0 90px rgba(147, 112, 219, 0.3),
              inset 0 0 15px rgba(255, 255, 255, 0.5);
          }
        }
        
        @keyframes orbRotate {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        @keyframes centerGlow {
          0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.8; }
          50% { transform: translate(-50%, -50%) scale(1.5); opacity: 1; }
        }
        
        @keyframes orbFloat {
          0%, 100% { 
            opacity: 0.4; 
            transform: rotate(var(--angle)) translateX(var(--radius)) translateY(-50%) scale(0.8);
          }
          50% { 
            opacity: 0.9; 
            transform: rotate(calc(var(--angle) + 10deg)) translateX(calc(var(--radius) + 5px)) translateY(-50%) scale(1.2);
          }
        }
        
        @keyframes energyPulse {
          0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.5; }
          50% { transform: translate(-50%, -50%) scale(1.1); opacity: 0.8; }
        }
        
        @keyframes beamFlow {
          0% { opacity: 0; transform: translateX(-10px); }
          50% { opacity: 0.8; }
          100% { opacity: 0; transform: translateX(10px); }
        }
        
        @keyframes sequentialLight {
          0%, 20%, 100% { opacity: 0.4; transform: scale(0.9); }
          10% { opacity: 1; transform: scale(1.1); }
        }
      `}} />
      
      {/* Energy rings */}
      {isActive && variant !== 'small' && (
        <>
          <EnergyRing isActive={isActive} size={config.container * 0.9} delay={0} />
          <EnergyRing isActive={isActive} size={config.container * 1.3} delay={0.3} />
        </>
      )}
      
      {/* Floating particles */}
      {particles}
      
      {/* Orbs based on variant */}
      {variant === 'single' && (
        <GlowingOrb isActive={isActive} isPrimary />
      )}
      
      {variant === 'triple' && (
        <div className="flex items-center gap-1">
          <GlowingOrb isActive={isActive} index={0} totalOrbs={3} />
          <GlowingOrb isActive={isActive} isPrimary index={1} totalOrbs={3} />
          <GlowingOrb isActive={isActive} index={2} totalOrbs={3} />
        </div>
      )}
      
      {variant === 'full' && (
        <div className="flex items-center gap-0.5">
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              style={{
                animation: isActive ? `sequentialLight 2s ease-in-out ${i * 0.2}s infinite` : 'none',
              }}
            >
              <GlowingOrb 
                isActive={isActive} 
                isPrimary={i === 2}
                index={i}
                totalOrbs={5}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
});

// ============================================================================
// COMPACT THINKING INDICATOR - For use in chat headers
// ============================================================================

export interface ThinkingIndicatorProps {
  isThinking: boolean;
  label?: string;
}

export const NicoleThinkingIndicator = memo(function NicoleThinkingIndicator({
  isThinking,
  label = 'Nicole is thinking',
}: ThinkingIndicatorProps) {
  if (!isThinking) return null;
  
  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-[#1a1a2e]/50 backdrop-blur-sm border border-purple-500/20">
      <NicoleOrbAnimation 
        isActive={isThinking} 
        size="small" 
        variant="single"
        showParticles={false}
      />
      <span className="text-sm text-purple-200/80 font-medium">
        {label}
        <span className="inline-flex ml-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-1 h-1 rounded-full bg-purple-400 mx-0.5"
              style={{
                animation: `pulse 1s ease-in-out ${i * 0.2}s infinite`,
              }}
            />
          ))}
        </span>
      </span>
    </div>
  );
});

export default NicoleOrbAnimation;

