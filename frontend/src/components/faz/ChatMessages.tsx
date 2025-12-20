'use client';

import React, { useState, useEffect, useRef } from 'react';
import { format } from 'date-fns';
import { Bot, User, CheckCircle2, XCircle, Loader2, ChevronDown, ChevronUp, Image as ImageIcon } from 'lucide-react';
import { useFazStore } from '@/lib/faz/store';
import { fazWS } from '@/lib/faz/websocket';
import ReactMarkdown from 'react-markdown';
import { motion, AnimatePresence } from 'framer-motion';

interface InlineApprovalButtonProps {
  messageIndex: number;
  onApprove: () => void;
  onDismiss: () => void;
  isSubmitting: boolean;
}

function InlineApprovalButton({ messageIndex, onApprove, onDismiss, isSubmitting }: InlineApprovalButtonProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="mt-3 flex items-center gap-2"
    >
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={onApprove}
        disabled={isSubmitting}
        className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
      >
        {isSubmitting ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <CheckCircle2 className="w-4 h-4" />
        )}
        <span>Approve</span>
      </motion.button>
      <span className="text-xs text-zinc-500">or type to provide feedback</span>
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
  const { messages, currentProject, currentGate } = useFazStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [pendingApprovalIndex, setPendingApprovalIndex] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [expandedArtifacts, setExpandedArtifacts] = useState<Set<string>>(new Set());

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Track which message has the approval button
  useEffect(() => {
    if (currentGate && messages.length > 0) {
      // Find the last message from Nicole that's asking for approval
      const lastNicoleIndex = messages.length - 1;
      const lastMessage = messages[lastNicoleIndex];
      
      if (lastMessage?.role === 'assistant' && 
          (lastMessage.content?.toLowerCase().includes('approve') || 
           lastMessage.content?.toLowerCase().includes('review') ||
           lastMessage.content?.toLowerCase().includes('ready for'))) {
        setPendingApprovalIndex(lastNicoleIndex);
      }
    } else {
      setPendingApprovalIndex(null);
    }
  }, [currentGate, messages]);

  // Dismiss approval button when user starts typing (handled in parent via prop)
  const handleApprove = async () => {
    setIsSubmitting(true);
    try {
      fazWS.approveGate(true);
      setPendingApprovalIndex(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDismissApproval = () => {
    setPendingApprovalIndex(null);
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

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-6">
      {messages.map((msg, idx) => {
        const { text, artifact } = parseArtifact(msg.content);
        const showApprovalButton = pendingApprovalIndex === idx && currentGate;
        const artifactKey = `${idx}-artifact`;
        
        return (
          <motion.div
            key={idx}
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
            
            <div className={`max-w-[80%] space-y-1 ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
              <div className={`
                px-4 py-2.5 rounded-2xl text-sm leading-relaxed
                ${msg.role === 'user' 
                  ? 'bg-[#1E1E2E] text-[#F1F5F9] rounded-tr-sm' 
                  : 'bg-transparent text-[#F1F5F9] border border-zinc-700/50 rounded-tl-sm'}
              `}>
                <ReactMarkdown 
                  className="prose prose-invert prose-sm max-w-none"
                  components={{
                    p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                    h1: ({children}) => <h1 className="text-lg font-bold mb-2 text-orange-400">{children}</h1>,
                    h2: ({children}) => <h2 className="text-base font-semibold mb-2 text-zinc-200">{children}</h2>,
                    h3: ({children}) => <h3 className="text-sm font-semibold mb-1 text-zinc-300">{children}</h3>,
                    ul: ({children}) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
                    ol: ({children}) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
                    li: ({children}) => <li className="text-zinc-300">{children}</li>,
                    strong: ({children}) => <strong className="text-orange-300 font-semibold">{children}</strong>,
                    code: ({className, children, ...props}) => {
                      const match = /language-(\w+)/.exec(className || '');
                      // Don't render large code blocks inline - they'll be in artifact
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
                
                {/* Inline approval button */}
                <AnimatePresence>
                  {showApprovalButton && (
                    <InlineApprovalButton
                      messageIndex={idx}
                      onApprove={handleApprove}
                      onDismiss={handleDismissApproval}
                      isSubmitting={isSubmitting}
                    />
                  )}
                </AnimatePresence>
              </div>
              
              <span className="text-[10px] text-[#64748B] px-1">
                {msg.agent_name && <span className="font-medium mr-1 capitalize text-orange-400/70">{msg.agent_name} •</span>}
                {format(new Date(msg.created_at || Date.now()), 'HH:mm')}
              </span>
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
            Describe your project below and Nicole will guide you through the entire process, 
            from planning to deployment.
          </p>
        </div>
      )}
    </div>
  );
}

// Export a function to dismiss approval button from parent
export function useDismissApproval() {
  return () => {
    // This would be called when user starts typing
    const store = useFazStore.getState();
    // Clear the gate to dismiss button
    store.setCurrentGate(null);
  };
}

export default ChatMessages;
