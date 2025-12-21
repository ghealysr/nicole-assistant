/**
 * Faz Code Component Exports
 * 
 * Centralized exports for all Faz Code dashboard components.
 */

// Core Components
export { ApprovalPanel } from './ApprovalPanel';
export { LivePreview } from './LivePreview';
export { ProjectSetupStatus } from './ProjectSetupStatus';
export { AgentActivityFeed } from './AgentActivityFeed';
export { ChatMessages, useDismissApproval } from './ChatMessages';
export { ChatInput } from './ChatInput';
export { FileTree } from './FileTree';
export { StatusBadge } from './StatusBadge';

// Re-export types for convenience
export type { GateArtifact } from '@/lib/faz/store';
