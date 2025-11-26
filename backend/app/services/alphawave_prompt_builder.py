"""
Prompt Builder Service for Nicole V7.
Dynamically constructs prompts for different agents and contexts.

QA NOTES:
- Loads agent prompts from markdown files in agents/prompts/
- Injects user context, memories, and conversation history
- Handles agent routing based on query classification
- Supports both streaming and non-streaming responses
"""

import logging
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from uuid import UUID

from app.config import settings
from app.services.alphawave_memory_service import memory_service

logger = logging.getLogger(__name__)

# Path to agent prompts
PROMPTS_DIR = Path(__file__).parent.parent / "agents" / "prompts"


class AlphawavePromptBuilder:
    """
    Service for building dynamic prompts with context injection.
    
    Features:
    - Load and cache agent prompts
    - Inject user-specific context
    - Add relevant memories to prompts
    - Handle conversation history
    - Route to specialized agents
    """
    
    def __init__(self):
        """Initialize the prompt builder."""
        self._prompt_cache: Dict[str, str] = {}
        self._load_prompts()
    
    def _load_prompts(self) -> None:
        """Load all agent prompts into cache."""
        if not PROMPTS_DIR.exists():
            logger.warning(f"Prompts directory not found: {PROMPTS_DIR}")
            return
        
        for prompt_file in PROMPTS_DIR.glob("*.md"):
            agent_name = prompt_file.stem
            try:
                content = prompt_file.read_text(encoding="utf-8")
                if content.strip():  # Only cache non-empty prompts
                    self._prompt_cache[agent_name] = content
                    logger.debug(f"Loaded prompt: {agent_name}")
            except Exception as e:
                logger.error(f"Error loading prompt {agent_name}: {e}")
        
        logger.info(f"Loaded {len(self._prompt_cache)} agent prompts")
    
    def get_agent_prompt(self, agent_name: str) -> Optional[str]:
        """
        Get the base prompt for an agent.
        
        Args:
            agent_name: Name of the agent (e.g., 'nicole_core', 'business_agent')
            
        Returns:
            The agent's base prompt or None if not found
        """
        return self._prompt_cache.get(agent_name)
    
    def list_available_agents(self) -> List[str]:
        """List all available agent names."""
        return list(self._prompt_cache.keys())
    
    async def build_chat_prompt(
        self,
        user_id: UUID,
        user_name: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        agent_name: str = "nicole_core",
        include_memories: bool = True,
        max_memories: int = 5
    ) -> str:
        """
        Build a complete chat prompt with context.
        
        Args:
            user_id: The user's UUID
            user_name: The user's display name
            user_message: The current message from the user
            conversation_history: Previous messages in the conversation
            agent_name: Which agent prompt to use
            include_memories: Whether to include relevant memories
            max_memories: Maximum number of memories to include
            
        Returns:
            The complete system prompt
            
        QA NOTE: This is the main entry point for prompt building
        """
        # Get base agent prompt
        base_prompt = self.get_agent_prompt(agent_name)
        if not base_prompt:
            logger.warning(f"Agent '{agent_name}' not found, using nicole_core")
            base_prompt = self.get_agent_prompt("nicole_core") or self._get_fallback_prompt()
        
        # Build context sections
        context_sections = []
        
        # Add user context
        context_sections.append(f"## Current User\nYou are speaking with {user_name}.")
        
        # Add relevant memories if requested
        if include_memories:
            memories = await self._get_relevant_memories(
                user_id, user_message, max_memories
            )
            if memories:
                memory_text = "\n".join([
                    f"- {m['content']} (confidence: {m.get('confidence_score', 0.5):.0%})"
                    for m in memories
                ])
                context_sections.append(f"## Relevant Memories\n{memory_text}")
        
        # Add conversation context
        if conversation_history:
            recent_messages = conversation_history[-6:]  # Last 6 messages
            history_text = "\n".join([
                f"{'User' if m['role'] == 'user' else 'Nicole'}: {m['content'][:200]}..."
                if len(m['content']) > 200 else
                f"{'User' if m['role'] == 'user' else 'Nicole'}: {m['content']}"
                for m in recent_messages
            ])
            context_sections.append(f"## Recent Conversation\n{history_text}")
        
        # Combine everything
        context_block = "\n\n".join(context_sections)
        
        full_prompt = f"""{base_prompt}

---

# CURRENT CONTEXT

{context_block}

---

Remember to stay in character and use the context above to inform your response.
"""
        
        return full_prompt
    
    async def _get_relevant_memories(
        self,
        user_id: UUID,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Fetch relevant memories for the current context."""
        try:
            memories = await memory_service.search_memory(
                user_id=user_id,
                query=query,
                limit=max_results,
                min_confidence=0.3
            )
            return memories
        except Exception as e:
            logger.warning(f"Error fetching memories: {e}")
            return []
    
    def _get_fallback_prompt(self) -> str:
        """Return a basic fallback prompt if no agent prompts are loaded."""
        return """You are Nicole, a warm and intelligent AI companion.

You are kind, helpful, and genuinely care about the people you interact with.
You have a great memory and pay attention to details about people's lives.
You communicate naturally and conversationally, like a close friend.

Be helpful, be kind, and be yourself."""
    
    async def classify_query_intent(
        self,
        query: str
    ) -> Dict[str, Any]:
        """
        Classify the intent of a user query for agent routing.
        
        Args:
            query: The user's message
            
        Returns:
            Dict with 'agent', 'confidence', and 'reasoning'
            
        QA NOTE: Simple keyword-based routing for now.
        Could be enhanced with Claude Haiku classification.
        """
        query_lower = query.lower()
        
        # Define keyword patterns for each agent
        patterns = {
            "business_agent": [
                "client", "invoice", "proposal", "contract", "business",
                "meeting", "schedule", "project", "deadline", "deliverable"
            ],
            "design_agent": [
                "design", "logo", "brand", "color", "layout", "ui", "ux",
                "mockup", "wireframe", "typography", "visual"
            ],
            "code_review_agent": [
                "code", "review", "bug", "error", "function", "class",
                "refactor", "optimize", "debug", "syntax"
            ],
            "seo_agent": [
                "seo", "keyword", "ranking", "google", "search",
                "traffic", "meta", "backlink", "optimization"
            ],
            "research_agent": [
                "research", "analyze", "compare", "investigate", "study",
                "deep dive", "explore", "understand"
            ]
        }
        
        # Score each agent
        scores = {}
        for agent, keywords in patterns.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[agent] = score
        
        # Return the best match or default to nicole_core
        if scores:
            best_agent = max(scores, key=scores.get)
            confidence = min(scores[best_agent] / 3, 1.0)  # Normalize to 0-1
            return {
                "agent": best_agent,
                "confidence": confidence,
                "reasoning": f"Matched {scores[best_agent]} keywords for {best_agent}"
            }
        
        return {
            "agent": "nicole_core",
            "confidence": 1.0,
            "reasoning": "No specialized agent matched, using core personality"
        }
    
    async def build_agent_prompt_with_routing(
        self,
        user_id: UUID,
        user_name: str,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> tuple[str, str]:
        """
        Automatically route to the appropriate agent and build the prompt.
        
        Args:
            user_id: The user's UUID
            user_name: The user's display name
            user_message: The current message
            conversation_history: Previous messages
            
        Returns:
            Tuple of (system_prompt, agent_name)
        """
        # Classify the intent
        intent = await self.classify_query_intent(user_message)
        agent_name = intent["agent"]
        
        logger.info(
            f"Routed to {agent_name} with {intent['confidence']:.0%} confidence: "
            f"{intent['reasoning']}"
        )
        
        # Build the prompt for the selected agent
        prompt = await self.build_chat_prompt(
            user_id=user_id,
            user_name=user_name,
            user_message=user_message,
            conversation_history=conversation_history,
            agent_name=agent_name
        )
        
        return prompt, agent_name


# Global service instance
prompt_builder = AlphawavePromptBuilder()

