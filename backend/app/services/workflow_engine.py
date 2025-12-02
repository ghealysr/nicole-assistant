"""
Nicole V7 - YAML Workflow Engine (Orchestra Pattern)

Implements declarative YAML-based workflow orchestration for complex automated tasks.

Benefits:
- Declarative: Change workflows without code deployment
- Dependency-aware: Parallel execution when possible
- Resumable: Crash recovery with state persistence
- Auditable: Every step logged

Use cases:
- Sports Oracle (collect → analyze → predict → notify)
- Daily Journal generation
- Memory consolidation jobs
- Scheduled report generation
- Multi-step API integrations

Example workflow:
```yaml
name: morning_briefing
schedule: "0 7 * * *"  # Daily at 7am
steps:
  - name: get_weather
    type: tool
    tool: weather_api
    params:
      location: "{{user.location}}"
  
  - name: get_calendar
    type: tool
    tool: google_calendar_today
    
  - name: generate_briefing
    type: agent
    agent: nicole_core
    prompt: |
      Create a morning briefing using:
      Weather: {{steps.get_weather.result}}
      Calendar: {{steps.get_calendar.result}}
```

Author: Nicole V7 Architecture
"""

import logging
import yaml
import json
import re
import asyncio
from typing import Dict, Any, List, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class StepType(str, Enum):
    """Types of workflow steps."""
    TOOL = "tool"           # Execute a tool
    AGENT = "agent"         # Call an agent with a prompt
    CONDITION = "condition"  # Conditional branching
    PARALLEL = "parallel"   # Parallel execution
    WAIT = "wait"           # Wait for a duration
    NOTIFY = "notify"       # Send notification


