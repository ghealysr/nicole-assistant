"""
Nicole V7 - Workflow Scheduler

Registers workflow handlers and schedules workflow executions.

This module:
1. Registers tool and agent handlers with the workflow engine
2. Loads YAML workflow definitions at startup
3. Schedules workflows using APScheduler
4. Provides API for manual workflow execution

Author: Nicole V7 Architecture
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.services.workflow_engine import WorkflowRegistry, WorkflowExecutor, WorkflowDefinition, WorkflowState, workflow_engine
from app.services.alphawave_memory_service import memory_service
from app.services.alphawave_document_service import document_service
from app.integrations.alphawave_claude import claude_client
from app.workflows import AVAILABLE_WORKFLOWS, list_workflows

logger = logging.getLogger(__name__)


class WorkflowScheduler:
    """
    Manages workflow scheduling and execution.
    
    Responsibilities:
    1. Register tool handlers with workflow engine
    2. Register agent handlers with workflow engine
    3. Load workflow definitions
    4. Schedule workflows based on cron expressions
    5. Provide manual execution API
    """
    
    def __init__(self):
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._initialized = False
        logger.info("[WORKFLOW SCHEDULER] Initializing...")
    
    async def initialize(self):
        """
        Initialize the workflow scheduler.
        
        Call this at application startup.
        """
        if self._initialized:
            logger.info("[WORKFLOW SCHEDULER] Already initialized")
            return
        
        logger.info("[WORKFLOW SCHEDULER] Starting initialization...")
        
        # Step 1: Register tool handlers
        self._register_tool_handlers()
        
        # Step 2: Register agent handlers
        self._register_agent_handlers()
        
        # Step 3: Load workflow definitions
        await self._load_workflows()
        
        # Step 4: Initialize scheduler
        self._scheduler = AsyncIOScheduler()
        
        # Step 5: Schedule workflows (disabled by default - enable when APIs are ready)
        # await self._schedule_workflows()
        
        # Step 6: Start scheduler
        self._scheduler.start()
        
        self._initialized = True
        logger.info("[WORKFLOW SCHEDULER] Initialization complete")
    
    def _register_tool_handlers(self):
        """Register tool handlers with the workflow engine."""
        
        # Memory Search
        async def memory_search_handler(**params) -> Dict[str, Any]:
            query = params.get("query", "")
            limit = params.get("limit", 5)
            memory_type = params.get("memory_type")
            
            # Note: user_id needs to be passed in context
            user_id = params.get("_user_id", 1)  # Default for system workflows
            
            memories = await memory_service.search_memory(
                user_id=user_id,
                query=query,
                limit=limit,
                min_confidence=0.3
            )
            
            if memory_type and memories:
                memories = [m for m in memories if m.get("memory_type") == memory_type]
            
            return {
                "count": len(memories) if memories else 0,
                "memories": memories or []
            }
        
        workflow_engine.register_tool_handler("memory_search", memory_search_handler)
        
        # Memory Store
        async def memory_store_handler(**params) -> Dict[str, Any]:
            content = params.get("content", "")
            memory_type = params.get("memory_type", "fact")
            importance = params.get("importance", "medium")
            tags = params.get("tags", [])
            
            user_id = params.get("_user_id", 1)
            
            result = await memory_service.save_memory(
                user_id=user_id,
                memory_type=memory_type,
                content=content,
                importance=importance,
                source="workflow"
            )
            
            return {
                "status": "stored" if result else "duplicate",
                "memory_id": result.get("memory_id") if result else None
            }
        
        workflow_engine.register_tool_handler("memory_store", memory_store_handler)
        workflow_engine.register_tool_handler("memory_store_batch", memory_store_handler)  # Alias
        
        # Document Search
        async def document_search_handler(**params) -> Dict[str, Any]:
            query = params.get("query", "")
            limit = params.get("limit", 3)
            user_id = params.get("_user_id", 1)
            
            results = await document_service.search_documents(
                user_id=user_id,
                query=query,
                limit=limit
            )
            
            return {
                "count": len(results) if results else 0,
                "documents": results or []
            }
        
        workflow_engine.register_tool_handler("document_search", document_search_handler)
        
        # Placeholder handlers for external APIs (to be implemented)
        async def placeholder_handler(**params) -> Dict[str, Any]:
            tool_name = params.get("_tool_name", "unknown")
            return {
                "status": "not_implemented",
                "message": f"Tool {tool_name} is not yet connected. Returning placeholder data.",
                "data": None
            }
        
        # ESPN API placeholders
        workflow_engine.register_tool_handler("espn_nfl_api", placeholder_handler)
        workflow_engine.register_tool_handler("espn_nba_api", placeholder_handler)
        workflow_engine.register_tool_handler("espn_ncaaf_api", placeholder_handler)
        workflow_engine.register_tool_handler("espn_ncaab_api", placeholder_handler)
        workflow_engine.register_tool_handler("espn_injuries", placeholder_handler)
        
        # Calendar placeholders
        workflow_engine.register_tool_handler("google_calendar_today", placeholder_handler)
        
        # Weather placeholder
        workflow_engine.register_tool_handler("weather_api", placeholder_handler)
        
        # Memory maintenance placeholders
        workflow_engine.register_tool_handler("memory_find_duplicates", placeholder_handler)
        workflow_engine.register_tool_handler("memory_merge_duplicates", placeholder_handler)
        workflow_engine.register_tool_handler("memory_apply_decay", placeholder_handler)
        workflow_engine.register_tool_handler("memory_relationship_maintenance", placeholder_handler)
        workflow_engine.register_tool_handler("memory_pattern_detection", placeholder_handler)
        workflow_engine.register_tool_handler("memory_archive", placeholder_handler)
        
        logger.info("[WORKFLOW SCHEDULER] Tool handlers registered")
    
    def _register_agent_handlers(self):
        """Register agent handlers with the workflow engine."""
        
        # Nicole Core Agent
        async def nicole_core_handler(prompt: str, context: Dict[str, Any]) -> str:
            """Execute Nicole core agent for workflow steps."""
            messages = [{"role": "user", "content": prompt}]
            
            system_prompt = """You are Nicole, an AI assistant helping with automated workflows.
            
