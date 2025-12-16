import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { format } from 'date-fns';
import { Bot, Code2, Search, PenTool, Bug, CheckCircle, BrainCircuit, AlertCircle } from 'lucide-react';
import { FazActivity } from '@/types/faz';
import { useFazStore } from '@/lib/faz/store';

const agentIcons: Record<string, React.ReactNode> = {
  nicole: <Bot size={16} className="text-purple-400" />,
  planning: <BrainCircuit size={16} className="text-indigo-400" />,
  research: <Search size={16} className="text-blue-400" />,
  design: <PenTool size={16} className="text-pink-400" />,
  coding: <Code2 size={16} className="text-yellow-400" />,
  qa: <Bug size={16} className="text-orange-400" />,
  review: <CheckCircle size={16} className="text-green-400" />,
};

const activityVariants = {
  initial: { opacity: 0, x: -20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 20 }
};

export function AgentActivityFeed() {
  const { activities } = useFazStore();
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [activities]);

  const renderContent = (activity: FazActivity) => {
    switch (activity.content_type) {
      case 'thinking':
        return (
          <div className="text-xs text-[#94A3B8] italic border-l-2 border-[#1E1E2E] pl-2 my-1">
            Thinking: {activity.message}
          </div>
        );
      case 'tool_call':
        return (
          <div className="text-xs text-[#94A3B8] bg-[#12121A] p-2 rounded my-1 font-mono">
            🛠️ Using tool: {activity.details?.tool_name || 'unknown'}
          </div>
        );
      case 'error':
        return (
          <div className="text-sm text-red-400 bg-red-950/20 p-2 rounded my-1 flex items-start gap-2">
            <AlertCircle size={14} className="mt-0.5" />
            {activity.message}
          </div>
        );
      default:
        return <div className="text-sm text-[#F1F5F9]">{activity.message}</div>;
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0A0A0F] border-l border-[#1E1E2E]">
      <div className="p-4 border-b border-[#1E1E2E] flex justify-between items-center">
        <h3 className="text-sm font-semibold text-[#F1F5F9]">Agent Activity</h3>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="text-xs text-[#94A3B8]">LIVE</span>
        </div>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
        <AnimatePresence mode="popLayout">
          {activities.length === 0 ? (
            <div className="text-center text-[#64748B] text-sm py-10">
              No activity yet. Start the pipeline!
            </div>
          ) : (
            activities.map((activity) => (
              <motion.div
                key={`${activity.activity_id}-${activity.started_at}`}
                variants={activityVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                layout
                className="relative pl-8 pb-4 border-l border-[#1E1E2E] last:border-0 last:pb-0"
              >
                <div className="absolute left-[-16px] top-0 bg-[#12121A] border border-[#1E1E2E] p-1.5 rounded-full shadow-lg z-10">
                  {agentIcons[activity.agent_name.toLowerCase()] || <Bot size={16} />}
                </div>
                
                <div className="flex flex-col gap-1">
                  <div className="flex justify-between items-start">
                    <span className="text-xs font-medium text-[#94A3B8] uppercase tracking-wide">
                      {activity.agent_name}
                    </span>
                    <span className="text-[10px] text-[#64748B]">
                      {format(new Date(activity.started_at), 'HH:mm:ss')}
                    </span>
                  </div>
                  
                  {renderContent(activity)}
                  
                  {(activity.cost_cents > 0 || activity.output_tokens > 0) && (
                    <div className="flex gap-2 mt-1">
                      {activity.cost_cents > 0 && (
                        <span className="text-[10px] text-[#64748B] bg-[#12121A] px-1.5 py-0.5 rounded">
                          ${(activity.cost_cents / 100).toFixed(4)}
                        </span>
                      )}
                      {activity.output_tokens > 0 && (
                        <span className="text-[10px] text-[#64748B] bg-[#12121A] px-1.5 py-0.5 rounded">
                          {activity.output_tokens} tok
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

