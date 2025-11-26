import Image from 'next/image';

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
 * Displays a rotating purple flower avatar and thinking steps.
 */
export function AlphawaveThinkingInterface({ steps }: AlphawaveThinkingInterfaceProps) {
  return (
    <div className="flex items-center space-x-4 p-4">
      {/* Purple flower avatar - rotating */}
      <div className="relative">
        <Image
          src="/images/nicole-thinking-avatar.png"
          alt="Nicole thinking"
          width={40}
          height={40}
          className="animate-spin"
        />
      </div>

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

