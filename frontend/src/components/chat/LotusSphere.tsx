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

// Draw petal helper function
const drawPetal = (
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  angle: number,
  innerRadius: number,
  outerRadius: number,
  width: number,
  isOuter: boolean,
  glowIntensity: number
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
      outerRadius - 20, -baseWidth * 0.4,
      tipX, tipY
    );
    ctx.bezierCurveTo(
      outerRadius - 20, baseWidth * 0.4,
      innerRadius + (outerRadius - innerRadius) * 0.3, baseWidth * 0.8,
      innerRadius, 0
    );
  } else {
    ctx.moveTo(innerRadius, 0);
    ctx.bezierCurveTo(
      innerRadius + (outerRadius - innerRadius) * 0.4, -baseWidth * 0.6,
      outerRadius - 10, -baseWidth * 0.15,
      tipX, tipY
    );
    ctx.bezierCurveTo(
      outerRadius - 10, baseWidth * 0.15,
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
  
  // Purple edge glow
  const glowColors = [
    { width: 10, color: `rgba(150, 100, 255, ${0.12 * glowIntensity})` },
    { width: 6, color: `rgba(180, 130, 255, ${0.25 * glowIntensity})` },
    { width: 3, color: `rgba(200, 160, 255, ${0.5 * glowIntensity})` },
    { width: 1.5, color: `rgba(230, 200, 255, ${0.8 * glowIntensity})` },
  ];
  
  glowColors.forEach(g => {
    ctx.strokeStyle = g.color;
    ctx.lineWidth = g.width;
    ctx.stroke();
  });
  
  // Inner vein
  ctx.beginPath();
  ctx.moveTo(innerRadius + 10, 0);
  ctx.lineTo(outerRadius - 15, 0);
  ctx.strokeStyle = `rgba(180, 140, 220, ${0.25 * glowIntensity})`;
  ctx.lineWidth = 1;
  ctx.stroke();
  
  ctx.restore();
};

export const LotusSphere = memo(function LotusSphere({
  state = 'default',
  size = 96, // Default size doubled from 48 to 96
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
      angle: (i / 8) * Math.PI * 2 + Math.random() * 0.3, // Distributed around circle
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
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;
    ctx.scale(dpr, dpr);
    
    const cx = size / 2;
    const cy = size / 2;
    const sphereRadius = size * 0.36; // Scale from 500px original
    const scaleFactor = size / 500;
    
    const animate = () => {
      if (!isActive && !prefersReducedMotion) {
        // Still render one frame when inactive
        timeRef.current = 0;
      } else {
        timeRef.current += 0.016;
      }
      
      const time = timeRef.current;
      
      // Mode parameters
      let rotationSpeed: number, glowPulse: number, centerSize: number;
      let glowColor = { r: 255, g: 255, b: 255 }; // Default white
      
      if (state === 'default' || prefersReducedMotion) {
        rotationSpeed = prefersReducedMotion ? 0 : 0.1;
        glowPulse = 0.85 + (prefersReducedMotion ? 0 : Math.sin(time) * 0.15);
        centerSize = (25 + (prefersReducedMotion ? 0 : Math.sin(time * 1.2) * 8)) * scaleFactor;
      } else if (state === 'searching') {
        rotationSpeed = 0.1;
        glowPulse = 0.9;
        centerSize = (20 + Math.sin(time * 2.5) * 18) * scaleFactor;
      } else if (state === 'thinking') {
        rotationSpeed = 1.0; // Fast spin for thinking
        glowPulse = 0.9 + Math.sin(time * 2) * 0.1;
        centerSize = (22 + Math.sin(time * 3) * 10) * scaleFactor;
        // Light green glow for thinking
        glowColor = { r: 200, g: 255, b: 200 };
      } else if (state === 'processing') {
        rotationSpeed = 0.15;
        glowPulse = 0.7 + Math.sin(time * 4) * 0.3;
        centerSize = (25 + Math.sin(time * 4) * 12) * scaleFactor;
      } else if (state === 'speaking') {
        rotationSpeed = 0.05;
        glowPulse = 0.95 + Math.sin(time * 3) * 0.05;
        centerSize = (28 + Math.sin(time * 2) * 5) * scaleFactor;
        // Soft blue for speaking
        glowColor = { r: 180, g: 220, b: 255 };
      } else {
        rotationSpeed = 0.1;
        glowPulse = 0.85;
        centerSize = 25 * scaleFactor;
      }
      
      // Clear with black background
      ctx.fillStyle = '#000000';
      ctx.fillRect(0, 0, size, size);
      
      // Ambient glow
      const ambientGlow = ctx.createRadialGradient(cx, cy, sphereRadius * 0.8, cx, cy, sphereRadius * 1.5);
      ambientGlow.addColorStop(0, 'rgba(130, 80, 200, 0.12)');
      ambientGlow.addColorStop(0.5, 'rgba(80, 40, 150, 0.06)');
      ambientGlow.addColorStop(1, 'rgba(0, 0, 0, 0)');
      ctx.fillStyle = ambientGlow;
      ctx.fillRect(0, 0, size, size);
      
      // Glass sphere back
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius, 0, Math.PI * 2);
      
      const rimGrad = ctx.createRadialGradient(
        cx - sphereRadius * 0.3, cy - sphereRadius * 0.3, sphereRadius * 0.5,
        cx, cy, sphereRadius
      );
      rimGrad.addColorStop(0, 'rgba(30, 15, 50, 0.3)');
      rimGrad.addColorStop(0.7, 'rgba(50, 25, 80, 0.4)');
      rimGrad.addColorStop(0.9, 'rgba(150, 80, 180, 0.3)');
      rimGrad.addColorStop(1, 'rgba(180, 130, 210, 0.5)');
      ctx.fillStyle = rimGrad;
      ctx.fill();
      
      // Rotation
      const rotation = time * rotationSpeed;
      
      // Purple center background
      const purpleBackGlow = ctx.createRadialGradient(cx, cy, 0, cx, cy, 80 * scaleFactor);
      purpleBackGlow.addColorStop(0, 'rgba(100, 60, 160, 0.5)');
      purpleBackGlow.addColorStop(0.4, 'rgba(80, 45, 140, 0.35)');
      purpleBackGlow.addColorStop(0.7, 'rgba(60, 30, 100, 0.15)');
      purpleBackGlow.addColorStop(1, 'rgba(40, 20, 70, 0)');
      
      ctx.beginPath();
      ctx.arc(cx, cy, 80 * scaleFactor, 0, Math.PI * 2);
      ctx.fillStyle = purpleBackGlow;
      ctx.fill();
      
      // PROCESSING: Energy bursts from perimeter INTO center (v5 update)
      if (state === 'processing' && !prefersReducedMotion) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(cx, cy, sphereRadius - 2, 0, Math.PI * 2);
        ctx.clip();
        
        energyBursts.forEach((burst) => {
          // Progress from 0 (at perimeter) to 1 (at center)
          const progress = ((time * burst.speed + burst.offset) % 1.5) / 1.5;
          
          // Start at perimeter, end at center
          const startRadius = sphereRadius - 10 * scaleFactor;
          const endRadius = 20 * scaleFactor; // Near center light
          const currentRadius = startRadius - (startRadius - endRadius) * progress;
          
          // Position along the angle
          const burstX = cx + Math.cos(burst.angle) * currentRadius;
          const burstY = cy + Math.sin(burst.angle) * currentRadius;
          
          // Fade out as approaching center (disappear into light)
          const fadeOut = progress > 0.7 ? 1 - ((progress - 0.7) / 0.3) : 1;
          // Also fade in at start
          const fadeIn = progress < 0.15 ? progress / 0.15 : 1;
          const opacity = fadeIn * fadeOut;
          
          if (opacity > 0.05) {
            // Outer glow
            const outerGlowGrad = ctx.createRadialGradient(
              burstX, burstY, 0,
              burstX, burstY, 20 * scaleFactor
            );
            outerGlowGrad.addColorStop(0, `rgba(255, 230, 150, ${0.35 * opacity})`);
            outerGlowGrad.addColorStop(0.5, `rgba(255, 210, 100, ${0.15 * opacity})`);
            outerGlowGrad.addColorStop(1, 'rgba(255, 200, 80, 0)');
            
            ctx.beginPath();
            ctx.arc(burstX, burstY, 20 * scaleFactor, 0, Math.PI * 2);
            ctx.fillStyle = outerGlowGrad;
            ctx.fill();
            
            // Main burst - elongated toward center
            ctx.save();
            ctx.translate(burstX, burstY);
            ctx.rotate(burst.angle); // Align with direction to center
            
            // Burst gets shorter as it approaches center
            const burstLength = burst.length * scaleFactor * (0.5 + (1 - progress) * 0.5);
            
            const burstGrad = ctx.createLinearGradient(-burstLength / 2, 0, burstLength / 2, 0);
            burstGrad.addColorStop(0, `rgba(255, 240, 180, ${0.1 * opacity})`);
            burstGrad.addColorStop(0.3, `rgba(255, 245, 200, ${0.5 * opacity})`);
            burstGrad.addColorStop(0.6, `rgba(255, 250, 220, ${0.7 * opacity})`);
            burstGrad.addColorStop(1, `rgba(255, 255, 240, ${0.3 * opacity})`);
            
            ctx.beginPath();
            ctx.ellipse(0, 0, burstLength / 2, 4 * scaleFactor, 0, 0, Math.PI * 2);
            ctx.fillStyle = burstGrad;
            ctx.fill();
            
            // Bright leading edge (toward center)
            ctx.beginPath();
            ctx.ellipse(burstLength / 4, 0, burstLength / 6, 2.5 * scaleFactor, 0, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 240, ${0.6 * opacity})`;
            ctx.fill();
            
            ctx.restore();
          }
        });
        
        ctx.restore();
      }
      
      // Outer petals
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + rotation + Math.PI / 8;
        drawPetal(ctx, cx, cy, angle, 50 * scaleFactor, 140 * scaleFactor, 45 * scaleFactor, true, glowPulse);
      }
      
      // Inner petals
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + rotation;
        drawPetal(ctx, cx, cy, angle, 30 * scaleFactor, 110 * scaleFactor, 35 * scaleFactor, false, glowPulse);
      }
      
      // Center radiating lines
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rotation);
      
      for (let i = 0; i < 16; i++) {
        const angle = (i / 16) * Math.PI * 2;
        ctx.beginPath();
        ctx.moveTo(Math.cos(angle) * 12 * scaleFactor, Math.sin(angle) * 12 * scaleFactor);
        ctx.lineTo(Math.cos(angle) * 40 * scaleFactor, Math.sin(angle) * 40 * scaleFactor);
        ctx.strokeStyle = `rgba(200, 180, 255, ${0.25 * glowPulse})`;
        ctx.lineWidth = 1;
        ctx.stroke();
      }
      
      ctx.restore();
      
      // SMOKEY HEAVENLY GLOW CENTER
      const { r, g, b } = glowColor;
      
      // Smoke layers
      const smokeLayers = 5;
      for (let layer = 0; layer < smokeLayers; layer++) {
        const noiseVal = noise(layer * 50, time * 100, time * 2);
        const offsetX = noiseVal * 8 * scaleFactor;
        const offsetY = noise(layer * 30 + 100, time * 80, time * 1.5) * 8 * scaleFactor;
        const sizeVariation = 1 + noise(layer * 20, time * 60, time) * 0.15;
        
        const layerSize = centerSize * sizeVariation * (1 + layer * 0.3);
        const layerOpacity = 0.15 / (layer + 1);
        
        const smokeGrad = ctx.createRadialGradient(
          cx + offsetX, cy + offsetY, 0,
          cx + offsetX, cy + offsetY, layerSize
        );
        smokeGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${layerOpacity * 2})`);
        smokeGrad.addColorStop(0.5, `rgba(${r * 0.9}, ${g * 0.9}, ${b * 0.95}, ${layerOpacity})`);
        smokeGrad.addColorStop(1, `rgba(${r * 0.8}, ${g * 0.8}, ${b * 0.9}, 0)`);
        
        ctx.beginPath();
        ctx.arc(cx + offsetX, cy + offsetY, layerSize, 0, Math.PI * 2);
        ctx.fillStyle = smokeGrad;
        ctx.fill();
      }
      
      // Outer halo
      const haloWobble = noise(0, 0, time * 2) * 5 * scaleFactor;
      const haloSize = centerSize * 2.5 + haloWobble;
      const haloGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, haloSize);
      haloGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.2)`);
      haloGrad.addColorStop(0.4, `rgba(${r * 0.95}, ${g * 0.95}, ${b * 0.98}, 0.12)`);
      haloGrad.addColorStop(0.7, `rgba(${r * 0.85}, ${g * 0.85}, ${b * 0.9}, 0.06)`);
      haloGrad.addColorStop(1, `rgba(${r * 0.7}, ${g * 0.7}, ${b * 0.8}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, haloSize, 0, Math.PI * 2);
      ctx.fillStyle = haloGrad;
      ctx.fill();
      
      // Middle glow
      const midOffset = noise(100, 50, time * 1.5) * 3 * scaleFactor;
      const midSize = centerSize * 1.6;
      const midGrad = ctx.createRadialGradient(cx + midOffset, cy, 0, cx + midOffset, cy, midSize);
      midGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.5)`);
      midGrad.addColorStop(0.5, `rgba(${r * 0.95}, ${g * 0.98}, ${b * 0.98}, 0.3)`);
      midGrad.addColorStop(1, `rgba(${r * 0.9}, ${g * 0.92}, ${b * 0.95}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx + midOffset, cy, midSize, 0, Math.PI * 2);
      ctx.fillStyle = midGrad;
      ctx.fill();
      
      // Inner core
      const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, centerSize * 0.8);
      coreGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.95)`);
      coreGrad.addColorStop(0.4, `rgba(${r}, ${g}, ${b}, 0.7)`);
      coreGrad.addColorStop(0.7, `rgba(${r * 0.95}, ${g * 0.97}, ${b * 0.98}, 0.4)`);
      coreGrad.addColorStop(1, `rgba(${r * 0.9}, ${g * 0.93}, ${b * 0.95}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, centerSize * 0.8, 0, Math.PI * 2);
      ctx.fillStyle = coreGrad;
      ctx.fill();
      
      // Center point
      const dotGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 5 * scaleFactor);
      dotGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 1)`);
      dotGrad.addColorStop(0.6, `rgba(${r}, ${g}, ${b}, 0.7)`);
      dotGrad.addColorStop(1, `rgba(${r * 0.95}, ${g * 0.97}, ${b * 0.98}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, 5 * scaleFactor, 0, Math.PI * 2);
      ctx.fillStyle = dotGrad;
      ctx.fill();
      
      // Glass rim
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
        ctx.lineWidth = Math.max(1, 3 * scaleFactor);
        ctx.stroke();
      }
      
      // Top highlight
      ctx.beginPath();
      ctx.ellipse(
        cx - sphereRadius * 0.45, 
        cy - sphereRadius * 0.45, 
        sphereRadius * 0.25, 
        sphereRadius * 0.12,
        -Math.PI / 4,
        0, Math.PI * 2
      );
      const highlight = ctx.createRadialGradient(
        cx - sphereRadius * 0.45, cy - sphereRadius * 0.45, 0,
        cx - sphereRadius * 0.45, cy - sphereRadius * 0.45, sphereRadius * 0.25
      );
      highlight.addColorStop(0, 'rgba(255, 255, 255, 0.3)');
      highlight.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = highlight;
      ctx.fill();
      
      // Bottom rim glow
      ctx.beginPath();
      ctx.arc(cx, cy + sphereRadius * 0.1, sphereRadius * 0.95, Math.PI * 0.6, Math.PI * 0.9);
      ctx.strokeStyle = 'rgba(150, 100, 220, 0.25)';
      ctx.lineWidth = 12 * scaleFactor;
      ctx.stroke();
      
      ctx.beginPath();
      ctx.arc(cx, cy + sphereRadius * 0.1, sphereRadius * 0.95, Math.PI * 0.1, Math.PI * 0.4);
      ctx.strokeStyle = 'rgba(150, 100, 220, 0.25)';
      ctx.lineWidth = 12 * scaleFactor;
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
      }}
      aria-label="Nicole is thinking"
      role="status"
      aria-live="polite"
    />
  );
});

export default LotusSphere;
