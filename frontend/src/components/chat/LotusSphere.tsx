'use client';

import React, { useEffect, useRef, memo, useMemo } from 'react';

/**
 * LOTUS SPHERE - Nicole Edition v6
 * 
 * Refined crystal-clear aesthetic with luminous petals
 * - Clear glass sphere (not tinted)
 * - Bright, ethereal petal glow
 * - Soft ambient light without heavy shadows
 * - Elegant, airy appearance
 */

export type ThinkingState = 'default' | 'searching' | 'thinking' | 'processing' | 'speaking';

export interface LotusSphereProps {
  state?: ThinkingState;
  size?: number;
  className?: string;
  isActive?: boolean;
}

const noise = (x: number, y: number, t: number): number => {
  return Math.sin(x * 0.05 + t) * Math.cos(y * 0.05 + t * 0.7) * 
         Math.sin((x + y) * 0.03 + t * 0.5);
};

const drawPetal = (
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  angle: number,
  innerRadius: number,
  outerRadius: number,
  width: number,
  isOuter: boolean,
  glowIntensity: number,
  scale: number
) => {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(angle);
  
  const tipX = outerRadius;
  const tipY = 0;
  const baseWidth = width;
  
  ctx.beginPath();
  
  if (isOuter) {
    ctx.moveTo(innerRadius, 0);
    ctx.bezierCurveTo(
      innerRadius + (outerRadius - innerRadius) * 0.3, -baseWidth * 0.8,
      outerRadius - 20 * scale, -baseWidth * 0.4,
      tipX, tipY
    );
    ctx.bezierCurveTo(
      outerRadius - 20 * scale, baseWidth * 0.4,
      innerRadius + (outerRadius - innerRadius) * 0.3, baseWidth * 0.8,
      innerRadius, 0
    );
  } else {
    ctx.moveTo(innerRadius, 0);
    ctx.bezierCurveTo(
      innerRadius + (outerRadius - innerRadius) * 0.4, -baseWidth * 0.6,
      outerRadius - 10 * scale, -baseWidth * 0.15,
      tipX, tipY
    );
    ctx.bezierCurveTo(
      outerRadius - 10 * scale, baseWidth * 0.15,
      innerRadius + (outerRadius - innerRadius) * 0.4, baseWidth * 0.6,
      innerRadius, 0
    );
  }
  
  ctx.closePath();
  
  // Lighter, more luminous purple gradient - feels like glowing petals
  const fillGrad = ctx.createLinearGradient(innerRadius, 0, outerRadius, 0);
  fillGrad.addColorStop(0, `rgba(100, 60, 160, ${0.7 * glowIntensity})`);
  fillGrad.addColorStop(0.4, `rgba(130, 80, 190, ${0.65 * glowIntensity})`);
  fillGrad.addColorStop(0.7, `rgba(160, 110, 220, ${0.55 * glowIntensity})`);
  fillGrad.addColorStop(1, `rgba(190, 140, 240, ${0.45 * glowIntensity})`);
  ctx.fillStyle = fillGrad;
  ctx.fill();
  
  // Bright edge glow - ethereal light
  const glowColors = [
    { width: Math.max(1, 6 * scale), color: `rgba(200, 170, 255, ${0.15 * glowIntensity})` },
    { width: Math.max(0.5, 3 * scale), color: `rgba(220, 190, 255, ${0.35 * glowIntensity})` },
    { width: Math.max(0.5, 1.5 * scale), color: `rgba(240, 220, 255, ${0.6 * glowIntensity})` },
  ];
  
  glowColors.forEach(g => {
    ctx.strokeStyle = g.color;
    ctx.lineWidth = g.width;
    ctx.stroke();
  });
  
  // Inner vein - subtle
  ctx.beginPath();
  ctx.moveTo(innerRadius + 10 * scale, 0);
  ctx.lineTo(outerRadius - 15 * scale, 0);
  ctx.strokeStyle = `rgba(220, 200, 255, ${0.2 * glowIntensity})`;
  ctx.lineWidth = Math.max(0.5, 1 * scale);
  ctx.stroke();
  
  ctx.restore();
};

