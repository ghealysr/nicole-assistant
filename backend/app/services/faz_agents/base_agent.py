"""
Faz Code Base Agent

Abstract base class for all Faz Code agents with:
- Multi-model support (Claude, Gemini, OpenAI)
- MCP tool execution
- Token/cost tracking
- Structured handoffs
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import logging
import json
import re

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result from agent execution."""
    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    files: Dict[str, str] = field(default_factory=dict)  # path -> content
    next_agent: Optional[str] = None
    error: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_cents: float = 0.0
    duration_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "files": self.files,
            "next_agent": self.next_agent,
            "error": self.error,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_cents": self.cost_cents,
            "duration_ms": self.duration_ms,
        }


# Model pricing per 1K tokens (December 2025)
MODEL_PRICING = {
    "claude-opus-4-5-20251101": {"input": 0.005, "output": 0.025},
    "claude-sonnet-4-5-20250929": {"input": 0.003, "output": 0.015},
    "claude-haiku-4-5-20251001": {"input": 0.00025, "output": 0.00125},
    "gemini-2.5-pro": {"input": 0.00125, "output": 0.01},
    "gpt-5-codex": {"input": 0.00175, "output": 0.014},
}


class BaseAgent(ABC):
    """
    Abstract base class for Faz Code agents.
    
    Each agent must implement:
    - _build_prompt(): Construct the prompt from state
    - _parse_response(): Parse LLM response into structured output
    """
    
    # Agent identity (override in subclasses)
    agent_id: str = "base"
    agent_name: str = "Base Agent"
    agent_role: str = "Unknown"
    model_provider: str = "anthropic"  # anthropic, google, openai
    model_name: str = "claude-sonnet-4-5-20250929"
    
    # Configuration
    temperature: float = 0.7
    max_tokens: int = 4096
    
    # Capabilities
    capabilities: List[str] = []
    available_tools: List[str] = []
    
    # Routing
    valid_handoff_targets: List[str] = []
    receives_handoffs_from: List[str] = []
    
    def __init__(self):
        """Initialize the agent."""
        self._claude_client = None
        self._gemini_client = None
        self._openai_client = None
        self._mcp_client = None
        logger.info(f"[{self.agent_name}] Initialized with {self.model_name}")
    
    async def _get_claude_client(self):
        """Get or create Claude client."""
        if self._claude_client is None:
            from app.integrations.alphawave_claude import claude_client
            self._claude_client = claude_client
        return self._claude_client
    
    async def _get_gemini_client(self):
        """Get or create Gemini client."""
        if self._gemini_client is None:
            from app.integrations.alphawave_gemini import gemini_client
            self._gemini_client = gemini_client
        return self._gemini_client
    
    async def _get_mcp_client(self):
        """Get or create MCP client."""
        if self._mcp_client is None:
            from app.mcp.docker_mcp_client import get_mcp_client
            self._mcp_client = await get_mcp_client()
        return self._mcp_client
    
    async def run(self, state: Dict[str, Any]) -> AgentResult:
        """
        Execute the agent's task.
        
        Args:
            state: Current pipeline state with project info, files, etc.
            
        Returns:
            AgentResult with success/failure, data, and optional next agent
        """
        start_time = datetime.utcnow()
        
        try:
            # Build prompt
            prompt = self._build_prompt(state)
            system_prompt = self._get_system_prompt()
            
            logger.info(f"[{self.agent_name}] Running with {len(prompt)} char prompt")
            
            # Call LLM based on provider
            response, input_tokens, output_tokens = await self._call_llm(
                prompt=prompt,
                system_prompt=system_prompt,
                state=state
            )
            
            # Parse response
            result = self._parse_response(response, state)
            
            # Calculate cost
            pricing = MODEL_PRICING.get(self.model_name, {"input": 0, "output": 0})
            cost_cents = (
                (input_tokens / 1000) * pricing["input"] +
                (output_tokens / 1000) * pricing["output"]
            ) * 100
            
            # Calculate duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            result.input_tokens = input_tokens
            result.output_tokens = output_tokens
            result.cost_cents = cost_cents
            result.duration_ms = duration_ms
            
            logger.info(
                f"[{self.agent_name}] Complete: {result.message[:100]}... "
                f"({input_tokens}+{output_tokens} tokens, ${cost_cents/100:.4f})"
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"[{self.agent_name}] Error: {e}")
            return AgentResult(
                success=False,
                message=f"{self.agent_name} failed",
                error=str(e),
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
    
    async def _call_llm(
        self,
        prompt: str,
        system_prompt: str,
        state: Dict[str, Any]
    ) -> Tuple[str, int, int]:
        """
        Call the appropriate LLM based on model_provider.
        
        Returns:
            Tuple of (response_text, input_tokens, output_tokens)
        """
        messages = [{"role": "user", "content": prompt}]
        
        if self.model_provider == "anthropic":
            client = await self._get_claude_client()
            response = await client.generate_response(
                messages=messages,
                system_prompt=system_prompt,
                model=self.model_name,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            # Estimate tokens (Claude client returns response text only)
            input_tokens = len(prompt) // 4
            output_tokens = len(response) // 4
            return response, input_tokens, output_tokens
            
        elif self.model_provider == "google":
            client = await self._get_gemini_client()
            # Use Gemini for generation
            result = await client.generate_content(
                prompt=f"{system_prompt}\n\n{prompt}",
                model_name=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            input_tokens = len(prompt) // 4
            output_tokens = len(result) // 4
            return result, input_tokens, output_tokens
            
        elif self.model_provider == "openai":
            # Use OpenAI client
            from openai import AsyncOpenAI
            from app.config import settings
            
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )
            result = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens if response.usage else len(prompt) // 4
            output_tokens = response.usage.completion_tokens if response.usage else len(result) // 4
            return result, input_tokens, output_tokens
            
        else:
            raise ValueError(f"Unknown model provider: {self.model_provider}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call an MCP tool.
        
        Args:
            tool_name: Name of the tool (e.g., 'brave_web_search')
            arguments: Tool arguments
            
        Returns:
            Tool result as dict
        """
        if tool_name not in self.available_tools:
            return {"error": f"Tool {tool_name} not available to {self.agent_name}"}
        
        try:
            mcp = await self._get_mcp_client()
            result = await mcp.call_tool(tool_name, arguments)
            
            if result.is_error:
                return {"error": result.error_message}
            
            return {"content": result.content}
            
        except Exception as e:
            logger.error(f"[{self.agent_name}] Tool call failed: {e}")
            return {"error": str(e)}
    
    def create_handoff(
        self,
        to_agent: str,
        completed_work: List[str],
        pending_tasks: List[str],
        artifacts: Dict[str, Any] = None,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Create a structured handoff to another agent.
        
        Args:
            to_agent: Target agent ID
            completed_work: List of completed items
            pending_tasks: List of remaining tasks
            artifacts: Any artifacts to pass along
            notes: Additional notes for the next agent
        """
        if to_agent not in self.valid_handoff_targets:
            logger.warning(f"[{self.agent_name}] Invalid handoff target: {to_agent}")
        
        return {
            "from_agent": self.agent_id,
            "to_agent": to_agent,
            "completed_work": completed_work,
            "pending_tasks": pending_tasks,
            "artifacts": artifacts or {},
            "notes": notes,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    @abstractmethod
    def _build_prompt(self, state: Dict[str, Any]) -> str:
        """
        Build the prompt from current state.
        Must be implemented by each agent.
        """
        pass
    
    @abstractmethod
    def _parse_response(self, response: str, state: Dict[str, Any]) -> AgentResult:
        """
        Parse the LLM response into structured output.
        Must be implemented by each agent.
        """
        pass
    
    def _get_system_prompt(self) -> str:
        """Get the agent's system prompt. Can be overridden."""
        return f"""You are {self.agent_name}, part of the Faz Code AI development team.

Your role: {self.agent_role}
Your capabilities: {', '.join(self.capabilities)}

You work with other agents to create production-quality websites from natural language prompts.
Always produce clean, professional output that can be directly used by the next agent in the pipeline.
"""
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from text, handling markdown code blocks."""
        # Try to find JSON in code blocks first
        patterns = [
            r'```json\n?(.*?)```',
            r'```\n?(.*?)```',
            r'\{[\s\S]*\}',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue
        
        return None
    
    def extract_files(self, text: str) -> Dict[str, str]:
        """
        Extract files from LLM response.
        
        Supports multiple formats:
        - ```file:path/to/file.tsx
        - ```typescript:path/to/file.tsx
        - **path/to/file.tsx** followed by code block
        """
        files = {}
        
        # Pattern 1: ```file:path/to/file
        pattern1 = r'```file:([^\n]+)\n(.*?)```'
        for match in re.finditer(pattern1, text, re.DOTALL):
            path = match.group(1).strip()
            content = match.group(2).strip()
            if content and len(content) > 10:
                files[path] = content
        
        # Pattern 2: ```language:path/to/file (e.g., ```tsx:app/page.tsx)
        pattern2 = r'```(?:tsx?|jsx?|typescript|javascript|css|json):([^\n]+)\n(.*?)```'
        for match in re.finditer(pattern2, text, re.DOTALL):
            path = match.group(1).strip()
            content = match.group(2).strip()
            if content and len(content) > 10 and path not in files:
                files[path] = content
        
        # Pattern 3: **path/to/file.tsx** followed by code block
        pattern3 = r'\*\*([^\*\n]+\.(?:tsx?|jsx?|css|json|html|md))\*\*\s*\n```\w*\n(.*?)```'
        for match in re.finditer(pattern3, text, re.DOTALL):
            path = match.group(1).strip()
            content = match.group(2).strip()
            if content and len(content) > 10 and path not in files:
                files[path] = content
        
        # Pattern 4: // filepath: path/to/file at start of code block
        pattern4 = r'```\w*\n//\s*(?:filepath:)?\s*([^\n]+\.(?:tsx?|jsx?|css|json))\n(.*?)```'
        for match in re.finditer(pattern4, text, re.DOTALL):
            path = match.group(1).strip()
            content = match.group(2).strip()
            if content and len(content) > 10 and path not in files:
                files[path] = content
        
        return files

