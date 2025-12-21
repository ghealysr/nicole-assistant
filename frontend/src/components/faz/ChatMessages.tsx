'use client';

import React, { useState, useEffect, useRef } from 'react';
import { format } from 'date-fns';
import { 
  Bot, User, CheckCircle2, Loader2, ChevronDown, ChevronUp,
  MessageCircle, XCircle
} from 'lucide-react';
import { useFazStore } from '@/lib/faz/store';
import { fazWS } from '@/lib/faz/websocket';
import ReactMarkdown from 'react-markdown';
import { motion, AnimatePresence } from 'framer-motion';

// Gate display names and descriptions
const GATE_INFO: Record<string, { title: string; description: string }> = {
  awaiting_confirm: { 
    title: "Project Understanding", 
    description: "Review Nicole's understanding of your requirements" 
  },
  awaiting_research_review: { 
    title: "Research Complete", 
    description: "Review the research findings and inspiration analysis" 
  },
  awaiting_plan_approval: { 
    title: "Architecture Ready", 
    description: "Review the technical plan and file structure" 
  },
  awaiting_design_approval: { 
    title: "Design System Ready", 
    description: "Review colors, typography, and component styles" 
  },
  awaiting_qa_approval: { 
    title: "QA Complete", 
    description: "Review quality assurance findings" 
  },
  awaiting_user_testing: { 
    title: "User Testing", 
    description: "Test the site and provide feedback" 
  },
  awaiting_final_approval: { 
    title: "Ready for Deployment", 
    description: "Final review before going live" 
  },
};

interface InlineApprovalProps {
  gate: string;
  onApprove: () => void;
  onReject: (feedback: string) => void;
  isSubmitting: boolean;
}

function InlineApprovalPanel({ gate, onApprove, onReject, isSubmitting }: InlineApprovalProps) {
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedback, setFeedback] = useState('');
  const gateInfo = GATE_INFO[gate] || { title: 'Review Required', description: 'Please review before continuing' };

  const handleReject = () => {
    if (!feedback.trim()) {
      setShowFeedback(true);
      return;
    }
    onReject(feedback);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.95 }}
      className="mt-4 p-4 bg-gradient-to-br from-amber-500/10 via-orange-500/5 to-transparent border border-amber-500/30 rounded-xl"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center">
          <MessageCircle className="w-4 h-4 text-amber-400" />
        </div>
        <div>
          <p className="text-sm font-semibold text-white">{gateInfo.title}</p>
          <p className="text-xs text-zinc-400">{gateInfo.description}</p>
        </div>
      </div>

      {/* Feedback area (shown when rejecting) */}
      <AnimatePresence>
        {showFeedback && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-3"
          >
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="What would you like changed?"
              className="w-full h-20 px-3 py-2 bg-zinc-900/70 border border-zinc-700 rounded-lg text-white placeholder:text-zinc-500 focus:outline-none focus:ring-1 focus:ring-amber-500/50 resize-none text-sm"
              autoFocus
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Action buttons */}
      <div className="flex gap-2">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onApprove}
          disabled={isSubmitting}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          {isSubmitting ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <CheckCircle2 className="w-4 h-4" />
          )}
          <span>Approve</span>
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleReject}
          disabled={isSubmitting || (showFeedback && !feedback.trim())}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-700 hover:bg-zinc-600 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
        >
          <XCircle className="w-4 h-4" />
          <span>{showFeedback ? 'Submit Feedback' : 'Request Changes'}</span>
        </motion.button>
      </div>

      <p className="text-xs text-zinc-500 mt-2 text-center">
        Type a message to dismiss and provide feedback instead
      </p>
    </motion.div>
  );
}

interface ArtifactPreviewProps {
  content: string;
  title: string;
  isExpanded: boolean;
  onToggle: () => void;
}

