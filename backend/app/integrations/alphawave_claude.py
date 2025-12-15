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
        self.sonnet_model = "claude-sonnet-4-5-20250929"
        self.haiku_model = "claude-haiku-4-5-20251001"
        logger.info(f"Claude client initialized with Sonnet: {self.sonnet_model}, Haiku: {self.haiku_model}")
    
    async def generate_response(
        self,
        messages: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        tools: Optional[List[Dict[str, Any]]] = None,
        enable_extended_thinking: bool = False,
        thinking_budget: int = 8000,
    ) -> str:
        """
        Generate response from Claude (non-streaming, async).
        
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

            # Try with extended thinking if enabled
            use_thinking = enable_extended_thinking
            if use_thinking:
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": min(thinking_budget, max_tokens - 1) if max_tokens else thinking_budget
                }
                # Extended thinking requires temperature to not be set
                del kwargs["temperature"]
            
            logger.debug(f"[Claude] Calling {model} with {len(messages)} messages, thinking={use_thinking}")
            
            try:
                # Use async client for true async operation
                response = await self.async_client.messages.create(**kwargs)
            except TypeError as e:
                # Fallback if 'thinking' parameter not supported by library version
                if "thinking" in str(e) and use_thinking:
                    logger.warning("[Claude] Extended thinking not supported by library, falling back to standard mode")
                    kwargs.pop("thinking", None)
                    kwargs["temperature"] = temperature
                    response = await self.async_client.messages.create(**kwargs)
                else:
                    raise
            
            # Extract text from response
            if response.content and len(response.content) > 0:
                # Handle tool_use responses
                text_parts = []
                for block in response.content:
                    if hasattr(block, 'text'):
                        text_parts.append(block.text)
                result = "".join(text_parts)
                logger.debug(f"[Claude] Response: {len(result)} chars")
                return result
            
            logger.warning("[Claude] Empty response from API")
            return ""
            
        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e.status_code} - {e.message}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Claude unexpected error: {e}", exc_info=True)
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
        enable_extended_thinking: bool = False,
        thinking_budget: int = 8000,
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
        
        # Track if we should try extended thinking
        use_thinking = enable_extended_thinking
        
        while iterations < max_tool_iterations:
            iterations += 1
            
            try:
                # Build kwargs dynamically to handle thinking fallback
                create_kwargs = {
                    "model": model,
                    "max_tokens": max_tokens,
                    "system": system_prompt if system_prompt else "",
                    "messages": conversation,
                    "tools": tools,
                }
                
                if use_thinking:
                    create_kwargs["thinking"] = {
                        "type": "enabled", 
                        "budget_tokens": min(thinking_budget, max_tokens - 1) if max_tokens else thinking_budget
                    }
                    # Extended thinking is incompatible with temperature
                else:
                    create_kwargs["temperature"] = temperature
                
                try:
                    # Use async client for proper async operation
                    response = await self.async_client.messages.create(**create_kwargs)
                except TypeError as e:
                    # Fallback if 'thinking' parameter not supported
                    if "thinking" in str(e) and use_thinking:
                        logger.warning("[Claude] Extended thinking not supported, falling back")
                        use_thinking = False
                        create_kwargs.pop("thinking", None)
                        create_kwargs["temperature"] = temperature
                        response = await self.async_client.messages.create(**create_kwargs)
                    else:
                        raise
                
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
        
        # Max iterations reached - make final call WITHOUT tools to get proper response
        logger.warning(f"Reached max tool iterations ({max_tool_iterations}), making final call without tools")
        try:
            # Build a clean conversation without tool_use/tool_result blocks
            # Extract just the text content for a clean final call
            clean_messages = []
            for msg in messages:  # Use original messages, not the tool-augmented conversation
                clean_messages.append(msg)
            
            # Summarize tool results for context
            tool_context_parts = []
            for tc in tool_calls_made:
                if not tc.get("is_error"):
                    result_preview = str(tc.get("result", ""))[:500]
                    tool_context_parts.append(f"- {tc['name']}: {result_preview}")
            
            if tool_context_parts:
                tool_context = "Based on my research:\n" + "\n".join(tool_context_parts[:5])  # Max 5 tools
                clean_messages.append({
                    "role": "user", 
                    "content": f"{tool_context}\n\nNow please provide your response incorporating this information."
                })
            
            # Make final call without tools
            final_response = await self.async_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=clean_messages
            )
            
            if final_response.content:
                text_parts = []
                for block in final_response.content:
                    if hasattr(block, 'text'):
                        text_parts.append(block.text)
                final_text = "".join(text_parts)
                if final_text.strip():
                    return final_text, tool_calls_made
                    
        except Exception as e:
            logger.error(f"Final response generation failed: {e}", exc_info=True)
        
        # Last resort: return a summary of what was found
        if tool_calls_made:
            successful_tools = [tc for tc in tool_calls_made if not tc.get("is_error")]
            if successful_tools:
                summary = f"I found {len(successful_tools)} pieces of information while researching. "
                summary += "Let me share what I discovered:\n\n"
                for tc in successful_tools[:3]:
                    result = tc.get("result", {})
                    if isinstance(result, dict):
                        summary += f"• {result.get('message', result.get('result', str(result)[:200]))}\n"
                return summary, tool_calls_made
        
        return "I gathered some research but encountered an issue formatting my response. Could you ask me again?", tool_calls_made
    
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
        
        Based on Anthropic docs: https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking
        
        Yields events:
        - {"type": "thinking_start"}
        - {"type": "thinking_delta", "content": "..."}
        - {"type": "thinking_stop", "duration": 3.2}
        - {"type": "text_delta", "content": "..."}
        - {"type": "done"}
        """
        import time
        
        if model is None:
            model = self.sonnet_model
        
        thinking_start_time = None
        in_thinking = False
        thinking_started = False
        response_started = False
        
        try:
            logger.info(f"[CLAUDE] Starting extended thinking stream with budget: {thinking_budget}")
            
            # Build request with extended thinking enabled
            # Note: temperature is NOT compatible with thinking
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": thinking_budget
                },
                "messages": messages,
            }
            
            if system_prompt:
                kwargs["system"] = system_prompt
            
            # Stream with raw events to capture thinking blocks
            # Following the exact pattern from Anthropic docs
            with self.client.messages.stream(**kwargs) as stream:
                for event in stream:
                    # Access event.type directly as per Anthropic SDK
                    if event.type == "content_block_start":
                        block_type = getattr(event.content_block, 'type', None)
                        logger.debug(f"[CLAUDE] Block start: {block_type}")
                        
                        if block_type == "thinking":
                            in_thinking = True
                            thinking_start_time = time.time()
                            if not thinking_started:
                                yield {"type": "thinking_start"}
                                thinking_started = True
                        elif block_type == "text":
                            if in_thinking:
                                duration = time.time() - thinking_start_time if thinking_start_time else 0
                                yield {"type": "thinking_stop", "duration": round(duration, 1)}
                                in_thinking = False
                    
                    elif event.type == "content_block_delta":
                        delta = event.delta
                        delta_type = getattr(delta, 'type', None)
                        
                        if delta_type == "thinking_delta":
                            # Thinking content is in delta.thinking (not delta.text)
                            thinking_text = getattr(delta, 'thinking', '')
                            if thinking_text:
                                yield {"type": "thinking_delta", "content": thinking_text}
                        
                        elif delta_type == "text_delta":
                            text = getattr(delta, 'text', '')
                            if text:
                                if not response_started:
                                    response_started = True
                                yield {"type": "text_delta", "content": text}
                    
                    elif event.type == "content_block_stop":
                        if in_thinking:
                            duration = time.time() - thinking_start_time if thinking_start_time else 0
                            yield {"type": "thinking_stop", "duration": round(duration, 1)}
                            in_thinking = False
            
            yield {"type": "done"}
            logger.info("[CLAUDE] Extended thinking stream complete")
            
        except anthropic.BadRequestError as e:
            error_msg = str(e)
            logger.warning(f"[CLAUDE] Extended thinking not available: {error_msg}. Falling back to standard.")
            
            # Fall back to standard streaming without thinking
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
                
                # Add extended thinking if enabled (first iteration only)
                # Note: temperature is NOT compatible with thinking
                if enable_thinking and iterations == 1:
                    kwargs["thinking"] = {
                        "type": "enabled",
                        "budget_tokens": thinking_budget
                    }
                elif not enable_thinking:
                    # Only set temperature when thinking is disabled
                    kwargs["temperature"] = temperature
                
                logger.info(f"[CLAUDE] Iteration {iterations} - calling Claude API")
                
                # Stream to capture thinking + tool decisions
                thinking_start_time = None
                in_thinking = False
                tool_uses_this_round = []
                text_buffer = []
                
                with self.client.messages.stream(**kwargs) as stream:
                    for event in stream:
                        # Use direct attribute access per Anthropic SDK patterns
                        if event.type == 'content_block_start':
                            block = event.content_block
                            block_type = getattr(block, 'type', None)
                            
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
                        
                        elif event.type == 'content_block_delta':
                            delta = event.delta
                            delta_type = getattr(delta, 'type', None)
                            
                            if delta_type == 'thinking_delta':
                                # Thinking content is in delta.thinking
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
                                    if 'partial_input' not in tool_uses_this_round[-1]:
                                        tool_uses_this_round[-1]['partial_input'] = ''
                                    tool_uses_this_round[-1]['partial_input'] += partial
                        
                        elif event.type == 'content_block_stop':
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
