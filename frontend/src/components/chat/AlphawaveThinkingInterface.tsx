'use client';

import { NicoleOrbAnimation } from './NicoleOrbAnimation';

/**
 * Interface for thinking step objects.
 */
interface ThinkingStep {
  label: string;
  completed: boolean;
  active: boolean;
}

/**
 * Props for AlphawaveThinkingInterface.
 */
interface AlphawaveThinkingInterfaceProps {
  steps: ThinkingStep[];
}

/**
 * Thinking interface component for Nicole V7.
 * Displays stunning glowing orb animation with thinking steps.
 */
export function AlphawaveThinkingInterface({ steps }: AlphawaveThinkingInterfaceProps) {
  const hasActiveStep = steps.some(s => s.active);
  
  return (
    <div className="flex items-center space-x-4 p-4">
      {/* Nicole's orb animation */}
      <NicoleOrbAnimation 
        isActive={hasActiveStep}
        size="medium"
        variant="single"
        showParticles={true}
      />

      {/* Steps */}
      <div className="flex space-x-2">
        {steps.map((step, i) => (
          <div key={i} className="flex items-center space-x-1">
            {step.completed && <span className="text-lavender">✓</span>}
            {step.active && (
              <div className="w-2 h-2 bg-lavender rounded-full animate-pulse" />
            )}
            <span className="text-sm text-text-secondary">{step.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
