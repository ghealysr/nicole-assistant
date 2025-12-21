'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { format } from 'date-fns';
import { 
  Bot, Code2, Search, Bug, CheckCircle, BrainCircuit, 
  AlertCircle, Sparkles, FileText, Palette, Zap, Eye
} from 'lucide-react';
import { FazActivity } from '@/types/faz';
import { useFazStore } from '@/lib/faz/store';
import { cn } from '@/lib/utils';

// Enhanced agent icons with better colors
const agentConfig: Record<string, { icon: React.ReactNode; color: string; bgColor: string }> = {
  nicole: { 
    icon: <Bot size={14} />, 
    color: 'text-orange-400', 
    bgColor: 'bg-orange-500/10 border-orange-500/20' 
  },
  planning: { 
    icon: <BrainCircuit size={14} />, 
    color: 'text-violet-400', 
    bgColor: 'bg-violet-500/10 border-violet-500/20' 
  },
  research: { 
    icon: <Search size={14} />, 
    color: 'text-blue-400', 
    bgColor: 'bg-blue-500/10 border-blue-500/20' 
  },
  design: { 
    icon: <Palette size={14} />, 
    color: 'text-pink-400', 
    bgColor: 'bg-pink-500/10 border-pink-500/20' 
  },
  coding: { 
    icon: <Code2 size={14} />, 
    color: 'text-yellow-400', 
    bgColor: 'bg-yellow-500/10 border-yellow-500/20' 
  },
  qa: { 
    icon: <Bug size={14} />, 
    color: 'text-amber-400', 
    bgColor: 'bg-amber-500/10 border-amber-500/20' 
  },
  review: { 
    icon: <CheckCircle size={14} />, 
    color: 'text-emerald-400', 
    bgColor: 'bg-emerald-500/10 border-emerald-500/20' 
  },
};

// Human-readable activity messages
const formatActivityMessage = (activity: FazActivity): string => {
  const agentName = activity.agent_name?.toLowerCase() || '';
  const message = String(activity.message || '');
  
  // Make Nicole's messages more conversational
  if (agentName === 'nicole') {
    if (message.includes('starting') || message.includes('Starting')) {
      return "I'm analyzing your request and preparing the project...";
    }
    if (message.includes('routing') || message.includes('Routing')) {
      return "Connecting you with the right specialist...";
    }
    if (message.includes('handoff') || message.includes('Handoff')) {
      const match = message.match(/to (\w+)/i);
      if (match) {
        const target = match[1].toLowerCase();
        const descriptions: Record<string, string> = {
          planning: "I'm bringing in our Planning specialist to create your architecture...",
          research: "Our Research team is gathering inspiration and best practices...",
          design: "The Design team will now create your visual system...",
          coding: "Our developers are now building your site...",
          qa: "Quality Assurance is reviewing the code...",
          review: "Final review in progress..."
        };
        return descriptions[target] || message;
      }
    }
  }
  
  // Format planning messages
  if (agentName === 'planning') {
    if (message.includes('architecture') || message.includes('structure')) {
      return "Designing the technical architecture...";
    }
    if (message.includes('components')) {
      return "Planning component hierarchy and relationships...";
    }
  }
  
  // Format research messages
  if (agentName === 'research') {
    if (message.includes('analyzing')) {
      return "Analyzing inspiration images and gathering ideas...";
    }
    if (message.includes('competitor')) {
      return "Researching competitor designs and best practices...";
    }
  }
  
  // Format design messages
  if (agentName === 'design') {
    if (message.includes('color') || message.includes('palette')) {
      return "Creating your color palette and visual identity...";
    }
    if (message.includes('typography')) {
      return "Selecting typography and type scale...";
    }
    if (message.includes('component')) {
      return "Designing reusable UI components...";
    }
  }
  
  // Format coding messages
  if (agentName === 'coding') {
    if (message.includes('generating') || message.includes('creating')) {
      const fileMatch = message.match(/file[s]?:?\s*(\d+)/i);
      if (fileMatch) {
        return `Building your site... ${fileMatch[1]} files generated`;
      }
      return "Building your site components...";
    }
    if (message.includes('implementing')) {
      return "Implementing the design system...";
    }
  }
  
  // Format QA messages
  if (agentName === 'qa') {
    if (message.includes('reviewing') || message.includes('checking')) {
      return "Reviewing code quality and best practices...";
    }
    if (message.includes('accessibility')) {
      return "Checking accessibility compliance...";
    }
    if (message.includes('passed') || message.includes('approved')) {
      return "✓ All quality checks passed!";
    }
    if (message.includes('issue') || message.includes('fix')) {
      return "Found some improvements, sending back to coding team...";
    }
  }
  
  return message;
};

const activityVariants = {
  initial: { opacity: 0, x: -20, scale: 0.95 },
  animate: { opacity: 1, x: 0, scale: 1 },
  exit: { opacity: 0, x: 20, scale: 0.95 }
};

interface ActivityItemProps {
  activity: FazActivity;
}

