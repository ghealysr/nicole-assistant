'use client';

import React, { useEffect, useRef, memo, useMemo } from 'react';

/**
 * LOTUS SPHERE - Nicole Edition v5
 * 
 * Premium canvas-based thinking animation featuring:
 * - Glowing purple lotus/mandala pattern inside glass sphere
 * - State-based behaviors (default, searching, thinking, processing, speaking)
 * - Smokey/organic glow texture
 * - Energy bursts that flow from perimeter INTO center (processing state)
 * - Reduced motion support
 * - Pixel-perfect rendering at any size
 */

export type ThinkingState = 'default' | 'searching' | 'thinking' | 'processing' | 'speaking';

export interface LotusSphereProps {
  /** Current animation state */
  state?: ThinkingState;
  /** Size in pixels (canvas will be square) */
  size?: number;
  /** Optional additional className */
  className?: string;
  /** Whether animation is active */
  isActive?: boolean;
}

// Noise function for smokey effect
const noise = (x: number, y: number, t: number): number => {
  return Math.sin(x * 0.05 + t) * Math.cos(y * 0.05 + t * 0.7) * 
         Math.sin((x + y) * 0.03 + t * 0.5);
};

// Draw petal helper function with pixel-perfect scaling
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
  
  // Purple gradient fill
  const fillGrad = ctx.createLinearGradient(innerRadius, 0, outerRadius, 0);
  fillGrad.addColorStop(0, 'rgba(45, 20, 80, 0.95)');
  fillGrad.addColorStop(0.4, 'rgba(70, 35, 120, 0.9)');
  fillGrad.addColorStop(0.7, 'rgba(100, 50, 160, 0.85)');
  fillGrad.addColorStop(1, 'rgba(130, 70, 190, 0.8)');
  ctx.fillStyle = fillGrad;
  ctx.fill();
  
  // Purple edge glow - scale line widths
  const glowColors = [
    { width: Math.max(1, 10 * scale), color: `rgba(150, 100, 255, ${0.12 * glowIntensity})` },
    { width: Math.max(1, 6 * scale), color: `rgba(180, 130, 255, ${0.25 * glowIntensity})` },
    { width: Math.max(0.5, 3 * scale), color: `rgba(200, 160, 255, ${0.5 * glowIntensity})` },
    { width: Math.max(0.5, 1.5 * scale), color: `rgba(230, 200, 255, ${0.8 * glowIntensity})` },
  ];
  
  glowColors.forEach(g => {
    ctx.strokeStyle = g.color;
    ctx.lineWidth = g.width;
    ctx.stroke();
  });
  
  // Inner vein
  ctx.beginPath();
  ctx.moveTo(innerRadius + 10 * scale, 0);
  ctx.lineTo(outerRadius - 15 * scale, 0);
  ctx.strokeStyle = `rgba(180, 140, 220, ${0.25 * glowIntensity})`;
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
  
  // Check for reduced motion preference
  const prefersReducedMotion = typeof window !== 'undefined' 
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches 
    : false;
  
  // Energy bursts for processing state - distributed around the perimeter, flow INWARD
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
    
    // Scale for retina displays
    const dpr = window.devicePixelRatio || 1;
    const canvasSize = Math.floor(size * dpr);
    canvas.width = canvasSize;
    canvas.height = canvasSize;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;
    ctx.scale(dpr, dpr);
    
    // Pixel-perfect center (use exact half for even sizes)
    const cx = size / 2;
    const cy = size / 2;
    
    // Use 40% of size for sphere radius (better fit)
    const sphereRadius = size * 0.40;
    
    // Scale factor from original 500px design
    const scale = size / 500;
    
    const animate = () => {
      if (!isActive && !prefersReducedMotion) {
        timeRef.current = 0;
      } else {
        timeRef.current += 0.016;
      }
      
      const time = timeRef.current;
      
      // Mode parameters
      let rotationSpeed: number, glowPulse: number, centerSize: number;
      let glowColor = { r: 255, g: 255, b: 255 };
      
      if (state === 'default' || prefersReducedMotion) {
        rotationSpeed = prefersReducedMotion ? 0 : 0.1;
        glowPulse = 0.85 + (prefersReducedMotion ? 0 : Math.sin(time) * 0.15);
        centerSize = (25 + (prefersReducedMotion ? 0 : Math.sin(time * 1.2) * 8)) * scale;
      } else if (state === 'searching') {
        rotationSpeed = 0.1;
        glowPulse = 0.9;
        centerSize = (20 + Math.sin(time * 2.5) * 18) * scale;
      } else if (state === 'thinking') {
        rotationSpeed = 1.0;
        glowPulse = 0.9 + Math.sin(time * 2) * 0.1;
        centerSize = (22 + Math.sin(time * 3) * 10) * scale;
        glowColor = { r: 200, g: 255, b: 200 };
      } else if (state === 'processing') {
        rotationSpeed = 0.15;
        glowPulse = 0.7 + Math.sin(time * 4) * 0.3;
        centerSize = (25 + Math.sin(time * 4) * 12) * scale;
      } else if (state === 'speaking') {
        rotationSpeed = 0.05;
        glowPulse = 0.95 + Math.sin(time * 3) * 0.05;
        centerSize = (28 + Math.sin(time * 2) * 5) * scale;
        glowColor = { r: 180, g: 220, b: 255 };
      } else {
        rotationSpeed = 0.1;
        glowPulse = 0.85;
        centerSize = 25 * scale;
      }
      
      // Clear canvas (transparent background)
      ctx.clearRect(0, 0, size, size);
      
      // Ambient glow - centered
      const ambientGlow = ctx.createRadialGradient(cx, cy, sphereRadius * 0.6, cx, cy, sphereRadius * 1.3);
      ambientGlow.addColorStop(0, 'rgba(130, 80, 200, 0.15)');
      ambientGlow.addColorStop(0.5, 'rgba(80, 40, 150, 0.08)');
      ambientGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = ambientGlow;
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius * 1.3, 0, Math.PI * 2);
      ctx.fill();
      
      // Glass sphere back - perfectly centered
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius, 0, Math.PI * 2);
      
      const rimGrad = ctx.createRadialGradient(
        cx - sphereRadius * 0.3, cy - sphereRadius * 0.3, sphereRadius * 0.4,
        cx, cy, sphereRadius
      );
      rimGrad.addColorStop(0, 'rgba(40, 20, 60, 0.35)');
      rimGrad.addColorStop(0.6, 'rgba(60, 30, 90, 0.45)');
      rimGrad.addColorStop(0.85, 'rgba(140, 80, 180, 0.35)');
      rimGrad.addColorStop(1, 'rgba(180, 130, 220, 0.55)');
      ctx.fillStyle = rimGrad;
      ctx.fill();
      
      // Rotation
      const rotation = time * rotationSpeed;
      
      // Purple center background - centered
      const purpleBackGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, sphereRadius * 0.5);
      purpleBackGlow.addColorStop(0, 'rgba(100, 60, 160, 0.5)');
      purpleBackGlow.addColorStop(0.4, 'rgba(80, 45, 140, 0.35)');
      purpleBackGlow.addColorStop(0.7, 'rgba(60, 30, 100, 0.15)');
      purpleBackGlow.addColorStop(1, 'rgba(40, 20, 70, 0)');
      
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius * 0.5, 0, Math.PI * 2);
      ctx.fillStyle = purpleBackGlow;
      ctx.fill();
      
      // PROCESSING: Energy bursts from perimeter INTO center
      if (state === 'processing' && !prefersReducedMotion) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(cx, cy, sphereRadius - 2 * scale, 0, Math.PI * 2);
        ctx.clip();
        
        energyBursts.forEach((burst) => {
          const progress = ((time * burst.speed + burst.offset) % 1.5) / 1.5;
          const startRadius = sphereRadius - 10 * scale;
          const endRadius = 20 * scale;
          const currentRadius = startRadius - (startRadius - endRadius) * progress;
          
          const burstX = cx + Math.cos(burst.angle) * currentRadius;
          const burstY = cy + Math.sin(burst.angle) * currentRadius;
          
          const fadeOut = progress > 0.7 ? 1 - ((progress - 0.7) / 0.3) : 1;
          const fadeIn = progress < 0.15 ? progress / 0.15 : 1;
          const opacity = fadeIn * fadeOut;
          
          if (opacity > 0.05) {
            const outerGlowGrad = ctx.createRadialGradient(
              burstX, burstY, 0,
              burstX, burstY, 20 * scale
            );
            outerGlowGrad.addColorStop(0, `rgba(255, 230, 150, ${0.35 * opacity})`);
            outerGlowGrad.addColorStop(0.5, `rgba(255, 210, 100, ${0.15 * opacity})`);
            outerGlowGrad.addColorStop(1, 'rgba(255, 200, 80, 0)');
            
            ctx.beginPath();
            ctx.arc(burstX, burstY, 20 * scale, 0, Math.PI * 2);
            ctx.fillStyle = outerGlowGrad;
            ctx.fill();
            
            ctx.save();
            ctx.translate(burstX, burstY);
            ctx.rotate(burst.angle);
            
            const burstLength = burst.length * scale * (0.5 + (1 - progress) * 0.5);
            
            const burstGrad = ctx.createLinearGradient(-burstLength / 2, 0, burstLength / 2, 0);
            burstGrad.addColorStop(0, `rgba(255, 240, 180, ${0.1 * opacity})`);
            burstGrad.addColorStop(0.3, `rgba(255, 245, 200, ${0.5 * opacity})`);
            burstGrad.addColorStop(0.6, `rgba(255, 250, 220, ${0.7 * opacity})`);
            burstGrad.addColorStop(1, `rgba(255, 255, 240, ${0.3 * opacity})`);
            
            ctx.beginPath();
            ctx.ellipse(0, 0, burstLength / 2, Math.max(2, 4 * scale), 0, 0, Math.PI * 2);
            ctx.fillStyle = burstGrad;
            ctx.fill();
            
            ctx.beginPath();
            ctx.ellipse(burstLength / 4, 0, burstLength / 6, Math.max(1.5, 2.5 * scale), 0, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 240, ${0.6 * opacity})`;
            ctx.fill();
            
            ctx.restore();
          }
        });
        
        ctx.restore();
      }
      
      // Outer petals - use relative sizing based on sphere radius
      const outerPetalInner = sphereRadius * 0.28;
      const outerPetalOuter = sphereRadius * 0.78;
      const outerPetalWidth = sphereRadius * 0.25;
      
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + rotation + Math.PI / 8;
        drawPetal(ctx, cx, cy, angle, outerPetalInner, outerPetalOuter, outerPetalWidth, true, glowPulse, scale);
      }
      
      // Inner petals
      const innerPetalInner = sphereRadius * 0.17;
      const innerPetalOuter = sphereRadius * 0.61;
      const innerPetalWidth = sphereRadius * 0.19;
      
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + rotation;
        drawPetal(ctx, cx, cy, angle, innerPetalInner, innerPetalOuter, innerPetalWidth, false, glowPulse, scale);
      }
      
      // Center radiating lines
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rotation);
      
      const lineInner = sphereRadius * 0.07;
      const lineOuter = sphereRadius * 0.22;
      
      for (let i = 0; i < 16; i++) {
        const angle = (i / 16) * Math.PI * 2;
        ctx.beginPath();
        ctx.moveTo(Math.cos(angle) * lineInner, Math.sin(angle) * lineInner);
        ctx.lineTo(Math.cos(angle) * lineOuter, Math.sin(angle) * lineOuter);
        ctx.strokeStyle = `rgba(200, 180, 255, ${0.25 * glowPulse})`;
        ctx.lineWidth = Math.max(0.5, 1 * scale);
        ctx.stroke();
      }
      
      ctx.restore();
      
      // SMOKEY HEAVENLY GLOW CENTER
      const { r, g, b } = glowColor;
      
      // Smoke layers - all centered on cx, cy
      const smokeLayers = 5;
      for (let layer = 0; layer < smokeLayers; layer++) {
        const noiseVal = noise(layer * 50, time * 100, time * 2);
        const offsetX = noiseVal * 8 * scale;
        const offsetY = noise(layer * 30 + 100, time * 80, time * 1.5) * 8 * scale;
        const sizeVariation = 1 + noise(layer * 20, time * 60, time) * 0.15;
        
        const layerSize = centerSize * sizeVariation * (1 + layer * 0.3);
        const layerOpacity = 0.15 / (layer + 1);
        
        const smokeGrad = ctx.createRadialGradient(
          cx + offsetX, cy + offsetY, 0,
          cx + offsetX, cy + offsetY, layerSize
        );
        smokeGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${layerOpacity * 2})`);
        smokeGrad.addColorStop(0.5, `rgba(${Math.floor(r * 0.9)}, ${Math.floor(g * 0.9)}, ${Math.floor(b * 0.95)}, ${layerOpacity})`);
        smokeGrad.addColorStop(1, `rgba(${Math.floor(r * 0.8)}, ${Math.floor(g * 0.8)}, ${Math.floor(b * 0.9)}, 0)`);
        
        ctx.beginPath();
        ctx.arc(cx + offsetX, cy + offsetY, layerSize, 0, Math.PI * 2);
        ctx.fillStyle = smokeGrad;
        ctx.fill();
      }
      
      // Outer halo - centered
      const haloWobble = noise(0, 0, time * 2) * 5 * scale;
      const haloSize = centerSize * 2.5 + haloWobble;
      const haloGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, haloSize);
      haloGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.2)`);
      haloGrad.addColorStop(0.4, `rgba(${Math.floor(r * 0.95)}, ${Math.floor(g * 0.95)}, ${Math.floor(b * 0.98)}, 0.12)`);
      haloGrad.addColorStop(0.7, `rgba(${Math.floor(r * 0.85)}, ${Math.floor(g * 0.85)}, ${Math.floor(b * 0.9)}, 0.06)`);
      haloGrad.addColorStop(1, `rgba(${Math.floor(r * 0.7)}, ${Math.floor(g * 0.7)}, ${Math.floor(b * 0.8)}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, haloSize, 0, Math.PI * 2);
      ctx.fillStyle = haloGrad;
      ctx.fill();
      
      // Middle glow - centered
      const midOffset = noise(100, 50, time * 1.5) * 3 * scale;
      const midSize = centerSize * 1.6;
      const midGrad = ctx.createRadialGradient(cx + midOffset, cy, 0, cx + midOffset, cy, midSize);
      midGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.5)`);
      midGrad.addColorStop(0.5, `rgba(${Math.floor(r * 0.95)}, ${Math.floor(g * 0.98)}, ${Math.floor(b * 0.98)}, 0.3)`);
      midGrad.addColorStop(1, `rgba(${Math.floor(r * 0.9)}, ${Math.floor(g * 0.92)}, ${Math.floor(b * 0.95)}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx + midOffset, cy, midSize, 0, Math.PI * 2);
      ctx.fillStyle = midGrad;
      ctx.fill();
      
      // Inner core - centered
      const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, centerSize * 0.8);
      coreGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.95)`);
      coreGrad.addColorStop(0.4, `rgba(${r}, ${g}, ${b}, 0.7)`);
      coreGrad.addColorStop(0.7, `rgba(${Math.floor(r * 0.95)}, ${Math.floor(g * 0.97)}, ${Math.floor(b * 0.98)}, 0.4)`);
      coreGrad.addColorStop(1, `rgba(${Math.floor(r * 0.9)}, ${Math.floor(g * 0.93)}, ${Math.floor(b * 0.95)}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, centerSize * 0.8, 0, Math.PI * 2);
      ctx.fillStyle = coreGrad;
      ctx.fill();
      
      // Center point - exactly centered
      const dotSize = Math.max(2, 5 * scale);
      const dotGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, dotSize);
      dotGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 1)`);
      dotGrad.addColorStop(0.6, `rgba(${r}, ${g}, ${b}, 0.7)`);
      dotGrad.addColorStop(1, `rgba(${Math.floor(r * 0.95)}, ${Math.floor(g * 0.97)}, ${Math.floor(b * 0.98)}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, dotSize, 0, Math.PI * 2);
      ctx.fillStyle = dotGrad;
      ctx.fill();
      
      // Glass rim - perfectly centered ring
      const rimWidth = Math.max(1.5, 3 * scale);
      const rimSegments = 36;
      for (let i = 0; i < rimSegments; i++) {
        const startAngle = (i / rimSegments) * Math.PI * 2;
        const endAngle = ((i + 1) / rimSegments) * Math.PI * 2;
        
        const hue = (i / rimSegments) * 40 + 270;
        const saturation = 65 + Math.sin(i * 0.5 + time) * 15;
        const lightness = 55 + Math.sin(i * 0.3) * 12;
        
        ctx.beginPath();
        ctx.arc(cx, cy, sphereRadius, startAngle, endAngle);
        ctx.strokeStyle = `hsla(${hue}, ${saturation}%, ${lightness}%, 0.55)`;
        ctx.lineWidth = rimWidth;
        ctx.stroke();
      }
      
      // Top highlight - positioned relative to center
      const highlightX = cx - sphereRadius * 0.4;
      const highlightY = cy - sphereRadius * 0.4;
      const highlightW = sphereRadius * 0.22;
      const highlightH = sphereRadius * 0.1;
      
      ctx.beginPath();
      ctx.ellipse(highlightX, highlightY, highlightW, highlightH, -Math.PI / 4, 0, Math.PI * 2);
      const highlight = ctx.createRadialGradient(highlightX, highlightY, 0, highlightX, highlightY, highlightW);
      highlight.addColorStop(0, 'rgba(255, 255, 255, 0.35)');
      highlight.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = highlight;
      ctx.fill();
      
      // Bottom rim glows - symmetrically positioned
      const bottomGlowWidth = Math.max(4, 12 * scale);
      
      ctx.beginPath();
      ctx.arc(cx, cy + sphereRadius * 0.08, sphereRadius * 0.92, Math.PI * 0.6, Math.PI * 0.9);
      ctx.strokeStyle = 'rgba(150, 100, 220, 0.25)';
      ctx.lineWidth = bottomGlowWidth;
      ctx.stroke();
      
      ctx.beginPath();
      ctx.arc(cx, cy + sphereRadius * 0.08, sphereRadius * 0.92, Math.PI * 0.1, Math.PI * 0.4);
      ctx.strokeStyle = 'rgba(150, 100, 220, 0.25)';
      ctx.lineWidth = bottomGlowWidth;
      ctx.stroke();
      
      // Continue animation if active
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
        filter: isActive ? 'drop-shadow(0 0 10px rgba(120, 60, 180, 0.4))' : 'none',
        display: 'block', // Prevent inline spacing issues
      }}
      aria-label="Nicole is thinking"
      role="status"
      aria-live="polite"
    />
  );
});

export default LotusSphere;
