'use client';

import React, { useEffect, useRef, memo, useMemo } from 'react';

/**
 * LOTUS SPHERE - Nicole Edition v5 (Perfected)
 * 
 * Ethereal, luminous, glassy lotus flower with soft purple glow.
 * Based on lotus-sphere-v5.jsx with enhanced vibrancy.
 */

export type ThinkingState = 'default' | 'searching' | 'thinking' | 'processing' | 'speaking';

export interface LotusSphereProps {
  state?: ThinkingState;
  size?: number;
  className?: string;
  isActive?: boolean;
  withBackground?: boolean;
}

const noise = (x: number, y: number, t: number): number => {
  return Math.sin(x * 0.05 + t) * Math.cos(y * 0.05 + t * 0.7) * 
         Math.sin((x + y) * 0.03 + t * 0.5);
};

export const LotusSphere = memo(function LotusSphere({
  state = 'default',
  size = 96,
  className = '',
  isActive = true,
  withBackground = false,
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
    
    const scale = size / 500;
    const cx = size / 2;
    const cy = size / 2;
    const sphereRadius = 180 * scale;
    
    // Draw petal with luminous glow
    const drawPetal = (
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
      
      // Rich purple gradient - more vibrant than before
      const fillGrad = ctx.createLinearGradient(innerRadius, 0, outerRadius, 0);
      fillGrad.addColorStop(0, 'rgba(60, 30, 100, 0.95)');
      fillGrad.addColorStop(0.3, 'rgba(90, 50, 140, 0.92)');
      fillGrad.addColorStop(0.6, 'rgba(120, 70, 180, 0.88)');
      fillGrad.addColorStop(1, 'rgba(150, 100, 210, 0.85)');
      ctx.fillStyle = fillGrad;
      ctx.fill();
      
      // Luminous edge glow - brighter, more ethereal
      const glowLayers = [
        { width: 12 * scale, color: `rgba(180, 140, 255, ${0.15 * glowIntensity})` },
        { width: 8 * scale, color: `rgba(200, 170, 255, ${0.25 * glowIntensity})` },
        { width: 4 * scale, color: `rgba(220, 200, 255, ${0.45 * glowIntensity})` },
        { width: 2 * scale, color: `rgba(240, 230, 255, ${0.7 * glowIntensity})` },
        { width: 1 * scale, color: `rgba(255, 250, 255, ${0.9 * glowIntensity})` },
      ];
      
      glowLayers.forEach(g => {
        ctx.strokeStyle = g.color;
        ctx.lineWidth = g.width;
        ctx.stroke();
      });
      
      // Inner highlight vein - adds depth
      ctx.beginPath();
      ctx.moveTo(innerRadius + 15 * scale, 0);
      ctx.lineTo(outerRadius - 20 * scale, 0);
      const veinGrad = ctx.createLinearGradient(innerRadius, 0, outerRadius, 0);
      veinGrad.addColorStop(0, `rgba(220, 200, 255, ${0.1 * glowIntensity})`);
      veinGrad.addColorStop(0.5, `rgba(255, 240, 255, ${0.3 * glowIntensity})`);
      veinGrad.addColorStop(1, `rgba(220, 200, 255, ${0.1 * glowIntensity})`);
      ctx.strokeStyle = veinGrad;
      ctx.lineWidth = 1.5 * scale;
      ctx.stroke();
      
      ctx.restore();
    };
    
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
        rotationSpeed = prefersReducedMotion ? 0 : 0.1;
        glowPulse = 0.85 + (prefersReducedMotion ? 0 : Math.sin(time * 1) * 0.15);
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
        rotationSpeed = 0.08;
        glowPulse = 0.95 + Math.sin(time * 3) * 0.05;
        centerSize = (28 + Math.sin(time * 2) * 5) * scale;
        glowColor = { r: 180, g: 220, b: 255 };
      } else {
        rotationSpeed = 0.1;
        glowPulse = 0.85;
        centerSize = 25 * scale;
      }
      
      // Clear
      ctx.clearRect(0, 0, size, size);
      
      // Background for sidebar only
      if (withBackground) {
        ctx.fillStyle = '#000000';
        ctx.fillRect(0, 0, size, size);
      }
      
      // Outer ambient glow - larger, softer
      const outerAmbient = ctx.createRadialGradient(cx, cy, sphereRadius * 0.5, cx, cy, sphereRadius * 1.8);
      outerAmbient.addColorStop(0, 'rgba(150, 100, 220, 0.15)');
      outerAmbient.addColorStop(0.4, 'rgba(120, 70, 180, 0.1)');
      outerAmbient.addColorStop(0.7, 'rgba(90, 50, 150, 0.05)');
      outerAmbient.addColorStop(1, 'rgba(60, 30, 100, 0)');
      ctx.fillStyle = outerAmbient;
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius * 1.8, 0, Math.PI * 2);
      ctx.fill();
      
      // Glass sphere - more translucent with purple tint
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius, 0, Math.PI * 2);
      
      const glassGrad = ctx.createRadialGradient(
        cx - sphereRadius * 0.3, cy - sphereRadius * 0.3, 0,
        cx, cy, sphereRadius
      );
      glassGrad.addColorStop(0, 'rgba(200, 180, 230, 0.15)');
      glassGrad.addColorStop(0.4, 'rgba(150, 120, 200, 0.12)');
      glassGrad.addColorStop(0.7, 'rgba(120, 90, 180, 0.18)');
      glassGrad.addColorStop(0.9, 'rgba(160, 120, 210, 0.25)');
      glassGrad.addColorStop(1, 'rgba(190, 150, 230, 0.4)');
      ctx.fillStyle = glassGrad;
      ctx.fill();
      
      const rotation = time * rotationSpeed;
      
      // Purple center background - richer
      const purpleCenter = ctx.createRadialGradient(cx, cy, 0, cx, cy, 90 * scale);
      purpleCenter.addColorStop(0, 'rgba(130, 90, 190, 0.5)');
      purpleCenter.addColorStop(0.3, 'rgba(110, 70, 170, 0.4)');
      purpleCenter.addColorStop(0.6, 'rgba(90, 50, 150, 0.2)');
      purpleCenter.addColorStop(1, 'rgba(70, 30, 120, 0)');
      ctx.beginPath();
      ctx.arc(cx, cy, 90 * scale, 0, Math.PI * 2);
      ctx.fillStyle = purpleCenter;
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
          const endRadius = 20 * scale;
          const currentRadius = startRadius - (startRadius - endRadius) * progress;
          
          const burstX = cx + Math.cos(burst.angle) * currentRadius;
          const burstY = cy + Math.sin(burst.angle) * currentRadius;
          
          const fadeOut = progress > 0.7 ? 1 - ((progress - 0.7) / 0.3) : 1;
          const fadeIn = progress < 0.15 ? progress / 0.15 : 1;
          const opacity = fadeIn * fadeOut;
          
          if (opacity > 0.05) {
            const glowGrad = ctx.createRadialGradient(burstX, burstY, 0, burstX, burstY, 20 * scale);
            glowGrad.addColorStop(0, `rgba(255, 230, 150, ${0.4 * opacity})`);
            glowGrad.addColorStop(0.5, `rgba(255, 210, 100, ${0.2 * opacity})`);
            glowGrad.addColorStop(1, 'rgba(255, 200, 80, 0)');
            
            ctx.beginPath();
            ctx.arc(burstX, burstY, 20 * scale, 0, Math.PI * 2);
            ctx.fillStyle = glowGrad;
            ctx.fill();
            
            ctx.save();
            ctx.translate(burstX, burstY);
            ctx.rotate(burst.angle);
            
            const burstLength = burst.length * scale * (0.5 + (1 - progress) * 0.5);
            
            const burstGrad = ctx.createLinearGradient(-burstLength / 2, 0, burstLength / 2, 0);
            burstGrad.addColorStop(0, `rgba(255, 240, 180, ${0.15 * opacity})`);
            burstGrad.addColorStop(0.4, `rgba(255, 248, 210, ${0.6 * opacity})`);
            burstGrad.addColorStop(0.7, `rgba(255, 252, 230, ${0.8 * opacity})`);
            burstGrad.addColorStop(1, `rgba(255, 255, 245, ${0.4 * opacity})`);
            
            ctx.beginPath();
            ctx.ellipse(0, 0, burstLength / 2, 4 * scale, 0, 0, Math.PI * 2);
            ctx.fillStyle = burstGrad;
            ctx.fill();
            
            ctx.beginPath();
            ctx.ellipse(burstLength / 4, 0, burstLength / 6, 2.5 * scale, 0, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 250, ${0.7 * opacity})`;
            ctx.fill();
            
            ctx.restore();
          }
        });
        
        ctx.restore();
      }
      
      // Outer petals (8)
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + rotation + Math.PI / 8;
        drawPetal(angle, 50 * scale, 140 * scale, 45 * scale, true, glowPulse);
      }
      
      // Inner petals (8)
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + rotation;
        drawPetal(angle, 30 * scale, 110 * scale, 35 * scale, false, glowPulse);
      }
      
      // Center radiating lines - more subtle
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(rotation);
      
      for (let i = 0; i < 16; i++) {
        const lineAngle = (i / 16) * Math.PI * 2;
        ctx.beginPath();
        ctx.moveTo(Math.cos(lineAngle) * 15 * scale, Math.sin(lineAngle) * 15 * scale);
        ctx.lineTo(Math.cos(lineAngle) * 45 * scale, Math.sin(lineAngle) * 45 * scale);
        ctx.strokeStyle = `rgba(220, 200, 255, ${0.2 * glowPulse})`;
        ctx.lineWidth = 1 * scale;
        ctx.stroke();
      }
      
      ctx.restore();
      
      // SMOKEY HEAVENLY CENTER GLOW
      const { r, g, b } = glowColor;
      
      // Smoke layers (5 layers)
      for (let layer = 0; layer < 5; layer++) {
        const noiseVal = noise(layer * 50, time * 100, time * 2);
        const offsetX = noiseVal * 8 * scale;
        const offsetY = noise(layer * 30 + 100, time * 80, time * 1.5) * 8 * scale;
        const sizeVar = 1 + noise(layer * 20, time * 60, time) * 0.15;
        
        const layerSize = centerSize * sizeVar * (1 + layer * 0.35);
        const layerOpacity = 0.18 / (layer + 1);
        
        const smokeGrad = ctx.createRadialGradient(
          cx + offsetX, cy + offsetY, 0,
          cx + offsetX, cy + offsetY, layerSize
        );
        smokeGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${layerOpacity * 2.5})`);
        smokeGrad.addColorStop(0.4, `rgba(${Math.floor(r * 0.95)}, ${Math.floor(g * 0.95)}, ${Math.floor(b * 0.97)}, ${layerOpacity * 1.5})`);
        smokeGrad.addColorStop(0.7, `rgba(${Math.floor(r * 0.9)}, ${Math.floor(g * 0.9)}, ${Math.floor(b * 0.95)}, ${layerOpacity * 0.7})`);
        smokeGrad.addColorStop(1, `rgba(${Math.floor(r * 0.85)}, ${Math.floor(g * 0.85)}, ${Math.floor(b * 0.9)}, 0)`);
        
        ctx.beginPath();
        ctx.arc(cx + offsetX, cy + offsetY, layerSize, 0, Math.PI * 2);
        ctx.fillStyle = smokeGrad;
        ctx.fill();
      }
      
      // Outer halo - more prominent
      const haloWobble = noise(0, 0, time * 2) * 6 * scale;
      const haloSize = centerSize * 2.8 + haloWobble;
      const haloGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, haloSize);
      haloGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.25)`);
      haloGrad.addColorStop(0.3, `rgba(${r}, ${g}, ${b}, 0.18)`);
      haloGrad.addColorStop(0.6, `rgba(${Math.floor(r * 0.9)}, ${Math.floor(g * 0.9)}, ${Math.floor(b * 0.95)}, 0.08)`);
      haloGrad.addColorStop(1, `rgba(${Math.floor(r * 0.8)}, ${Math.floor(g * 0.8)}, ${Math.floor(b * 0.9)}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, haloSize, 0, Math.PI * 2);
      ctx.fillStyle = haloGrad;
      ctx.fill();
      
      // Middle glow
      const midOffset = noise(100, 50, time * 1.5) * 4 * scale;
      const midSize = centerSize * 1.8;
      const midGrad = ctx.createRadialGradient(cx + midOffset, cy, 0, cx + midOffset, cy, midSize);
      midGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.6)`);
      midGrad.addColorStop(0.4, `rgba(${r}, ${g}, ${b}, 0.4)`);
      midGrad.addColorStop(0.7, `rgba(${Math.floor(r * 0.95)}, ${Math.floor(g * 0.97)}, ${Math.floor(b * 0.98)}, 0.2)`);
      midGrad.addColorStop(1, `rgba(${Math.floor(r * 0.9)}, ${Math.floor(g * 0.95)}, ${Math.floor(b * 0.97)}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx + midOffset, cy, midSize, 0, Math.PI * 2);
      ctx.fillStyle = midGrad;
      ctx.fill();
      
      // Inner core - bright
      const coreGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, centerSize * 0.9);
      coreGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 1)`);
      coreGrad.addColorStop(0.3, `rgba(${r}, ${g}, ${b}, 0.85)`);
      coreGrad.addColorStop(0.6, `rgba(${Math.floor(r * 0.97)}, ${Math.floor(g * 0.98)}, ${Math.floor(b * 0.99)}, 0.5)`);
      coreGrad.addColorStop(1, `rgba(${Math.floor(r * 0.95)}, ${Math.floor(g * 0.97)}, ${Math.floor(b * 0.98)}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, centerSize * 0.9, 0, Math.PI * 2);
      ctx.fillStyle = coreGrad;
      ctx.fill();
      
      // Bright center point
      const dotGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 6 * scale);
      dotGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, 1)`);
      dotGrad.addColorStop(0.5, `rgba(${r}, ${g}, ${b}, 0.8)`);
      dotGrad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
      
      ctx.beginPath();
      ctx.arc(cx, cy, 6 * scale, 0, Math.PI * 2);
      ctx.fillStyle = dotGrad;
      ctx.fill();
      
      // Glass rim - rainbow purple segments
      const rimSegments = 36;
      for (let i = 0; i < rimSegments; i++) {
        const startAngle = (i / rimSegments) * Math.PI * 2;
        const endAngle = ((i + 1) / rimSegments) * Math.PI * 2;
        
        const hue = (i / rimSegments) * 50 + 260;
        const saturation = 60 + Math.sin(i * 0.5 + time) * 20;
        const lightness = 60 + Math.sin(i * 0.3) * 15;
        
        ctx.beginPath();
        ctx.arc(cx, cy, sphereRadius, startAngle, endAngle);
        ctx.strokeStyle = `hsla(${hue}, ${saturation}%, ${lightness}%, 0.6)`;
        ctx.lineWidth = 3.5 * scale;
        ctx.stroke();
      }
      
      // Inner rim glow
      ctx.beginPath();
      ctx.arc(cx, cy, sphereRadius - 2 * scale, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(200, 180, 255, 0.15)';
      ctx.lineWidth = 4 * scale;
      ctx.stroke();
      
      // Top highlight - glass reflection
      ctx.beginPath();
      ctx.ellipse(
        cx - sphereRadius * 0.4, 
        cy - sphereRadius * 0.4, 
        sphereRadius * 0.28, 
        sphereRadius * 0.14,
        -Math.PI / 4,
        0, Math.PI * 2
      );
      const topHighlight = ctx.createRadialGradient(
        cx - sphereRadius * 0.4, cy - sphereRadius * 0.4, 0,
        cx - sphereRadius * 0.4, cy - sphereRadius * 0.4, sphereRadius * 0.28
      );
      topHighlight.addColorStop(0, 'rgba(255, 255, 255, 0.35)');
      topHighlight.addColorStop(0.5, 'rgba(255, 255, 255, 0.15)');
      topHighlight.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = topHighlight;
      ctx.fill();
      
      // Bottom rim glow - purple accents
      ctx.beginPath();
      ctx.arc(cx, cy + sphereRadius * 0.08, sphereRadius * 0.92, Math.PI * 0.55, Math.PI * 0.95);
      ctx.strokeStyle = 'rgba(160, 120, 230, 0.3)';
      ctx.lineWidth = 14 * scale;
      ctx.stroke();
      
      ctx.beginPath();
      ctx.arc(cx, cy + sphereRadius * 0.08, sphereRadius * 0.92, Math.PI * 0.05, Math.PI * 0.45);
      ctx.strokeStyle = 'rgba(160, 120, 230, 0.3)';
      ctx.lineWidth = 14 * scale;
      ctx.stroke();
      
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
  }, [size, state, isActive, prefersReducedMotion, energyBursts, withBackground]);
  
  return (
    <canvas 
      ref={canvasRef}
      className={className}
      style={{
        filter: isActive ? 'drop-shadow(0 0 25px rgba(140, 100, 200, 0.35))' : 'none',
        display: 'block',
      }}
      aria-label="Nicole thinking indicator"
      role="status"
      aria-live="polite"
    />
  );
});

export default LotusSphere;
