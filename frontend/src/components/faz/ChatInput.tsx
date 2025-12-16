import React from 'react';
import { Send } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = React.useState('');
  const textareaRef = React.useRef<HTMLTextAreaElement>(null);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if (!input.trim() || disabled) return;
    onSend(input);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  return (
    <div className="relative bg-[#12121A] border border-[#1E1E2E] rounded-xl focus-within:border-[#6366F1] transition-colors">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        placeholder="Ask Nicole to change something..."
        className="w-full bg-transparent text-[#F1F5F9] placeholder-[#64748B] p-4 pr-12 text-sm resize-none outline-none min-h-[50px] max-h-[200px]"
        rows={1}
        disabled={disabled}
      />
      <button
        onClick={handleSubmit}
        disabled={!input.trim() || disabled}
        className={cn(
          "absolute right-3 bottom-3 p-1.5 rounded-lg transition-all",
          input.trim() && !disabled
            ? "bg-[#6366F1] text-white hover:bg-[#818CF8]" 
            : "bg-[#1E1E2E] text-[#64748B] cursor-not-allowed"
        )}
      >
        <Send size={16} />
      </button>
      <div className="absolute left-4 -bottom-6 text-[10px] text-[#64748B]">
        Cmd + Enter to send
      </div>
    </div>
  );
}

