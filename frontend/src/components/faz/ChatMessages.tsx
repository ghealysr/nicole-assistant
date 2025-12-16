import React from 'react';
import { format } from 'date-fns';
import { Bot, User } from 'lucide-react';
import { useFazStore } from '@/lib/faz/store';
import ReactMarkdown from 'react-markdown';

export function ChatMessages() {
  const { messages } = useFazStore();
  const scrollRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-6">
      {messages.map((msg, idx) => (
        <div 
          key={idx} 
          className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
        >
          <div className={`
            w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
            ${msg.role === 'user' ? 'bg-[#1E1E2E] text-[#94A3B8]' : 'bg-[#6366F1]/20 text-[#6366F1]'}
          `}>
            {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
          </div>
          
          <div className={`max-w-[80%] space-y-1 ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col`}>
            <div className={`
              px-4 py-2.5 rounded-2xl text-sm leading-relaxed
              ${msg.role === 'user' 
                ? 'bg-[#1E1E2E] text-[#F1F5F9] rounded-tr-sm' 
                : 'bg-transparent text-[#F1F5F9] border border-[#1E1E2E] rounded-tl-sm'}
            `}>
              <ReactMarkdown 
                className="prose prose-invert prose-sm max-w-none"
                components={{
                  p: ({children}) => <p className="mb-2 last:mb-0">{children}</p>,
                  code: ({node, className, children, ...props}) => {
                    const match = /language-(\w+)/.exec(className || '')
                    return match ? (
                      <code className="block bg-[#0A0A0F] p-2 rounded text-xs font-mono my-2 overflow-x-auto" {...props}>
                        {children}
                      </code>
                    ) : (
                      <code className="bg-[#0A0A0F] px-1 py-0.5 rounded text-xs font-mono" {...props}>
                        {children}
                      </code>
                    )
                  }
                }}
              >
                {msg.content}
              </ReactMarkdown>
            </div>
            
            <span className="text-[10px] text-[#64748B] px-1">
              {msg.agent_name && <span className="font-medium mr-1 capitalize">{msg.agent_name} •</span>}
              {format(new Date(msg.created_at || Date.now()), 'HH:mm')}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

