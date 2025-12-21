/**
 * Faz Code Component Exports
 * 
 * Centralized exports for all Faz Code dashboard components.
 */

// Core Components
export { ApprovalPanel } from './ApprovalPanel';
export { ProjectSetupStatus } from './ProjectSetupStatus';
export { AgentActivityFeed } from './AgentActivityFeed';
export { ChatMessages, useDismissApproval } from './ChatMessages';
export { ChatInput } from './ChatInput';
export { FileTree } from './FileTree';
export { CodeViewer } from './CodeViewer';
export { WorkspaceLayout } from './WorkspaceLayout';
export { ProjectCard } from './ProjectCard';
export { StatusBadge } from './StatusBadge';
export { PreviewFrame } from './PreviewFrame';

// Re-export types for convenience
export type { GateArtifact } from '@/lib/faz/store';
export type { PreviewMode } from './PreviewFrame';