Your task is to analyze the provided data and generate the requested output.
Be concise, accurate, and actionable. Format your response appropriately for the request."""
            
            response = await claude_client.generate_response(
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=2048,
                temperature=0.7
            )
            
            return response
        
        workflow_engine.register_agent_handler("nicole_core", nicole_core_handler)
        
        logger.info("[WORKFLOW SCHEDULER] Agent handlers registered")
    
    async def _load_workflows(self):
        """Load all workflow definitions from YAML files."""
        for name, path in AVAILABLE_WORKFLOWS.items():
            try:
                workflow_engine.load_workflow_file(str(path))
                logger.info(f"[WORKFLOW SCHEDULER] Loaded workflow: {name}")
            except Exception as e:
                logger.error(f"[WORKFLOW SCHEDULER] Failed to load workflow {name}: {e}")
    
    async def _schedule_workflows(self):
        """Schedule workflows based on their cron expressions."""
        for workflow_name, workflow_def in workflow_engine._workflows.items():
            schedule = workflow_def.get("schedule")
            if schedule:
                try:
                    trigger = CronTrigger.from_crontab(schedule)
                    self._scheduler.add_job(
                        self._execute_scheduled_workflow,
                        trigger,
                        args=[workflow_name],
                        id=f"workflow_{workflow_name}",
                        replace_existing=True
                    )
                    logger.info(f"[WORKFLOW SCHEDULER] Scheduled {workflow_name} with cron: {schedule}")
                except Exception as e:
                    logger.error(f"[WORKFLOW SCHEDULER] Failed to schedule {workflow_name}: {e}")
    
    async def _execute_scheduled_workflow(self, workflow_name: str):
        """Execute a scheduled workflow."""
        logger.info(f"[WORKFLOW SCHEDULER] Executing scheduled workflow: {workflow_name}")
        
        try:
            execution = await workflow_engine.execute(
                workflow_name=workflow_name,
                user_id=1,  # System user for scheduled workflows
                context={
                    "now": {
                        "date": datetime.utcnow().strftime("%Y-%m-%d"),
                        "time": datetime.utcnow().strftime("%H:%M:%S"),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    "user": {
                        "name": "Glen",
                        "location": "Default"
                    }
                }
            )
            
            if execution.status == "completed":
                logger.info(f"[WORKFLOW SCHEDULER] Workflow {workflow_name} completed successfully")
            else:
                logger.error(f"[WORKFLOW SCHEDULER] Workflow {workflow_name} failed: {execution.status}")
                
        except Exception as e:
            logger.error(f"[WORKFLOW SCHEDULER] Error executing {workflow_name}: {e}", exc_info=True)
    
    async def execute_workflow(
        self,
        workflow_name: str,
        user_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> WorkflowState:
        """
        Manually execute a workflow.
        
        Args:
            workflow_name: Name of the workflow to execute
            user_id: User ID for context
            context: Additional context variables
            
        Returns:
            WorkflowState result
        """
        if not self._initialized:
            await self.initialize()
        
        # Build context
        full_context = {
            "now": {
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "time": datetime.utcnow().strftime("%H:%M:%S"),
                "timestamp": datetime.utcnow().isoformat()
            },
            "_user_id": user_id  # Pass user_id to tool handlers
        }
        
        if context:
            full_context.update(context)
        
        return await workflow_engine.execute(
            workflow_name=workflow_name,
            user_id=user_id,
            context=full_context
        )
    
    def list_workflows(self) -> Dict[str, Any]:
        """List all available workflows with their status."""
        workflows = {}
        
        for name in list_workflows():
            workflow_def = workflow_engine._workflows.get(name) or {}
            
            # Check if scheduled
            scheduled = False
            next_run = None
            if self._scheduler:
                job = self._scheduler.get_job(f"workflow_{name}")
                if job:
                    scheduled = True
                    next_run = job.next_run_time.isoformat() if job.next_run_time else None
            
            workflows[name] = {
                "name": name,
                "description": workflow_def.get("description", ""),
                "version": workflow_def.get("version", "1.0.0"),
                "schedule": workflow_def.get("schedule"),
                "steps_count": len(workflow_def.get("steps", [])),
                "scheduled": scheduled,
                "next_run": next_run
            }
        
        return workflows
    
    async def shutdown(self):
        """Shutdown the scheduler."""
        if self._scheduler:
            self._scheduler.shutdown()
            logger.info("[WORKFLOW SCHEDULER] Scheduler shutdown complete")


# Global scheduler instance
workflow_scheduler = WorkflowScheduler()

