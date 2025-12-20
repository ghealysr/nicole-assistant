'use client';

import React, { useEffect, useRef, memo, useMemo } from 'react';

/**
 * LOTUS SPHERE - Nicole Edition v7
 * 
 * Refined crystal aesthetic with purple border for depth
 * - Clear glass sphere with subtle purple rim
 * - Luminous petal glow
 * - Elegant, polished appearance
 * - Purple stroke makes it look rounder/more defined
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
  
  // Rich purple gradient - more vibrant
  const fillGrad = ctx.createLinearGradient(innerRadius, 0, outerRadius, 0);
  fillGrad.addColorStop(0, `rgba(90, 50, 150, ${0.85 * glowIntensity})`);
  fillGrad.addColorStop(0.4, `rgba(120, 70, 180, ${0.75 * glowIntensity})`);
  fillGrad.addColorStop(0.7, `rgba(150, 100, 210, ${0.65 * glowIntensity})`);
  fillGrad.addColorStop(1, `rgba(180, 130, 235, ${0.55 * glowIntensity})`);
  ctx.fillStyle = fillGrad;
  ctx.fill();
  
  // Bright edge glow
  const glowColors = [
    { width: Math.max(1, 5 * scale), color: `rgba(200, 170, 255, ${0.2 * glowIntensity})` },
    { width: Math.max(0.5, 2.5 * scale), color: `rgba(220, 195, 255, ${0.4 * glowIntensity})` },
    { width: Math.max(0.5, 1.2 * scale), color: `rgba(240, 225, 255, ${0.7 * glowIntensity})` },
  ];
  
  glowColors.forEach(g => {
    ctx.strokeStyle = g.color;
    ctx.lineWidth = g.width;
    ctx.stroke();
  });
  
  // Inner vein
  ctx.beginPath();
  ctx.moveTo(innerRadius + 8 * scale, 0);
  ctx.lineTo(outerRadius - 12 * scale, 0);
  ctx.strokeStyle = `rgba(230, 210, 255, ${0.25 * glowIntensity})`;
  ctx.lineWidth = Math.max(0.5, 0.8 * scale);
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
        rotationSpeed = prefersReducedMotion ? 0 : 0.06;
        glowPulse = 0.92 + (prefersReducedMotion ? 0 : Math.sin(time * 0.8) * 0.08);
        centerSize = (18 + (prefersReducedMotion ? 0 : Math.sin(time * 1.0) * 5)) * scale;
      } else if (state === 'searching') {
        rotationSpeed = 0.15;
        glowPulse = 0.9 + Math.sin(time * 2) * 0.1;
        centerSize = (16 + Math.sin(time * 2.5) * 12) * scale;
        glowColor = { r: 255, g: 240, b: 200 }; // Warm yellow for searching
      } else if (state === 'thinking') {
        rotationSpeed = 0.6;
        glowPulse = 0.95 + Math.sin(time * 2.5) * 0.05;
        centerSize = (18 + Math.sin(time * 3) * 8) * scale;
        glowColor = { r: 200, g: 255, b: 200 }; // Green for thinking
      } else if (state === 'processing') {
        rotationSpeed = 0.1;
        glowPulse = 0.85 + Math.sin(time * 4) * 0.15;
        centerSize = (20 + Math.sin(time * 4) * 10) * scale;
        glowColor = { r: 255, g: 200, b: 150 }; // Orange for processing
      } else if (state === 'speaking') {
        rotationSpeed = 0.04;
        glowPulse = 0.98 + Math.sin(time * 3) * 0.02;
        centerSize = (22 + Math.sin(time * 2) * 4) * scale;
        glowColor = { r: 180, g: 220, b: 255 }; // Blue for speaking
      } else {
        rotationSpeed = 0.06;
        glowPulse = 0.92;
        centerSize = 18 * scale;
      }
      
      ctx.clearRect(0, 0, size, size);
      
      // Outer purple glow ring - creates depth
      const outerGlow = ctx.createRadialGradient(cx, cy, sphereRadius * 0.85, cx, cy, sphereRadius * 1.15);
      outerGlow.addColorStop(0, 'rgba(160, 130, 200, 0)');
      outerGlow.addColorStop(0.5, 'rgba(150, 120, 190, 0.12)');
      outerGlow.addColorStop(0.8, 'rgba(140, 110, 180, 0.08)');
      outerGlow.addColorStop(1, 'rgba(130, 100, 170, 0)');
      ctx.fillStyle = outerGlow;
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius * 1.15, 0, Math.PI * 2);
      ctx.fill();
      
      // Glass sphere - subtle lavender tint for visibility
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius, 0, Math.PI * 2);
      
      const glassGrad = ctx.createRadialGradient(
        cx - sphereRadius * 0.25, cy - sphereRadius * 0.25, 0,
        cx, cy, sphereRadius
      );
      glassGrad.addColorStop(0, 'rgba(255, 255, 255, 0.15)');
      glassGrad.addColorStop(0.3, 'rgba(245, 240, 255, 0.12)');
      glassGrad.addColorStop(0.6, 'rgba(230, 220, 250, 0.15)');
      glassGrad.addColorStop(0.85, 'rgba(210, 195, 240, 0.2)');
      glassGrad.addColorStop(1, 'rgba(190, 170, 225, 0.3)');
      ctx.fillStyle = glassGrad;
      ctx.fill();
      
      const rotation = time * rotationSpeed;
      
      // Center glow
      const centerGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, sphereRadius * 0.35);
      centerGlow.addColorStop(0, 'rgba(200, 175, 240, 0.3)');
      centerGlow.addColorStop(0.5, 'rgba(180, 155, 220, 0.15)');
      centerGlow.addColorStop(1, 'rgba(160, 135, 200, 0)');
      
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius * 0.35, 0, Math.PI * 2);
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
          const startRadius = sphereRadius - 8 * scale;
          const endRadius = 12 * scale;
          const currentRadius = startRadius - (startRadius - endRadius) * progress;
          
          const burstX = cx + Math.cos(burst.angle) * currentRadius;
          const burstY = cy + Math.sin(burst.angle) * currentRadius;
          
          const fadeOut = progress > 0.7 ? 1 - ((progress - 0.7) / 0.3) : 1;
          const fadeIn = progress < 0.15 ? progress / 0.15 : 1;
          const opacity = fadeIn * fadeOut;
          
          if (opacity > 0.05) {
            const burstGrad = ctx.createRadialGradient(
              burstX, burstY, 0,
              burstX, burstY, 12 * scale
            );
            burstGrad.addColorStop(0, `rgba(255, 230, 180, ${0.5 * opacity})`);
            burstGrad.addColorStop(0.5, `rgba(255, 210, 140, ${0.25 * opacity})`);
            burstGrad.addColorStop(1, 'rgba(255, 190, 100, 0)');
            
            ctx.beginPath();
            ctx.arc(burstX, burstY, 12 * scale, 0, Math.PI * 2);
            ctx.fillStyle = burstGrad;
            ctx.fill();
          }
        });
        
        ctx.restore();
      }
      
      // Outer petals
      const outerPetalInner = sphereRadius * 0.24;
      const outerPetalOuter = sphereRadius * 0.82;
      const outerPetalWidth = sphereRadius * 0.20;
      
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + rotation + Math.PI / 8;
        drawPetal(ctx, cx, cy, angle, outerPetalInner, outerPetalOuter, outerPetalWidth, true, glowPulse, scale);
      }
      
      // Inner petals
      const innerPetalInner = sphereRadius * 0.14;
      const innerPetalOuter = sphereRadius * 0.56;
      const innerPetalWidth = sphereRadius * 0.15;
      
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + rotation;
        drawPetal(ctx, cx, cy, angle, innerPetalInner, innerPetalOuter, innerPetalWidth, false, glowPulse, scale);
      }
      
      // Center radiating lines
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rotation);
      
      const lineInner = sphereRadius * 0.05;
      const lineOuter = sphereRadius * 0.18;
      
      for (let i = 0; i < 16; i++) {
        const angle = (i / 16) * Math.PI * 2;
        ctx.beginPath();
        ctx.moveTo(Math.cos(angle) * lineInner, Math.sin(angle) * lineInner);
        ctx.lineTo(Math.cos(angle) * lineOuter, Math.sin(angle) * lineOuter);
        ctx.strokeStyle = `rgba(220, 200, 255, ${0.35 * glowPulse})`;
        ctx.lineWidth = Math.max(0.5, 0.8 * scale);
        ctx.stroke();
      }
      
      ctx.restore();
      
      // Luminous center
      const { r, g, b } = glowColor;
      
      // Ethereal smoke layers
      const smokeLayers = 3;
      for (let layer = 0; layer < smokeLayers; layer++) {
        const noiseVal = noise(layer * 50, time * 100, time * 2);
        const offsetX = noiseVal * 4 * scale;
        const offsetY = noise(layer * 30 + 100, time * 80, time * 1.5) * 4 * scale;
        const sizeVariation = 1 + noise(layer * 20, time * 60, time) * 0.08;
        
        const layerSize = centerSize * sizeVariation * (1 + layer * 0.2);
        const layerOpacity = 0.15 / (layer + 1);
        
        const smokeGrad = ctx.createRadialGradient(
          cx + offsetX, cy + offsetY, 0,
          cx + offsetX, cy + offsetY, layerSize
        );
        smokeGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${layerOpacity * 2.5})`);
        smokeGrad.addColorStop(0.6, `rgba(${Math.floor(r * 0.95)}, ${Math.floor(g * 0.95)}, ${Math.floor(b * 0.97)}, ${layerOpacity})`);
        smokeGrad.addColorStop(1, `rgba(${Math.floor(r * 0.9)}, ${Math.floor(g * 0.9)}, ${Math.floor(b * 0.95)}, 0)`);
        
        ctx.beginPath();
        ctx.arc(cx + offsetX, cy + offsetY, layerSize, 0, Math.PI * 2);
        ctx.fillStyle = smokeGrad;
        ctx.fill();
      }
      
      // Outer halo
      const haloWobble = noise(0, 0, time * 2) * 2 * scale;
      const haloSize = centerSize * 1.8 + haloWobble;
      const haloGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, haloSize);
      haloGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.22)`);
      haloGrad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, 0.1)`);
      haloGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, haloSize, 0, Math.PI * 2);
      ctx.fillStyle = haloGrad;
      ctx.fill();
      
      // PURE LIGHT CENTER - no visible shape, just radiant glow
      // Larger, softer core glow
      const coreSize = centerSize * 1.2;
      const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreSize);
      coreGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.85)`);
      coreGrad.addColorStop(0.3, `rgba(${r}, ${g}, ${b}, 0.5)`);
      coreGrad.addColorStop(0.6, `rgba(${r}, ${g}, ${b}, 0.25)`);
      coreGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, coreSize, 0, Math.PI * 2);
      ctx.fillStyle = coreGrad;
      ctx.fill();
      
      // Inner bright bloom - pure light, no hard edges
      const bloomSize = centerSize * 0.5;
      const bloomGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, bloomSize);
      bloomGrad.addColorStop(0, `rgba(255, 255, 255, 0.9)`);
      bloomGrad.addColorStop(0.4, `rgba(${r}, ${g}, ${b}, 0.6)`);
      bloomGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, bloomSize, 0, Math.PI * 2);
      ctx.fillStyle = bloomGrad;
      ctx.fill();
      
      // PURPLE BORDER/STROKE - makes sphere look rounder
      const borderWidth = Math.max(1.5, 2.5 * scale);
      
      // Outer glow for border
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(160, 130, 200, 0.25)';
      ctx.lineWidth = borderWidth + 3 * scale;
      ctx.stroke();
      
      // Main purple border
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius, 0, Math.PI * 2);
      const borderGrad = ctx.createLinearGradient(
        cx - sphereRadius, cy - sphereRadius,
        cx + sphereRadius, cy + sphereRadius
      );
      borderGrad.addColorStop(0, 'rgba(200, 175, 235, 0.7)');
      borderGrad.addColorStop(0.25, 'rgba(175, 150, 215, 0.6)');
      borderGrad.addColorStop(0.5, 'rgba(160, 135, 200, 0.65)');
      borderGrad.addColorStop(0.75, 'rgba(175, 150, 215, 0.6)');
      borderGrad.addColorStop(1, 'rgba(200, 175, 235, 0.7)');
      ctx.strokeStyle = borderGrad;
      ctx.lineWidth = borderWidth;
      ctx.stroke();
      
      // Inner highlight line
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius - borderWidth * 0.5, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(240, 230, 255, 0.25)';
      ctx.lineWidth = Math.max(0.5, 0.8 * scale);
      ctx.stroke();
      
      // Top highlight - crisp glass reflection
      const highlightX = cx - sphereRadius * 0.32;
      const highlightY = cy - sphereRadius * 0.32;
      const highlightW = sphereRadius * 0.18;
      const highlightH = sphereRadius * 0.07;
      
      ctx.beginPath();
      ctx.ellipse(highlightX, highlightY, highlightW, highlightH, -Math.PI / 4, 0, Math.PI * 2);
      const highlight = ctx.createRadialGradient(highlightX, highlightY, 0, highlightX, highlightY, highlightW);
      highlight.addColorStop(0, 'rgba(255, 255, 255, 0.6)');
      highlight.addColorStop(0.5, 'rgba(255, 255, 255, 0.25)');
      highlight.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = highlight;
      ctx.fill();
      
      // Secondary small highlight
      const highlight2X = cx - sphereRadius * 0.12;
      const highlight2Y = cy - sphereRadius * 0.48;
      const highlight2R = sphereRadius * 0.05;
      
      ctx.beginPath();
      ctx.arc(highlight2X, highlight2Y, highlight2R, 0, Math.PI * 2);
      const highlight2 = ctx.createRadialGradient(highlight2X, highlight2Y, 0, highlight2X, highlight2Y, highlight2R);
      highlight2.addColorStop(0, 'rgba(255, 255, 255, 0.7)');
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
        filter: isActive ? 'drop-shadow(0 2px 8px rgba(150, 120, 190, 0.35))' : 'none',
        display: 'block',
      }}
      aria-label="Nicole thinking indicator"
      role="status"
      aria-live="polite"
    />
  );
});

export default LotusSphere;