function ActivityItem({ activity }: ActivityItemProps) {
  const config = agentConfig[activity.agent_name.toLowerCase()] || agentConfig.nicole;
  const formattedMessage = formatActivityMessage(activity);
  
  const renderIcon = () => {
    switch (activity.content_type) {
      case 'thinking':
        return <Sparkles size={12} className="text-purple-400" />;
      case 'tool_call':
        return <Zap size={12} className="text-cyan-400" />;
      case 'response':
        return <FileText size={12} className="text-blue-400" />;
      case 'error':
        return <AlertCircle size={12} className="text-red-400" />;
      default:
        return config.icon;
    }
  };

  return (
    <motion.div
      variants={activityVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      layout
      className="relative"
    >
      {/* Timeline connector */}
      <div className="absolute left-3 top-8 bottom-0 w-px bg-zinc-800" />
      
      {/* Activity card */}
      <div className="flex gap-3">
        {/* Icon */}
        <div className={cn(
          "w-6 h-6 rounded-full border flex items-center justify-center flex-shrink-0 z-10",
          config.bgColor
        )}>
          <span className={config.color}>{renderIcon()}</span>
        </div>
        
        {/* Content */}
        <div className="flex-1 pb-4">
          <div className="flex items-center justify-between mb-1">
            <span className={cn("text-xs font-medium capitalize", config.color)}>
              {activity.agent_name}
            </span>
            <span className="text-[10px] text-zinc-600">
              {format(new Date(activity.started_at), 'HH:mm:ss')}
            </span>
          </div>
          
          {/* Message */}
          <div className={cn(
            "text-sm leading-relaxed",
            activity.content_type === 'error' ? 'text-red-400' : 'text-zinc-300'
          )}>
            {formattedMessage}
          </div>
          
          {/* Thinking indicator */}
          {activity.content_type === 'thinking' && activity.status === 'running' && (
            <div className="mt-2 flex items-center gap-2 text-xs text-zinc-500">
              <span className="flex gap-1">
                <span className="w-1 h-1 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1 h-1 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1 h-1 bg-zinc-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
              <span>Thinking...</span>
            </div>
          )}
          
          {/* Tool usage */}
          {activity.content_type === 'tool_call' && activity.details?.tool_name && (
            <div className="mt-1 inline-flex items-center gap-1.5 px-2 py-0.5 bg-cyan-500/10 border border-cyan-500/20 rounded text-[10px] text-cyan-400 font-mono">
              <Zap size={10} />
              {String(activity.details.tool_name)}
            </div>
          )}
          
          {/* Cost metrics */}
          {(activity.cost_cents > 0 || activity.output_tokens > 0) && activity.status === 'complete' && (
            <div className="flex gap-2 mt-2">
              {activity.cost_cents > 0 && (
                <span className="text-[10px] text-zinc-600 bg-zinc-800/50 px-1.5 py-0.5 rounded">
                  ${(activity.cost_cents / 100).toFixed(4)}
                </span>
              )}
              {activity.output_tokens > 0 && (
                <span className="text-[10px] text-zinc-600 bg-zinc-800/50 px-1.5 py-0.5 rounded">
                  {activity.output_tokens.toLocaleString()} tokens
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export function AgentActivityFeed() {
  const { activities, currentProject } = useFazStore();
  const scrollRef = React.useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new activities
  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [activities]);

  const isActive = currentProject?.status === 'processing' || 
                   currentProject?.status === 'building' ||
                   currentProject?.status === 'designing' ||
                   currentProject?.status === 'researching' ||
                   currentProject?.status === 'planning';

  return (
    <div className="h-full flex flex-col bg-[#0A0A0F] border-l border-zinc-800/50">
      {/* Header */}
      <div className="p-4 border-b border-zinc-800/50 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Eye size={14} className="text-zinc-500" />
          <h3 className="text-sm font-semibold text-zinc-200">Activity</h3>
        </div>
        <div className="flex items-center gap-2">
          {isActive ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
              </span>
              <span className="text-[10px] text-emerald-400 uppercase tracking-wider font-medium">Live</span>
            </>
          ) : (
            <span className="text-[10px] text-zinc-600 uppercase tracking-wider">Idle</span>
          )}
        </div>
      </div>

      {/* Activities */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar p-4">
        <AnimatePresence mode="popLayout">
          {activities.length === 0 ? (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-full text-center py-10"
            >
              <div className="w-12 h-12 rounded-full bg-zinc-800/50 flex items-center justify-center mb-3">
                <Bot className="w-6 h-6 text-zinc-600" />
              </div>
              <p className="text-sm text-zinc-500 mb-1">No activity yet</p>
              <p className="text-xs text-zinc-600">Nicole is ready to help you build</p>
            </motion.div>
          ) : (
            <div className="space-y-0">
              {activities.map((activity, idx) => (
                <ActivityItem 
                  key={`${activity.activity_id}-${activity.started_at}-${idx}`} 
                  activity={activity} 
                />
              ))}
            </div>
          )}
        </AnimatePresence>
      </div>

      {/* Summary footer */}
      {activities.length > 0 && (
        <div className="px-4 py-2 border-t border-zinc-800/50 bg-zinc-900/50">
          <div className="flex items-center justify-between text-[10px] text-zinc-600">
            <span>{activities.length} activities</span>
            <span>
              {activities.reduce((sum, a) => sum + (a.cost_cents || 0), 0) > 0 && (
                <>Total: ${(activities.reduce((sum, a) => sum + (a.cost_cents || 0), 0) / 100).toFixed(4)}</>
              )}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default AgentActivityFeed;
