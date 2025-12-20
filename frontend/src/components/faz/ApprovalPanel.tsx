'use client';

/**
 * ApprovalPanel Component
 * 
 * Displays artifacts at approval gates and allows users to approve/reject/provide feedback.
 * Used in interactive pipeline mode to review agent outputs before continuing.
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle2, 
  XCircle, 
  MessageSquare, 
  ChevronDown,
  ChevronUp,
  FileText,
  Code2,
  Palette,
  ClipboardCheck,
  Star,
  Loader2
} from 'lucide-react';
import { useFazStore } from '@/lib/faz/store';
import { fazWS } from '@/lib/faz/websocket';
import type { ArtifactType } from '@/types/faz';

interface ApprovalPanelProps {
  onApprove?: (feedback?: string) => void;
  onReject?: (feedback: string) => void;
}

const ARTIFACT_ICONS: Record<ArtifactType, React.ElementType> = {
  project_brief: FileText,
  research: FileText,
  architecture: Code2,
  design_system: Palette,
  qa_report: ClipboardCheck,
  review_summary: Star,
  custom: FileText,
};

const ARTIFACT_TITLES: Record<ArtifactType, string> = {
  project_brief: 'Project Understanding',
  research: 'Research Findings',
  architecture: 'Architecture Plan',
  design_system: 'Design System',
  qa_report: 'QA Report',
  review_summary: 'Final Review',
  custom: 'Document',
};

const GATE_DESCRIPTIONS: Record<string, string> = {
  awaiting_confirm: "Review Nicole's understanding of your project requirements.",
  awaiting_research_review: "Review the research findings and design inspiration.",
  awaiting_plan_approval: "Review the proposed architecture and technical plan.",
  awaiting_design_approval: "Review the design system and visual tokens.",
  awaiting_qa_approval: "Review the QA findings and decide on fixes.",
  awaiting_final_approval: "Final review before deployment.",
};

export function ApprovalPanel({ onApprove, onReject }: ApprovalPanelProps) {
  const { currentProject } = useFazStore();
  const [feedback, setFeedback] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [expandedArtifact, setExpandedArtifact] = useState<string | null>(null);
  
  // Get current gate and artifacts
  const currentGate = currentProject?.awaiting_approval_for;
  const artifacts = currentProject?.artifacts || [];
  
  // Check if we're at a gate
  const isAtGate = useMemo(() => {
    return currentGate && currentGate.startsWith('awaiting_');
  }, [currentGate]);
  
  if (!isAtGate) {
    return null;
  }
  
  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      if (onApprove) {
        onApprove(feedback || undefined);
      } else {
        fazWS.approveGate(true, feedback || undefined);
      }
      setFeedback('');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleReject = async () => {
    if (!feedback.trim()) {
      alert('Please provide feedback on what needs to be changed.');
      return;
    }
    
    setIsSubmitting(true);
    try {
      if (onReject) {
        onReject(feedback);
      } else {
        fazWS.rejectGate(feedback);
      }
      setFeedback('');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const toggleArtifact = (type: string) => {
    setExpandedArtifact(prev => prev === type ? null : type);
  };
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="bg-gradient-to-br from-amber-500/10 via-orange-500/5 to-transparent border border-amber-500/30 rounded-xl p-5"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
          <MessageSquare className="w-5 h-5 text-amber-400" />
        </div>
        <div>
          <h3 className="font-semibold text-white">Review Required</h3>
          <p className="text-sm text-zinc-400">
            {GATE_DESCRIPTIONS[currentGate || ''] || 'Please review the following before continuing.'}
          </p>
        </div>
      </div>
      
      {/* Artifacts */}
      <div className="space-y-3 mb-5">
        <AnimatePresence>
          {artifacts.map((artifact) => {
            const Icon = ARTIFACT_ICONS[artifact.artifact_type] || FileText;
            const title = ARTIFACT_TITLES[artifact.artifact_type] || artifact.title;
            const isExpanded = expandedArtifact === artifact.artifact_type;
            
            return (
              <motion.div
                key={artifact.artifact_type}
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="bg-zinc-900/50 border border-zinc-700/50 rounded-lg overflow-hidden"
              >
                {/* Artifact Header */}
                <button
                  onClick={() => toggleArtifact(artifact.artifact_type)}
                  className="w-full flex items-center justify-between p-3 hover:bg-zinc-800/50 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-4 h-4 text-zinc-400" />
                    <span className="font-medium text-zinc-200">{title}</span>
                    {artifact.is_approved && (
                      <span className="text-xs px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded-full">
                        Approved
                      </span>
                    )}
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-zinc-500" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-zinc-500" />
                  )}
                </button>
                
                {/* Artifact Content */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="border-t border-zinc-700/50"
                    >
                      <div className="p-4 max-h-96 overflow-y-auto">
                        <pre className="text-sm text-zinc-300 whitespace-pre-wrap font-mono leading-relaxed">
                          {artifact.content}
                        </pre>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </AnimatePresence>
        
        {artifacts.length === 0 && (
          <div className="text-center py-6 text-zinc-500">
            <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Waiting for artifacts...</p>
          </div>
        )}
      </div>
      
      {/* Feedback Input */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-zinc-400 mb-2">
          Feedback (optional for approval, required for rejection)
        </label>
        <textarea
          value={feedback}
          onChange={(e) => setFeedback(e.target.value)}
          placeholder="Add any feedback or requested changes..."
          className="w-full h-24 px-3 py-2 bg-zinc-900/70 border border-zinc-700 rounded-lg text-white placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 resize-none"
        />
      </div>
      
      {/* Action Buttons */}
      <div className="flex gap-3">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleApprove}
          disabled={isSubmitting}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <CheckCircle2 className="w-4 h-4" />
          )}
          <span>Approve & Continue</span>
        </motion.button>
        
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleReject}
          disabled={isSubmitting || !feedback.trim()}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-zinc-700 hover:bg-zinc-600 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <XCircle className="w-4 h-4" />
          )}
          <span>Request Changes</span>
        </motion.button>
      </div>
    </motion.div>
  );
}

export default ApprovalPanel;

