'use client';

/**
 * Props for AlphawaveDashPanel.
 */
interface AlphawaveDashPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Dashboard panel component for Nicole V7.
 * Slides in from the right at 40% width.
 */
export function AlphawaveDashPanel({ isOpen, onClose }: AlphawaveDashPanelProps) {
  if (!isOpen) return null;

  return (
    <div className="w-2/5 bg-white border-l border-border-line flex flex-col">
      <div className="p-4 border-b border-border-line flex justify-between items-center">
        <h2 className="text-lg font-serif text-lavender-text">Dashboard</h2>
        <button onClick={onClose} className="text-text-tertiary hover:text-text-primary">
          ✕
        </button>
      </div>
      <div className="flex-1 p-4">
        <p className="text-text-secondary">Dashboard content will be implemented based on master plan features.</p>
      </div>
    </div>
  );
}