function ArtifactPreview({ content, title, isExpanded, onToggle }: ArtifactPreviewProps) {
  return (
    <div className="mt-3 border border-zinc-700/50 rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 bg-zinc-800/50 hover:bg-zinc-800 transition-colors"
      >
        <span className="text-sm font-medium text-zinc-300">{title}</span>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-zinc-500" />
        ) : (
          <ChevronDown className="w-4 h-4 text-zinc-500" />
        )}
      </button>
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-3 bg-zinc-900/50 max-h-64 overflow-y-auto">
              <pre className="text-xs text-zinc-400 font-mono whitespace-pre-wrap">
                {content}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function ChatMessages() {
  const { messages, currentGate, currentProject } = useFazStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [expandedArtifacts, setExpandedArtifacts] = useState<Set<string>>(new Set());

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, currentGate]);

  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      fazWS.approveGate(true);
    } finally {
      setTimeout(() => setIsSubmitting(false), 500);
    }
  };

  const handleReject = async (feedback: string) => {
    setIsSubmitting(true);
    try {
      fazWS.rejectGate(feedback);
    } finally {
      setTimeout(() => setIsSubmitting(false), 500);
    }
  };

  const toggleArtifact = (key: string) => {
    setExpandedArtifacts(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  // Check if message contains an artifact to display
  const parseArtifact = (content: string): { text: string; artifact?: { title: string; content: string } } => {
    // Look for JSON code blocks that might be artifacts
    const jsonMatch = content.match(/```json\n?([\s\S]*?)```/);
    if (jsonMatch) {
      const text = content.replace(/```json\n?[\s\S]*?```/, '').trim();
      return {
        text,
        artifact: {
          title: 'View Details',
          content: jsonMatch[1].trim()
        }
      };
    }

    // Look for markdown code blocks
    const mdMatch = content.match(/```(?:markdown|md)?\n?([\s\S]*?)```/);
    if (mdMatch && mdMatch[1].length > 200) {
      const text = content.replace(/```(?:markdown|md)?\n?[\s\S]*?```/, '').trim();
      return {
        text: text || 'Here are the details:',
        artifact: {
          title: 'View Document',
          content: mdMatch[1].trim()
        }
      };
    }

    return { text: content };
  };

  // Determine if this is the last message and should show approval
  const shouldShowApproval = (idx: number) => {
    if (!currentGate) return false;
    if (idx !== messages.length - 1) return false;
    const msg = messages[idx];
    return msg.role === 'assistant';
  };

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-6">
      {messages.map((msg, idx) => {
        const { text, artifact } = parseArtifact(msg.content);
        const showApprovalButton = shouldShowApproval(idx);
        const artifactKey = `${idx}-artifact`;

        return (
          <motion.div
            key={msg.message_id || idx}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
          >
            <div className={`
              w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
              ${msg.role === 'user' ? 'bg-[#1E1E2E] text-[#94A3B8]' : 'bg-gradient-to-br from-orange-500/20 to-amber-500/20 text-orange-400'}
            `}>
              {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
            </div>

            <div className={`max-w-[85%] space-y-1 ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
              <div className={`
                px-4 py-2.5 rounded-2xl text-sm leading-relaxed
                ${msg.role === 'user'
                  ? 'bg-[#1E1E2E] text-[#F1F5F9] rounded-tr-sm'
                  : 'bg-transparent text-[#F1F5F9] border border-zinc-700/50 rounded-tl-sm'}
              `}>
                <ReactMarkdown
                  className="prose prose-invert prose-sm max-w-none"
                  components={{
                    p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                    h1: ({ children }) => <h1 className="text-lg font-bold mb-2 text-orange-400">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-base font-semibold mb-2 text-zinc-200">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-sm font-semibold mb-1 text-zinc-300">{children}</h3>,
                    ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                    li: ({ children }) => <li className="text-zinc-300">{children}</li>,
                    strong: ({ children }) => <strong className="text-orange-300 font-semibold">{children}</strong>,
                    code: ({ className, children, ...props }) => {
                      const match = /language-(\w+)/.exec(className || '');
                      if (match && String(children).length > 200) {
                        return null;
                      }
                      return match ? (
                        <code className="block bg-[#0A0A0F] p-2 rounded text-xs font-mono my-2 overflow-x-auto" {...props}>
                          {children}
                        </code>
                      ) : (
                        <code className="bg-[#0A0A0F] px-1 py-0.5 rounded text-xs font-mono" {...props}>
                          {children}
                        </code>
                      );
                    }
                  }}
                >
                  {text}
                </ReactMarkdown>

                {/* Collapsible artifact preview */}
                {artifact && (
                  <ArtifactPreview
                    content={artifact.content}
                    title={artifact.title}
                    isExpanded={expandedArtifacts.has(artifactKey)}
                    onToggle={() => toggleArtifact(artifactKey)}
                  />
                )}
              </div>

              <span className="text-[10px] text-[#64748B] px-1">
                {msg.agent_name && <span className="font-medium mr-1 capitalize text-orange-400/70">{msg.agent_name} •</span>}
                {format(new Date(msg.created_at || Date.now()), 'HH:mm')}
              </span>

              {/* Inline approval panel - shows after the last assistant message when at a gate */}
              <AnimatePresence>
                {showApprovalButton && currentGate && (
                  <InlineApprovalPanel
                    gate={currentGate}
                    onApprove={handleApprove}
                    onReject={handleReject}
                    isSubmitting={isSubmitting}
                  />
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        );
      })}

      {/* Empty state */}
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-center text-zinc-500 py-12">
          <Bot className="w-12 h-12 mb-4 opacity-30" />
          <p className="text-lg font-medium mb-2">Ready to build something amazing</p>
          <p className="text-sm max-w-md">
            Nicole will guide you through the entire process, presenting plans for your 
            approval at each step before building begins.
          </p>
        </div>
      )}

      {/* Processing indicator */}
      {currentProject?.status === 'processing' && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-3 text-[#94A3B8] px-4"
        >
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-500/20 to-amber-500/20 flex items-center justify-center">
            <Loader2 className="w-4 h-4 text-orange-400 animate-spin" />
          </div>
          <div className="flex items-center gap-2 text-sm">
            <span className="text-orange-400 font-medium capitalize">{currentProject.current_agent || 'Nicole'}</span>
            <span>is working...</span>
          </div>
        </motion.div>
      )}
    </div>
  );
}

// Export a hook to dismiss approval button from parent
export function useDismissApproval() {
  const { setCurrentGate } = useFazStore();
  return () => setCurrentGate(null);
}

export default ChatMessages;
