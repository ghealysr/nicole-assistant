import { AlphawaveMessageActions } from './AlphawaveMessageActions';

/**
 * Interface for message objects.
 */
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

/**
 * Props for AlphawaveMessageBubble.
 */
interface AlphawaveMessageBubbleProps {
  message: Message;
}

/**
 * Message bubble component for Nicole V7.
 * Displays Nicole's messages on the left with no background, user messages on the right with mint background.
 */
export function AlphawaveMessageBubble({ message }: AlphawaveMessageBubbleProps) {
  /**
   * Formats the timestamp for display.
   * @param date The date to format.
   * @returns Formatted time string.
   */
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (message.role === 'assistant') {
    return (
      <div className="flex justify-start">
        <div className="max-w-xs lg:max-w-md">
          <div className="flex items-center mb-2">
            <span className="text-lavender-text font-serif">Nicole</span>
            <span className="mx-2 text-text-tertiary">•</span>
            <span className="text-xs text-text-tertiary">{formatTime(message.timestamp)}</span>
          </div>
          <div className="p-3 text-text-primary">
            {message.content}
          </div>
          {/* Action buttons: 300ms debounced */}
          <AlphawaveMessageActions messageId={message.id} />
        </div>
      </div>
    );
  }

  // User message - mint background bubble
  return (
    <div className="flex justify-end">
      <div className="max-w-xs lg:max-w-md bg-mint rounded-lg p-3">
        <div className="flex items-center justify-end mb-2">
          <span className="text-xs text-mint-dark mr-2">{formatTime(message.timestamp)}</span>
          <span className="text-mint-dark font-medium">Glen</span>
        </div>
        <div className="text-text-primary">
          {message.content}
        </div>
      </div>
    </div>
  );
}

