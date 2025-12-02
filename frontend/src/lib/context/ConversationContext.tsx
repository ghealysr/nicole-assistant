'use client';

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

/**
 * Context for managing conversation state across components
 */
interface ConversationContextType {
  currentConversationId: number | null;
  setCurrentConversationId: (id: number | null) => void;
  clearConversation: () => void;
}

const ConversationContext = createContext<ConversationContextType>({
  currentConversationId: null,
  setCurrentConversationId: () => {},
  clearConversation: () => {},
});

export const useConversation = () => useContext(ConversationContext);

interface ConversationProviderProps {
  children: ReactNode;
}

export function ConversationProvider({ children }: ConversationProviderProps) {
  const [currentConversationId, setCurrentConversationId] = useState<number | null>(null);

  const clearConversation = useCallback(() => {
    setCurrentConversationId(null);
  }, []);

  return (
    <ConversationContext.Provider value={{
      currentConversationId,
      setCurrentConversationId,
      clearConversation,
    }}>
      {children}
    </ConversationContext.Provider>
  );
}

