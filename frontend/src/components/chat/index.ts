/**
 * Chat Components Index
 * 
 * Exports all chat-related components for easy importing.
 */

// Main chat components
export { AlphawaveChatContainer } from './AlphawaveChatContainer';
export { AlphawaveChatInput } from './AlphawaveChatInput';
export type { FileAttachment } from './AlphawaveChatInput';
export { AlphawaveDashPanel } from './AlphawaveDashPanel';
export { AlphawaveChatsPanel } from './AlphawaveChatsPanel';

// Nicole's Message Renderer (enhanced markdown + components)
export { NicoleMessageRenderer } from './NicoleMessageRenderer';

// Nicole's Orb Animation (legacy - kept for compatibility)
export { NicoleOrbAnimation, NicoleThinkingIndicator } from './NicoleOrbAnimation';
export type { NicoleOrbAnimationProps, ThinkingIndicatorProps as OrbThinkingIndicatorProps } from './NicoleOrbAnimation';

// LotusSphere - Canvas-based premium thinking animation (new)
export { LotusSphere } from './LotusSphere';
export type { LotusSphereProps, ThinkingState } from './LotusSphere';

// ThinkingIndicator - Claude-style inline thinking indicator (new)
export { ThinkingIndicator, GlowingIndicator, useThinkingState } from './ThinkingIndicator';
export type { ThinkingIndicatorProps, GlowingIndicatorProps, UseThinkingStateOptions, UseThinkingStateResult } from './ThinkingIndicator';

// Nicole's Thinking Block (extended thinking display)
export { NicoleThinkingBlock } from './NicoleThinkingBlock';
export type { ThinkingBlockProps, ToolUse } from './NicoleThinkingBlock';

// Nicole's Workflow Progress (multi-step workflow tracking)
export { WorkflowProgress } from './WorkflowProgress';

// Nicole's Thinking UI Components
export {
  // Main components
  ThinkingBox,
  FileCard,
  StyledTable,
  FileLink,
  NoteCard,
  StyledList,
  StyledListItem,
  FileBadge,
  GradientButton,
  StepIcon,
  
  // Colors
  nicoleColors,
  colors,
  
  // Icons
  CheckIcon,
  SpinnerIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  SparklesIcon,
  CopyIcon,
  DownloadIcon,
  ExternalLinkIcon,
  FileCodeIcon,
  FileTextIcon,
  ClockIcon,
  LightbulbIcon,
} from './NicoleThinkingUI';

// Types
export type { ThinkingStep, StepStatus } from './NicoleThinkingUI';