export const LotusSphere = memo(function LotusSphere({
  state = 'default',
  size = 96,
  className = '',
  isActive = true,
}: LotusSphereProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);
  const timeRef = useRef(0);
  
  const prefersReducedMotion = typeof window !== 'undefined' 
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches 
    : false;
  
  const energyBursts = useMemo(() => 
    Array.from({ length: 8 }, (_, i) => ({
      angle: (i / 8) * Math.PI * 2 + Math.random() * 0.3,
      speed: 0.8 + Math.random() * 0.4,
      length: 35 + Math.random() * 25,
      offset: Math.random() * Math.PI * 2,
    })), []
  );
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const dpr = window.devicePixelRatio || 1;
    const canvasSize = Math.floor(size * dpr);
    canvas.width = canvasSize;
    canvas.height = canvasSize;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;
    ctx.scale(dpr, dpr);
    
    const cx = size / 2;
    const cy = size / 2;
    const sphereRadius = size * 0.42;
    const scale = size / 500;
    
    const animate = () => {
      if (!isActive && !prefersReducedMotion) {
        timeRef.current = 0;
      } else {
        timeRef.current += 0.016;
      }
      
      const time = timeRef.current;
      
      let rotationSpeed: number, glowPulse: number, centerSize: number;
      let glowColor = { r: 255, g: 255, b: 255 };
      
      if (state === 'default' || prefersReducedMotion) {
        rotationSpeed = prefersReducedMotion ? 0 : 0.08;
        glowPulse = 0.9 + (prefersReducedMotion ? 0 : Math.sin(time) * 0.1);
        centerSize = (20 + (prefersReducedMotion ? 0 : Math.sin(time * 1.2) * 6)) * scale;
      } else if (state === 'searching') {
        rotationSpeed = 0.1;
        glowPulse = 0.95;
        centerSize = (18 + Math.sin(time * 2.5) * 14) * scale;
      } else if (state === 'thinking') {
        rotationSpeed = 0.8;
        glowPulse = 0.95 + Math.sin(time * 2) * 0.05;
        centerSize = (20 + Math.sin(time * 3) * 8) * scale;
        glowColor = { r: 220, g: 255, b: 220 };
      } else if (state === 'processing') {
        rotationSpeed = 0.12;
        glowPulse = 0.85 + Math.sin(time * 4) * 0.15;
        centerSize = (22 + Math.sin(time * 4) * 10) * scale;
      } else if (state === 'speaking') {
        rotationSpeed = 0.05;
        glowPulse = 0.98 + Math.sin(time * 3) * 0.02;
        centerSize = (24 + Math.sin(time * 2) * 4) * scale;
        glowColor = { r: 200, g: 230, b: 255 };
      } else {
        rotationSpeed = 0.08;
        glowPulse = 0.9;
        centerSize = 20 * scale;
      }
      
      ctx.clearRect(0, 0, size, size);
      
      // Soft, subtle ambient glow - light lavender, not dark
      const ambientGlow = ctx.createRadialGradient(cx, cy, sphereRadius * 0.5, cx, cy, sphereRadius * 1.2);
      ambientGlow.addColorStop(0, 'rgba(180, 150, 220, 0.08)');
      ambientGlow.addColorStop(0.6, 'rgba(160, 130, 200, 0.04)');
      ambientGlow.addColorStop(1, 'rgba(140, 110, 180, 0)');
      ctx.fillStyle = ambientGlow;
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius * 1.2, 0, Math.PI * 2);
      ctx.fill();
      
      // Clear glass sphere - very subtle, transparent
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius, 0, Math.PI * 2);
      
      // Light, airy gradient - clear glass not tinted
      const glassGrad = ctx.createRadialGradient(
        cx - sphereRadius * 0.3, cy - sphereRadius * 0.3, 0,
        cx, cy, sphereRadius
      );
      glassGrad.addColorStop(0, 'rgba(255, 255, 255, 0.12)');
      glassGrad.addColorStop(0.4, 'rgba(240, 235, 250, 0.08)');
      glassGrad.addColorStop(0.7, 'rgba(220, 210, 240, 0.1)');
      glassGrad.addColorStop(0.9, 'rgba(200, 180, 230, 0.15)');
      glassGrad.addColorStop(1, 'rgba(180, 160, 220, 0.25)');
      ctx.fillStyle = glassGrad;
      ctx.fill();
      
      const rotation = time * rotationSpeed;
      
      // Light center glow
      const centerGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, sphereRadius * 0.4);
      centerGlow.addColorStop(0, 'rgba(200, 170, 240, 0.25)');
      centerGlow.addColorStop(0.5, 'rgba(180, 150, 220, 0.12)');
      centerGlow.addColorStop(1, 'rgba(160, 130, 200, 0)');
      
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius * 0.4, 0, Math.PI * 2);
      ctx.fillStyle = centerGlow;
      ctx.fill();
      
      // Processing energy bursts
      if (state === 'processing' && !prefersReducedMotion) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(cx, cy, sphereRadius - 2 * scale, 0, Math.PI * 2);
        ctx.clip();
        
        energyBursts.forEach((burst) => {
          const progress = ((time * burst.speed + burst.offset) % 1.5) / 1.5;
          const startRadius = sphereRadius - 10 * scale;
          const endRadius = 15 * scale;
          const currentRadius = startRadius - (startRadius - endRadius) * progress;
          
          const burstX = cx + Math.cos(burst.angle) * currentRadius;
          const burstY = cy + Math.sin(burst.angle) * currentRadius;
          
          const fadeOut = progress > 0.7 ? 1 - ((progress - 0.7) / 0.3) : 1;
          const fadeIn = progress < 0.15 ? progress / 0.15 : 1;
          const opacity = fadeIn * fadeOut;
          
          if (opacity > 0.05) {
            const burstGrad = ctx.createRadialGradient(
              burstX, burstY, 0,
              burstX, burstY, 15 * scale
            );
            burstGrad.addColorStop(0, `rgba(255, 240, 200, ${0.4 * opacity})`);
            burstGrad.addColorStop(0.5, `rgba(255, 220, 150, ${0.2 * opacity})`);
            burstGrad.addColorStop(1, 'rgba(255, 200, 100, 0)');
            
            ctx.beginPath();
            ctx.arc(burstX, burstY, 15 * scale, 0, Math.PI * 2);
            ctx.fillStyle = burstGrad;
            ctx.fill();
          }
        });
        
        ctx.restore();
      }
      
      // Outer petals
      const outerPetalInner = sphereRadius * 0.26;
      const outerPetalOuter = sphereRadius * 0.80;
      const outerPetalWidth = sphereRadius * 0.22;
      
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + rotation + Math.PI / 8;
        drawPetal(ctx, cx, cy, angle, outerPetalInner, outerPetalOuter, outerPetalWidth, true, glowPulse, scale);
      }
      
      // Inner petals
      const innerPetalInner = sphereRadius * 0.15;
      const innerPetalOuter = sphereRadius * 0.58;
      const innerPetalWidth = sphereRadius * 0.17;
      
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + rotation;
        drawPetal(ctx, cx, cy, angle, innerPetalInner, innerPetalOuter, innerPetalWidth, false, glowPulse, scale);
      }
      
      // Center radiating lines - brighter
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rotation);
      
      const lineInner = sphereRadius * 0.06;
      const lineOuter = sphereRadius * 0.20;
      
      for (let i = 0; i < 16; i++) {
        const angle = (i / 16) * Math.PI * 2;
        ctx.beginPath();
        ctx.moveTo(Math.cos(angle) * lineInner, Math.sin(angle) * lineInner);
        ctx.lineTo(Math.cos(angle) * lineOuter, Math.sin(angle) * lineOuter);
        ctx.strokeStyle = `rgba(220, 200, 255, ${0.3 * glowPulse})`;
        ctx.lineWidth = Math.max(0.5, 1 * scale);
        ctx.stroke();
      }
      
      ctx.restore();
      
      // Luminous center glow
      const { r, g, b } = glowColor;
      
      // Soft ethereal smoke
      const smokeLayers = 4;
      for (let layer = 0; layer < smokeLayers; layer++) {
        const noiseVal = noise(layer * 50, time * 100, time * 2);
        const offsetX = noiseVal * 5 * scale;
        const offsetY = noise(layer * 30 + 100, time * 80, time * 1.5) * 5 * scale;
        const sizeVariation = 1 + noise(layer * 20, time * 60, time) * 0.1;
        
        const layerSize = centerSize * sizeVariation * (1 + layer * 0.25);
        const layerOpacity = 0.12 / (layer + 1);
        
        const smokeGrad = ctx.createRadialGradient(
          cx + offsetX, cy + offsetY, 0,
          cx + offsetX, cy + offsetY, layerSize
        );
        smokeGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${layerOpacity * 2})`);
        smokeGrad.addColorStop(0.6, `rgba(${Math.floor(r * 0.95)}, ${Math.floor(g * 0.95)}, ${Math.floor(b * 0.97)}, ${layerOpacity})`);
        smokeGrad.addColorStop(1, `rgba(${Math.floor(r * 0.9)}, ${Math.floor(g * 0.9)}, ${Math.floor(b * 0.95)}, 0)`);
        
        ctx.beginPath();
        ctx.arc(cx + offsetX, cy + offsetY, layerSize, 0, Math.PI * 2);
        ctx.fillStyle = smokeGrad;
        ctx.fill();
      }
      
      // Outer halo - softer
      const haloWobble = noise(0, 0, time * 2) * 3 * scale;
      const haloSize = centerSize * 2 + haloWobble;
      const haloGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, haloSize);
      haloGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.18)`);
      haloGrad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, 0.08)`);
      haloGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, haloSize, 0, Math.PI * 2);
      ctx.fillStyle = haloGrad;
      ctx.fill();
      
      // Inner core - bright
      const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, centerSize * 0.7);
      coreGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.9)`);
      coreGrad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, 0.5)`);
      coreGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, centerSize * 0.7, 0, Math.PI * 2);
      ctx.fillStyle = coreGrad;
      ctx.fill();
      
      // Center bright point
      const dotSize = Math.max(2, 4 * scale);
      const dotGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, dotSize);
      dotGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 1)`);
      dotGrad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, 0.6)`);
      dotGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, dotSize, 0, Math.PI * 2);
      ctx.fillStyle = dotGrad;
      ctx.fill();
      
      // Glass rim - delicate iridescent edge
      const rimWidth = Math.max(1, 2 * scale);
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius, 0, Math.PI * 2);
      
      const rimGrad = ctx.createLinearGradient(
        cx - sphereRadius, cy - sphereRadius,
        cx + sphereRadius, cy + sphereRadius
      );
      rimGrad.addColorStop(0, 'rgba(220, 200, 255, 0.4)');
      rimGrad.addColorStop(0.3, 'rgba(200, 180, 240, 0.3)');
      rimGrad.addColorStop(0.5, 'rgba(180, 160, 230, 0.35)');
      rimGrad.addColorStop(0.7, 'rgba(200, 180, 240, 0.3)');
      rimGrad.addColorStop(1, 'rgba(220, 200, 255, 0.4)');
      ctx.strokeStyle = rimGrad;
      ctx.lineWidth = rimWidth;
      ctx.stroke();
      
      // Top highlight - crisp
      const highlightX = cx - sphereRadius * 0.35;
      const highlightY = cy - sphereRadius * 0.35;
      const highlightW = sphereRadius * 0.20;
      const highlightH = sphereRadius * 0.08;
      
      ctx.beginPath();
      ctx.ellipse(highlightX, highlightY, highlightW, highlightH, -Math.PI / 4, 0, Math.PI * 2);
      const highlight = ctx.createRadialGradient(highlightX, highlightY, 0, highlightX, highlightY, highlightW);
      highlight.addColorStop(0, 'rgba(255, 255, 255, 0.5)');
      highlight.addColorStop(0.5, 'rgba(255, 255, 255, 0.2)');
      highlight.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = highlight;
      ctx.fill();
      
      // Secondary smaller highlight
      const highlight2X = cx - sphereRadius * 0.15;
      const highlight2Y = cy - sphereRadius * 0.5;
      const highlight2R = sphereRadius * 0.06;
      
      ctx.beginPath();
      ctx.arc(highlight2X, highlight2Y, highlight2R, 0, Math.PI * 2);
      const highlight2 = ctx.createRadialGradient(highlight2X, highlight2Y, 0, highlight2X, highlight2Y, highlight2R);
      highlight2.addColorStop(0, 'rgba(255, 255, 255, 0.6)');
      highlight2.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = highlight2;
      ctx.fill();
      
      if (isActive && !prefersReducedMotion) {
        animationRef.current = requestAnimationFrame(animate);
      }
    };
    
    animate();
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [size, state, isActive, prefersReducedMotion, energyBursts]);
  
  return (
    <canvas 
      ref={canvasRef}
      className={className}
      style={{
        filter: isActive ? 'drop-shadow(0 0 8px rgba(180, 150, 220, 0.3))' : 'none',
        display: 'block',
      }}
      aria-label="Nicole is thinking"
      role="status"
      aria-live="polite"
    />
  );
});

export default LotusSphere;
