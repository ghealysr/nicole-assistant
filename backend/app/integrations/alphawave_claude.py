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
        Generate streaming response from Claude using sync client with chunking.
        
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
            logger.info(f"[CLAUDE] Starting sync stream with model: {model}, messages: {len(messages)}")
            
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_prompt if system_prompt else "",
                "messages": messages
            }
            
            if tools:
                kwargs["tools"] = tools
            
            # Use sync client with native streaming
            with self.client.messages.stream(**kwargs) as stream:
                chunk_count = 0
                for text in stream.text_stream:
                    chunk_count += 1
                    yield text
                logger.info(f"[CLAUDE] Sync stream complete, {chunk_count} chunks")
                    
        except Exception as e:
            logger.error(f"[CLAUDE] Streaming error: {e}", exc_info=True)
            raise
    
    async def generate_streaming_response_with_thinking(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 16000,
        thinking_budget: int = 10000,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Generate streaming response with extended thinking enabled.
        
        Yields events:
        - {"type": "thinking_start"}
        - {"type": "thinking_delta", "content": "..."}
        - {"type": "thinking_stop", "duration": 3.2}
        - {"type": "text_delta", "content": "..."}
        - {"type": "done"}
        
        Args:
            messages: Conversation messages
            system_prompt: System prompt
            model: Model to use
            max_tokens: Max tokens for response
            thinking_budget: Max tokens for thinking
        """
        import time
        
        if model is None:
            model = self.sonnet_model
        
        thinking_start_time = None
        in_thinking = False
        
        try:
            logger.info(f"[CLAUDE] Starting extended thinking stream with budget: {thinking_budget}")
            
            # Build request with extended thinking enabled
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "system": system_prompt if system_prompt else "",
                "messages": messages,
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": thinking_budget
                }
            }
            
            # Stream with raw events to capture thinking blocks
            with self.client.messages.stream(**kwargs) as stream:
                for event in stream:
                    event_type = getattr(event, 'type', None)
                    
                    if event_type == 'content_block_start':
                        block = getattr(event, 'content_block', None)
                        if block and getattr(block, 'type', None) == 'thinking':
                            in_thinking = True
                            thinking_start_time = time.time()
                            yield {"type": "thinking_start"}
                        elif block and getattr(block, 'type', None) == 'text':
                            if in_thinking:
                                # Thinking just ended
                                duration = time.time() - thinking_start_time if thinking_start_time else 0
                                yield {"type": "thinking_stop", "duration": round(duration, 1)}
                                in_thinking = False
                    
                    elif event_type == 'content_block_delta':
                        delta = getattr(event, 'delta', None)
                        if delta:
                            delta_type = getattr(delta, 'type', None)
                            if delta_type == 'thinking_delta':
                                thinking_text = getattr(delta, 'thinking', '')
                                if thinking_text:
                                    yield {"type": "thinking_delta", "content": thinking_text}
                            elif delta_type == 'text_delta':
                                text = getattr(delta, 'text', '')
                                if text:
                                    yield {"type": "text_delta", "content": text}
                    
                    elif event_type == 'content_block_stop':
                        if in_thinking:
                            duration = time.time() - thinking_start_time if thinking_start_time else 0
                            yield {"type": "thinking_stop", "duration": round(duration, 1)}
                            in_thinking = False
            
            yield {"type": "done"}
            logger.info("[CLAUDE] Extended thinking stream complete")
            
        except anthropic.BadRequestError as e:
            # Extended thinking not supported - fall back to standard streaming
            logger.warning(f"[CLAUDE] Extended thinking not available: {e}. Falling back to standard.")
            async for text in self.generate_streaming_response(
                messages=messages,
                system_prompt=system_prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=1.0
            ):
                yield {"type": "text_delta", "content": text}
            yield {"type": "done"}
            
        except Exception as e:
            logger.error(f"[CLAUDE] Extended thinking error: {e}", exc_info=True)
            yield {"type": "error", "message": str(e)}
    
    async def generate_streaming_response_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_executor: Any,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 16000,
        temperature: float = 1.0,
        max_tool_iterations: int = 10,
        enable_thinking: bool = True,
        thinking_budget: int = 8000,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Generate streaming response with tool use and extended thinking support.
        
        Flow:
        1. Enable extended thinking for reasoning
        2. Stream thinking deltas (fast)
        3. Handle tool use loops
        4. Stream final response
        
        Yields events for:
        - thinking_start: Thinking begins
        - thinking_delta: Thinking content (fast stream)
        - thinking_stop: Thinking complete with duration
        - text: Text content chunks
        - tool_use_start: Tool use beginning
        - tool_use_complete: Tool use finished
        - done: Stream complete
        """
        import time
        
        if model is None:
            model = self.sonnet_model
        
        conversation = list(messages)
        iterations = 0
        thinking_emitted = False
        
        logger.info(f"[CLAUDE] Starting response with thinking={enable_thinking}, budget={thinking_budget}")
        
        while iterations < max_tool_iterations:
            iterations += 1
            
            try:
                kwargs = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "system": system_prompt if system_prompt else "",
                    "messages": conversation,
                    "tools": tools
                }
                
                # Add extended thinking if enabled and first iteration
                if enable_thinking and iterations == 1:
                    kwargs["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": thinking_budget
                    }
                    # Can't use temperature with thinking
                else:
                    kwargs["temperature"] = temperature
                
                logger.info(f"[CLAUDE] Iteration {iterations} - calling Claude API")
                
                # Stream to capture thinking + tool decisions
                thinking_start_time = None
                in_thinking = False
                tool_uses_this_round = []
                text_buffer = []
                
                with self.client.messages.stream(**kwargs) as stream:
                    for event in stream:
                        event_type = getattr(event, 'type', None)
                        
                        if event_type == 'content_block_start':
                            block = getattr(event, 'content_block', None)
                            block_type = getattr(block, 'type', None) if block else None
                            
                            if block_type == 'thinking':
                                in_thinking = True
                                thinking_start_time = time.time()
                                if not thinking_emitted:
                                    yield {"type": "thinking_start"}
                                    thinking_emitted = True
                            
                            elif block_type == 'tool_use':
                                tool_id = getattr(block, 'id', '')
                                tool_name = getattr(block, 'name', '')
                                tool_uses_this_round.append({
                                    'id': tool_id,
                                    'name': tool_name,
                                    'input': {}
                                })
                                yield {"type": "tool_use_start", "tool_name": tool_name, "tool_id": tool_id}
                        
                        elif event_type == 'content_block_delta':
                            delta = getattr(event, 'delta', None)
                            if delta:
                                delta_type = getattr(delta, 'type', None)
                                
                                if delta_type == 'thinking_delta':
                                    thinking_text = getattr(delta, 'thinking', '')
                                    if thinking_text:
                                        yield {"type": "thinking_delta", "content": thinking_text}
                                
                                elif delta_type == 'text_delta':
                                    text = getattr(delta, 'text', '')
                                    if text:
                                        text_buffer.append(text)
                                        yield {"type": "text", "content": text}
                                
                                elif delta_type == 'input_json_delta':
                                    # Accumulate tool input JSON
                                    partial = getattr(delta, 'partial_json', '')
                                    if tool_uses_this_round and partial:
                                        # Store partial input for later parsing
                                        if 'partial_input' not in tool_uses_this_round[-1]:
                                            tool_uses_this_round[-1]['partial_input'] = ''
                                        tool_uses_this_round[-1]['partial_input'] += partial
                        
                        elif event_type == 'content_block_stop':
                            if in_thinking:
                                duration = time.time() - thinking_start_time if thinking_start_time else 0
                                yield {"type": "thinking_stop", "duration": round(duration, 1)}
                                in_thinking = False
                    
                    # Get the final message for tool processing
                    final_message = stream.get_final_message()
                
                # Check if we need to execute tools
                actual_tool_uses = [b for b in final_message.content if b.type == 'tool_use']
                
                if not actual_tool_uses:
                    # No tools, we're done (text already streamed)
                    yield {"type": "done"}
                    return
                
                # Process tool uses
                logger.info(f"[CLAUDE] Processing {len(actual_tool_uses)} tool uses")
                assistant_content = []
                
                for block in final_message.content:
                    if block.type == "text":
                        assistant_content.append({"type": "text", "text": block.text})
                    elif block.type == "thinking":
                        assistant_content.append({"type": "thinking", "thinking": block.thinking})
                    elif block.type == "tool_use":
                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input
                        })
                
                conversation.append({"role": "assistant", "content": assistant_content})
                
                # Execute tools
                tool_results = []
                for tool_use in actual_tool_uses:
                    # Special handling for think tool
                    if tool_use.name == "think":
                        thought = tool_use.input.get("thought", "")
                        yield {
                            "type": "thinking_delta",
                            "content": f"\n{thought}\n"
                        }
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": "Thinking recorded."
                        })
                        continue
                    
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
                
                conversation.append({"role": "user", "content": tool_results})
                
            except anthropic.BadRequestError as e:
                # Extended thinking not supported - disable and retry
                if enable_thinking and "thinking" in str(e).lower():
                    logger.warning(f"[CLAUDE] Extended thinking not available: {e}")
                    enable_thinking = False
                    continue
                raise
                
            except Exception as e:
                logger.error(f"Streaming tool loop error: {e}", exc_info=True)
                yield {"type": "error", "message": str(e)}
                return
        
        logger.warning(f"Reached max tool iterations ({max_tool_iterations})")
        yield {"type": "error", "message": "Maximum tool iterations reached"}
                
                # Process tool uses
                logger.info(f"[CLAUDE] Processing tool uses")
                assistant_content = []
                tool_uses = []
                
                for block in response.content:
                    if block.type == "text":
                        if block.text:
                            yield {"type": "text", "content": block.text}
                        assistant_content.append({"type": "text", "text": block.text})
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
