"""
Claude AI integration for Nicole V7.
Primary LLM for complex reasoning and chat responses.
"""

from typing import AsyncIterator, Optional, List, Dict, Any
import anthropic
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class AlphawaveClaudeClient:
    """
    Claude AI client wrapper.
    
    Handles interactions with Anthropic Claude API (Sonnet 4.5 and Haiku 4.5).
    """
    
    def __init__(self):
        """Initialize Claude client."""
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.sonnet_model = "claude-sonnet-4-5-20250929"
        self.haiku_model = "claude-haiku-4-5-20250514"
    
    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
    ) -> str:
        """
        Generate response from Claude (non-streaming).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            model: Model to use (defaults to Sonnet 4.5)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated response text
        """
        
        if model is None:
            model = self.sonnet_model
        
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=messages
            )
            
            # Extract text from response
            if response.content and len(response.content) > 0:
                return response.content[0].text
            
            return ""
            
        except Exception as e:
            logger.error(f"Claude API error: {e}", exc_info=True)
            raise
    
    async def generate_streaming_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
    ) -> AsyncIterator[str]:
        """
        Generate streaming response from Claude.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            model: Model to use (defaults to Sonnet 4.5)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Yields:
            Text chunks as they're generated
        """
        
        if model is None:
            model = self.sonnet_model
        
        try:
            with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except Exception as e:
            logger.error(f"Claude streaming error: {e}", exc_info=True)
            raise
    
    async def classify_with_haiku(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Fast classification/routing with Haiku model.
        
        Args:
            prompt: Classification prompt
            system_prompt: Optional system prompt
            
        Returns:
            Classification result
        """
        
        messages = [{"role": "user", "content": prompt}]
        
        return await self.generate_response(
            messages=messages,
            system_prompt=system_prompt,
            model=self.haiku_model,
            max_tokens=1024,
            temperature=0.0
        )
    
    def select_model(
        self,
        query_length: int,
        has_agents: bool,
        context_size: int
    ) -> str:
        """
        Select appropriate model based on complexity.
        
        Args:
            query_length: Length of query in words
            has_agents: Whether agents are needed
            context_size: Size of context in characters
            
        Returns:
            Model name to use
        """
        
        # Use Haiku for simple queries
        if query_length < 20 and not has_agents and context_size < 5000:
            return self.haiku_model
        
        # Use Sonnet for complex queries
        return self.sonnet_model


# Global client instance
claude_client = AlphawaveClaudeClient()
