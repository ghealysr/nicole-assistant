"""
Claude AI integration for Nicole V7.
Primary LLM for complex reasoning and chat responses.

Now with full tool support for:
- Think Tool (explicit reasoning)
- Tool Search (dynamic tool discovery)
- Memory operations
- Document operations
"""

from typing import AsyncIterator, Optional, List, Dict, Any, Tuple, Union
import anthropic
import asyncio
import logging
import json

from app.config import settings

logger = logging.getLogger(__name__)


class ToolCallResult:
    """Result of a tool call execution."""
    def __init__(
        self,
        tool_use_id: str,
        tool_name: str,
        result: Any,
        is_error: bool = False
    ):
        self.tool_use_id = tool_use_id
        self.tool_name = tool_name
        self.result = result
        self.is_error = is_error
    
    def to_content_block(self) -> Dict[str, Any]:
        """Convert to Anthropic tool_result content block."""
        return {
            "type": "tool_result",
            "tool_use_id": self.tool_use_id,
            "content": json.dumps(self.result) if not isinstance(self.result, str) else self.result,
            "is_error": self.is_error
        }


class AlphawaveClaudeClient:
    """
    Claude AI client wrapper.
    
    Handles interactions with Anthropic Claude API (Sonnet 4.5 and Haiku 4.5).
    Now includes full tool support for agent architecture.
    Uses both sync client (for tool calls) and async client (for streaming).
    """
    
    def __init__(self):
        """Initialize Claude clients."""
        # Sync client for non-streaming and tool calls
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        # Async client for true async streaming
        self.async_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        # Use latest Claude Sonnet and Haiku models
        self.sonnet_model = "claude-sonnet-4-20250514"
        self.haiku_model = "claude-haiku-4-20250514"
        logger.info(f"Claude client initialized with Sonnet: {self.sonnet_model}, Haiku: {self.haiku_model}")
    
    async def generate_response(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Generate response from Claude (non-streaming).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            model: Model to use (defaults to Sonnet 4.5)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            tools: Optional list of tool definitions
            
        Returns:
            Generated response text
        """
        
        if model is None:
            model = self.sonnet_model
        
        try:
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_prompt if system_prompt else "",
                "messages": messages
            }
            
            if tools:
                kwargs["tools"] = tools
            
            response = self.client.messages.create(**kwargs)
            
            # Extract text from response
            if response.content and len(response.content) > 0:
                # Handle tool_use responses
                text_parts = []
                for block in response.content:
                    if hasattr(block, 'text'):
                        text_parts.append(block.text)
                return "".join(text_parts)
            
            return ""
            
        except Exception as e:
            logger.error(f"Claude API error: {e}", exc_info=True)
            raise
    
    async def generate_response_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_executor: Any,  # Callable that executes tools
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        max_tool_iterations: int = 10,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Generate response with tool use loop.
        
        Handles the full tool use cycle:
        1. Send message to Claude with tools
        2. If Claude uses a tool, execute it
        3. Send result back to Claude
        4. Repeat until Claude responds with text
        
        Args:
            messages: Conversation messages
            tools: List of tool definitions
            tool_executor: Async function that executes tools
            system_prompt: System prompt
            model: Model to use
            max_tokens: Max tokens per response
            temperature: Sampling temperature
            max_tool_iterations: Maximum tool use iterations
            
        Returns:
            Tuple of (final_text_response, list_of_tool_calls)
        """
        if model is None:
            model = self.sonnet_model
        
        conversation = list(messages)
        tool_calls_made = []
        iterations = 0
        
        while iterations < max_tool_iterations:
            iterations += 1
            
            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt if system_prompt else "",
                    messages=conversation,
                    tools=tools
                )
                
                # Check stop reason
                if response.stop_reason == "end_turn":
                    # Claude is done, extract text
                    text_parts = []
                    for block in response.content:
                        if hasattr(block, 'text'):
                            text_parts.append(block.text)
                    return "".join(text_parts), tool_calls_made
                
                elif response.stop_reason == "tool_use":
                    # Claude wants to use tools
                    assistant_content = []
                    tool_uses = []
                    
                    for block in response.content:
                        if block.type == "text":
                            assistant_content.append({
                                "type": "text",
                                "text": block.text
                            })
                        elif block.type == "tool_use":
                            assistant_content.append({
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input
                            })
                            tool_uses.append(block)
                    
                    # Add assistant message with tool uses
                    conversation.append({
                        "role": "assistant",
                        "content": assistant_content
                    })
                    
                    # Execute each tool and collect results
                    tool_results = []
                    for tool_use in tool_uses:
                        tool_call_record = {
                            "id": tool_use.id,
                            "name": tool_use.name,
                            "input": tool_use.input
                        }
                        
                        try:
                            result = await tool_executor(
                                tool_name=tool_use.name,
                                tool_input=tool_use.input
                            )
                            tool_call_record["result"] = result
                            tool_call_record["is_error"] = False
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": json.dumps(result) if not isinstance(result, str) else result
                            })
                        except Exception as e:
                            logger.error(f"Tool execution error for {tool_use.name}: {e}")
                            tool_call_record["result"] = str(e)
                            tool_call_record["is_error"] = True
                            
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": f"Error: {str(e)}",
                                "is_error": True
                            })
                        
                        tool_calls_made.append(tool_call_record)
                    
                    # Add user message with tool results
                    conversation.append({
                        "role": "user",
                        "content": tool_results
                    })
                
                else:
                    # Unknown stop reason, return what we have
                    logger.warning(f"Unexpected stop_reason: {response.stop_reason}")
                    text_parts = []
                    for block in response.content:
                        if hasattr(block, 'text'):
                            text_parts.append(block.text)
                    return "".join(text_parts), tool_calls_made
                    
            except Exception as e:
                logger.error(f"Tool loop error: {e}", exc_info=True)
                raise
        
        logger.warning(f"Reached max tool iterations ({max_tool_iterations})")
        return "I apologize, but I encountered an issue processing your request. Please try again.", tool_calls_made
    
    async def generate_streaming_response(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncIterator[str]:
        """
        Generate streaming response from Claude using async client.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            model: Model to use (defaults to Sonnet 4.5)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            tools: Optional list of tool definitions
            
        Yields:
            Text chunks as they're generated
        """
        
        if model is None:
            model = self.sonnet_model
        
        try:
            logger.info(f"Starting Claude async stream with model: {model}")
            
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_prompt if system_prompt else "",
                "messages": messages
            }
            
            if tools:
                kwargs["tools"] = tools
            
            async with self.async_client.messages.stream(**kwargs) as stream:
                chunk_count = 0
                async for text in stream.text_stream:
                    chunk_count += 1
                    yield text
                logger.info(f"Claude async stream complete, {chunk_count} chunks")
                    
        except Exception as e:
            logger.error(f"Claude streaming error: {e}", exc_info=True)
            raise
    
    async def generate_streaming_response_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_executor: Any,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        max_tool_iterations: int = 10,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Generate streaming response with tool use support.
        
        Uses Anthropic's native streaming API for the final text response
        to deliver true token-by-token streaming like Claude.ai.
        
        Flow:
        1. Tool iterations use non-streaming (necessary to execute tools)
        2. Final response uses real streaming from Anthropic API
        
        Yields events for:
        - text: Text content chunks (real tokens from API)
        - tool_use_start: Tool use beginning
        - tool_use_complete: Tool use finished
        - thinking: Think tool invocations
        - done: Stream complete
        
        Args:
            messages: Conversation messages
            tools: List of tool definitions
            tool_executor: Async function that executes tools
            system_prompt: System prompt
            model: Model to use
            max_tokens: Max tokens per response
            temperature: Sampling temperature
            max_tool_iterations: Maximum tool use iterations
            
        Yields:
            Event dictionaries with type and content
        """
        if model is None:
            model = self.sonnet_model
        
        conversation = list(messages)
        iterations = 0
        
        while iterations < max_tool_iterations:
            iterations += 1
            
            try:
                kwargs = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system_prompt if system_prompt else "",
                    "messages": conversation,
                    "tools": tools
                }
                
                # First, check if Claude wants to use tools (non-streaming probe)
                response = self.client.messages.create(**kwargs)
                
                # Check if we have tool uses
                has_tool_use = any(block.type == "tool_use" for block in response.content)
                
                if not has_tool_use or response.stop_reason == "end_turn":
                    # ============================================================
                    # FINAL RESPONSE: Use async streaming from Anthropic API
                    # This delivers true token-by-token streaming like Claude.ai
                    # ============================================================
                    logger.info("[STREAM] Final response - using native Anthropic async streaming")
                    
                    # Streaming pace: ~15ms delay for readable flow (50% slower)
                    STREAM_DELAY_MS = 15
                    
                    async with self.async_client.messages.stream(**kwargs) as stream:
                        async for text_chunk in stream.text_stream:
                            yield {
                                "type": "text",
                                "content": text_chunk
                            }
                            # Pace the stream for readable flow
                            await asyncio.sleep(STREAM_DELAY_MS / 1000)
                    
                    yield {"type": "done"}
                    return
                
                # Process tool uses (non-streaming path)
                assistant_content = []
                tool_uses = []
                
                for block in response.content:
                    if block.type == "text":
                        # Yield any text before tool use
                        if block.text:
                            yield {
                                "type": "text",
                                "content": block.text
                            }
                        assistant_content.append({
                            "type": "text",
                            "text": block.text
                        })
                    elif block.type == "tool_use":
                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input
                        })
                        tool_uses.append(block)
                
                # Add assistant message
                conversation.append({
                    "role": "assistant",
                    "content": assistant_content
                })
                
                # Execute tools and yield events
                tool_results = []
                for tool_use in tool_uses:
                    # Special handling for think tool
                    if tool_use.name == "think":
                        thought = tool_use.input.get("thought", "")
                        category = tool_use.input.get("category", "multi_step_planning")
                        conclusion = tool_use.input.get("conclusion", "")
                        
                        yield {
                            "type": "thinking",
                            "thought": thought,
                            "category": category,
                            "conclusion": conclusion
                        }
                        
                        # Think tool always succeeds
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": "Thinking recorded."
                        })
                        continue
                    
                    # Regular tool execution
                    yield {
                        "type": "tool_use_start",
                        "tool_name": tool_use.name,
                        "tool_id": tool_use.id
                    }
                    
                    try:
                        result = await tool_executor(
                            tool_name=tool_use.name,
                            tool_input=tool_use.input
                        )
                        
                        yield {
                            "type": "tool_use_complete",
                            "tool_name": tool_use.name,
                            "tool_id": tool_use.id,
                            "success": True
                        }
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": json.dumps(result) if not isinstance(result, str) else result
                        })
                        
                    except Exception as e:
                        logger.error(f"Tool execution error for {tool_use.name}: {e}")
                        
                        yield {
                            "type": "tool_use_complete",
                            "tool_name": tool_use.name,
                            "tool_id": tool_use.id,
                            "success": False,
                            "error": str(e)
                        }
                        
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True
                        })
                
                # Add tool results to conversation
                conversation.append({
                    "role": "user",
                    "content": tool_results
                })
                
            except Exception as e:
                logger.error(f"Streaming tool loop error: {e}", exc_info=True)
                yield {
                    "type": "error",
                    "message": str(e)
                }
                return
        
        logger.warning(f"Reached max tool iterations ({max_tool_iterations})")
        yield {
            "type": "error",
            "message": "Maximum tool iterations reached"
        }
    
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