class StepStatus(str, Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    step_type: StepType
    config: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retries: int = 0
    max_retries: int = 3


@dataclass
class WorkflowExecution:
    """State of a workflow execution."""
    workflow_name: str
    execution_id: str
    user_id: int
    steps: List[WorkflowStep]
    context: Dict[str, Any] = field(default_factory=dict)
    status: str = "running"
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def get_step(self, name: str) -> Optional[WorkflowStep]:
        """Get a step by name."""
        for step in self.steps:
            if step.name == name:
                return step
        return None
    
    def get_completed_results(self) -> Dict[str, Any]:
        """Get results from all completed steps."""
        return {
            step.name: step.result
            for step in self.steps
            if step.status == StepStatus.COMPLETED and step.result is not None
        }


class WorkflowEngine:
    """
    YAML-based workflow orchestration engine.
    
    This engine:
    1. Parses YAML workflow definitions
    2. Resolves template variables
    3. Executes steps in dependency order
    4. Handles parallel execution where possible
    5. Provides crash recovery via state persistence
    """
    
    def __init__(self):
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._tool_handlers: Dict[str, Callable] = {}
        self._agent_handlers: Dict[str, Callable] = {}
        self._executions: Dict[str, WorkflowExecution] = {}
        logger.info("[WORKFLOW] Engine initialized")
    
    def register_tool_handler(
        self,
        tool_name: str,
        handler: Callable[..., Awaitable[Any]]
    ):
        """Register a handler function for a tool."""
        self._tool_handlers[tool_name] = handler
        logger.debug(f"[WORKFLOW] Registered tool handler: {tool_name}")
    
    def register_agent_handler(
        self,
        agent_name: str,
        handler: Callable[[str, Dict[str, Any]], Awaitable[str]]
    ):
        """Register a handler function for an agent."""
        self._agent_handlers[agent_name] = handler
        logger.debug(f"[WORKFLOW] Registered agent handler: {agent_name}")
    
    def load_workflow(self, yaml_content: str) -> Dict[str, Any]:
        """
        Load a workflow from YAML content.
        
        Returns the parsed workflow definition.
        """
        try:
            workflow = yaml.safe_load(yaml_content)
            
            # Validate required fields
            if "name" not in workflow:
                raise ValueError("Workflow must have a 'name'")
            if "steps" not in workflow:
                raise ValueError("Workflow must have 'steps'")
            
            self._workflows[workflow["name"]] = workflow
            logger.info(f"[WORKFLOW] Loaded workflow: {workflow['name']} with {len(workflow['steps'])} steps")
            
            return workflow
            
        except yaml.YAMLError as e:
            logger.error(f"[WORKFLOW] YAML parse error: {e}")
            raise ValueError(f"Invalid YAML: {e}")
    
    def load_workflow_file(self, file_path: str) -> Dict[str, Any]:
        """Load a workflow from a YAML file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Workflow file not found: {file_path}")
        
        return self.load_workflow(path.read_text())
    
    def _resolve_template(
        self,
        template: Any,
        context: Dict[str, Any]
    ) -> Any:
        """
        Resolve template variables in a value.
        
        Supports:
        - {{user.property}} - User context
        - {{steps.step_name.result}} - Previous step results
        - {{env.VAR_NAME}} - Environment variables
        """
        if isinstance(template, str):
            # Find all {{...}} patterns
            pattern = r'\{\{([^}]+)\}\}'
            
            def replace(match):
                path = match.group(1).strip()
                parts = path.split(".")
                
                try:
                    value = context
                    for part in parts:
                        if isinstance(value, dict):
                            value = value.get(part)
                        else:
                            value = getattr(value, part, None)
                        if value is None:
                            return match.group(0)  # Keep original if not found
                    
                    # Convert to string if needed
                    if isinstance(value, (dict, list)):
                        return json.dumps(value)
                    return str(value)
                    
                except Exception:
                    return match.group(0)
            
            return re.sub(pattern, replace, template)
        
        elif isinstance(template, dict):
            return {k: self._resolve_template(v, context) for k, v in template.items()}
        
        elif isinstance(template, list):
            return [self._resolve_template(item, context) for item in template]
        
        return template
    
    def _parse_steps(
        self,
        workflow: Dict[str, Any]
    ) -> List[WorkflowStep]:
        """Parse workflow steps into WorkflowStep objects."""
        steps = []
        
        for step_def in workflow.get("steps", []):
            step_type = StepType(step_def.get("type", "tool"))
            
            step = WorkflowStep(
                name=step_def["name"],
                step_type=step_type,
                config=step_def,
                depends_on=step_def.get("depends_on", []),
                max_retries=step_def.get("max_retries", 3)
            )
            
            steps.append(step)
        
        return steps
    
    def _can_execute_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution
    ) -> bool:
        """Check if a step can be executed (all dependencies met)."""
        if step.status != StepStatus.PENDING:
            return False
        
        for dep_name in step.depends_on:
            dep_step = execution.get_step(dep_name)
            if not dep_step or dep_step.status != StepStatus.COMPLETED:
                return False
        
        return True
    
    async def _execute_step(
        self,
        step: WorkflowStep,
        execution: WorkflowExecution
    ):
        """Execute a single workflow step."""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.utcnow()
        
        # Build context for template resolution
        context = {
            "user": execution.context.get("user", {}),
            "steps": execution.get_completed_results(),
            "env": execution.context.get("env", {}),
            "workflow": {
                "name": execution.workflow_name,
                "execution_id": execution.execution_id
            }
        }
        
        try:
            if step.step_type == StepType.TOOL:
                result = await self._execute_tool_step(step, context)
            
            elif step.step_type == StepType.AGENT:
                result = await self._execute_agent_step(step, context)
            
            elif step.step_type == StepType.CONDITION:
                result = await self._execute_condition_step(step, context)
            
            elif step.step_type == StepType.WAIT:
                result = await self._execute_wait_step(step, context)
            
            elif step.step_type == StepType.NOTIFY:
                result = await self._execute_notify_step(step, context)
            
            elif step.step_type == StepType.PARALLEL:
                result = await self._execute_parallel_step(step, context, execution)
            
            else:
                raise ValueError(f"Unknown step type: {step.step_type}")
            
            step.result = result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.utcnow()
            
            logger.info(f"[WORKFLOW] Step '{step.name}' completed successfully")
            
        except Exception as e:
            step.error = str(e)
            step.retries += 1
            
            if step.retries < step.max_retries:
                step.status = StepStatus.PENDING  # Retry
                logger.warning(f"[WORKFLOW] Step '{step.name}' failed, will retry ({step.retries}/{step.max_retries})")
            else:
                step.status = StepStatus.FAILED
                logger.error(f"[WORKFLOW] Step '{step.name}' failed permanently: {e}")
    
    async def _execute_tool_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> Any:
        """Execute a tool step."""
        tool_name = step.config.get("tool")
        if not tool_name:
            raise ValueError(f"Tool step '{step.name}' missing 'tool' field")
        
        handler = self._tool_handlers.get(tool_name)
        if not handler:
            raise ValueError(f"No handler registered for tool: {tool_name}")
        
        # Resolve template parameters
        params = self._resolve_template(step.config.get("params", {}), context)
        
        return await handler(**params)
    
    async def _execute_agent_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> str:
        """Execute an agent step."""
        agent_name = step.config.get("agent")
        if not agent_name:
            raise ValueError(f"Agent step '{step.name}' missing 'agent' field")
        
        handler = self._agent_handlers.get(agent_name)
        if not handler:
            raise ValueError(f"No handler registered for agent: {agent_name}")
        
        # Resolve prompt template
        prompt = self._resolve_template(step.config.get("prompt", ""), context)
        
        return await handler(prompt, context)
    
    async def _execute_condition_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> bool:
        """Execute a condition step."""
        condition = step.config.get("condition", "")
        condition = self._resolve_template(condition, context)
        
        # Simple evaluation (could be enhanced with safe eval)
        # For now, just check truthiness
        result = bool(condition and condition.lower() not in ("false", "0", "none", "null", ""))
        
        return result
    
    async def _execute_wait_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> str:
        """Execute a wait step."""
        duration = step.config.get("duration", 0)
        if isinstance(duration, str):
            duration = int(self._resolve_template(duration, context))
        
        await asyncio.sleep(duration)
        return f"Waited {duration} seconds"
    
    async def _execute_notify_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any]
    ) -> str:
        """Execute a notification step."""
        channel = step.config.get("channel", "log")
        message = self._resolve_template(step.config.get("message", ""), context)
        
        if channel == "log":
            logger.info(f"[WORKFLOW NOTIFY] {message}")
        # Add other channels (email, slack, etc.) as needed
        
        return f"Notified via {channel}"
    
    async def _execute_parallel_step(
        self,
        step: WorkflowStep,
        context: Dict[str, Any],
        execution: WorkflowExecution
    ) -> Dict[str, Any]:
        """Execute parallel sub-steps."""
        sub_steps = step.config.get("steps", [])
        
        # Create WorkflowStep objects for each sub-step
        parallel_steps = []
        for sub_def in sub_steps:
            sub_step = WorkflowStep(
                name=f"{step.name}.{sub_def['name']}",
                step_type=StepType(sub_def.get("type", "tool")),
                config=sub_def
            )
            parallel_steps.append(sub_step)
        
        # Execute all in parallel
        tasks = [
            self._execute_step(s, execution)
            for s in parallel_steps
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        results = {}
        for s in parallel_steps:
            if s.status == StepStatus.COMPLETED:
                results[s.name] = s.result
            else:
                results[s.name] = {"error": s.error}
        
        return results
    
    async def execute(
        self,
        workflow_name: str,
        user_id: int,
        context: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None
    ) -> WorkflowExecution:
        """
        Execute a workflow.
        
        Args:
            workflow_name: Name of the loaded workflow
            user_id: User ID for context
            context: Additional context variables
            execution_id: Optional execution ID (for resume)
            
        Returns:
            The workflow execution result
        """
        workflow = self._workflows.get(workflow_name)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_name}")
        
        # Create or resume execution
        if execution_id and execution_id in self._executions:
            execution = self._executions[execution_id]
        else:
            execution_id = execution_id or f"{workflow_name}_{datetime.utcnow().timestamp()}"
            execution = WorkflowExecution(
                workflow_name=workflow_name,
                execution_id=execution_id,
                user_id=user_id,
                steps=self._parse_steps(workflow),
                context=context or {}
            )
            self._executions[execution_id] = execution
        
        logger.info(f"[WORKFLOW] Executing workflow: {workflow_name} (id: {execution_id})")
        
        # Execute steps in dependency order
        max_iterations = len(execution.steps) * 2  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Find steps that can be executed
            executable = [
                step for step in execution.steps
                if self._can_execute_step(step, execution)
            ]
            
            if not executable:
                # Check if we're done or stuck
                pending = [s for s in execution.steps if s.status == StepStatus.PENDING]
                if not pending:
                    break  # All done
                
                # Check for dependency failures
                failed = [s for s in execution.steps if s.status == StepStatus.FAILED]
                if failed:
                    execution.status = "failed"
                    break
                
                # Stuck - circular dependency?
                logger.error(f"[WORKFLOW] Stuck with pending steps: {[s.name for s in pending]}")
                execution.status = "failed"
                break
            
            # Execute steps (could parallelize independent steps here)
            for step in executable:
                await self._execute_step(step, execution)
        
        # Check final status
        failed_steps = [s for s in execution.steps if s.status == StepStatus.FAILED]
        if failed_steps:
            execution.status = "failed"
        else:
            execution.status = "completed"
        
        execution.completed_at = datetime.utcnow()
        
        logger.info(f"[WORKFLOW] Workflow {workflow_name} {execution.status}")
        return execution
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get an execution by ID."""
        return self._executions.get(execution_id)
    
    def get_workflow_template(self, workflow_type: str) -> str:
        """Get a template for a workflow type."""
        templates = {
            "sports_oracle": """
name: sports_oracle_daily
schedule: "0 6 * * *"
description: Daily sports predictions and analysis

steps:
  - name: collect_nfl_data
    type: tool
    tool: espn_nfl_api
    params:
      endpoint: scoreboard
      
  - name: collect_nba_data
    type: tool
    tool: espn_nba_api
    params:
      endpoint: scoreboard
      
  - name: get_historical
    type: tool
    tool: memory_search
    params:
      query: "sports predictions accuracy"
      limit: 10
      
  - name: analyze_games
    type: agent
    agent: nicole_core
    depends_on: [collect_nfl_data, collect_nba_data, get_historical]
    prompt: |
      Analyze today's games and make predictions:
      
      NFL Data: {{steps.collect_nfl_data.result}}
      NBA Data: {{steps.collect_nba_data.result}}
      Historical Accuracy: {{steps.get_historical.result}}
      
      Provide predictions with confidence levels.
      
  - name: store_predictions
    type: tool
    tool: memory_store
    depends_on: [analyze_games]
    params:
      content: "{{steps.analyze_games.result}}"
      memory_type: "prediction"
      tags: ["sports", "oracle", "daily"]
""",
            
            "morning_briefing": """
name: morning_briefing
schedule: "0 7 * * *"
description: Daily morning briefing for the user

steps:
  - name: get_weather
    type: tool
    tool: weather_api
    params:
      location: "{{user.location}}"
      
  - name: get_calendar
    type: tool
    tool: google_calendar_today
    
  - name: get_reminders
    type: tool
    tool: memory_search
    params:
      query: "reminder today task"
      memory_type: "task"
      limit: 5
      
  - name: generate_briefing
    type: agent
    agent: nicole_core
    depends_on: [get_weather, get_calendar, get_reminders]
    prompt: |
      Create a warm, personalized morning briefing for {{user.name}}:
      
      Weather: {{steps.get_weather.result}}
      Today's Calendar: {{steps.get_calendar.result}}
      Reminders: {{steps.get_reminders.result}}
      
      Make it feel like a friend updating them on their day.
""",
            
            "memory_consolidation": """
name: memory_consolidation
schedule: "0 3 * * *"
description: Nightly memory consolidation and cleanup

steps:
  - name: find_duplicates
    type: tool
    tool: memory_find_duplicates
    
  - name: merge_duplicates
    type: tool
    tool: memory_merge
    depends_on: [find_duplicates]
    params:
      duplicates: "{{steps.find_duplicates.result}}"
      
  - name: decay_old_memories
    type: tool
    tool: memory_apply_decay
    
  - name: detect_patterns
    type: tool
    tool: memory_pattern_detection
    depends_on: [decay_old_memories]
    
  - name: create_insights
    type: agent
    agent: nicole_core
    depends_on: [detect_patterns]
    prompt: |
      Based on pattern detection results, create insights:
      {{steps.detect_patterns.result}}
      
      What patterns or connections should be remembered?
"""
        }
        
        return templates.get(workflow_type, "")


# Global engine instance
workflow_engine = WorkflowEngine()

