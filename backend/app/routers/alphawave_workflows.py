"""
Workflows Router - Nicole V7

API endpoints for managing and executing workflows.

Endpoints:
- GET /workflows - List all available workflows
- POST /workflows/{name}/execute - Execute a workflow manually
- GET /workflows/{name}/status/{execution_id} - Get execution status

Author: Nicole V7 Architecture
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging

from app.middleware.alphawave_auth import get_current_tiger_user_id
from app.services.workflow_scheduler import workflow_scheduler
from app.services.workflow_engine import WorkflowRegistry, WorkflowExecutor, workflow_engine

logger = logging.getLogger(__name__)

router = APIRouter()


class WorkflowExecuteRequest(BaseModel):
    """Request to execute a workflow."""
    context: Optional[Dict[str, Any]] = None


class WorkflowListResponse(BaseModel):
    """Response listing available workflows."""
    workflows: Dict[str, Any]


class WorkflowExecutionResponse(BaseModel):
    """Response from workflow execution."""
    execution_id: str
    workflow_name: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    steps_completed: int
    steps_total: int
    results: Optional[Dict[str, Any]] = None


@router.get("")
async def list_workflows(request: Request) -> WorkflowListResponse:
    """
    List all available workflows.
    
    Returns:
        Dictionary of workflow names to their metadata
    """
    tiger_user_id = get_current_tiger_user_id(request)
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    workflows = workflow_scheduler.list_workflows()
    
    return WorkflowListResponse(workflows=workflows)


@router.post("/{workflow_name}/execute")
async def execute_workflow(
    request: Request,
    workflow_name: str,
    body: WorkflowExecuteRequest
) -> WorkflowExecutionResponse:
    """
    Execute a workflow manually.
    
    Args:
        workflow_name: Name of the workflow to execute
        body: Request body with optional context
        
    Returns:
        Workflow execution result
    """
    tiger_user_id = get_current_tiger_user_id(request)
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Check if workflow exists
    available = workflow_scheduler.list_workflows()
    if workflow_name not in available:
        raise HTTPException(
            status_code=404, 
            detail=f"Workflow '{workflow_name}' not found. Available: {list(available.keys())}"
        )
    
    try:
        execution = await workflow_scheduler.execute_workflow(
            workflow_name=workflow_name,
            user_id=tiger_user_id,
            context=body.context
        )
        
        # Count completed steps
        completed = sum(1 for s in execution.steps if s.status.value == "completed")
        
        return WorkflowExecutionResponse(
            execution_id=execution.execution_id,
            workflow_name=execution.workflow_name,
            status=execution.status,
            started_at=execution.started_at.isoformat(),
            completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
            steps_completed=completed,
            steps_total=len(execution.steps),
            results=execution.get_completed_results()
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Workflow execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


@router.get("/{workflow_name}/status/{execution_id}")
async def get_execution_status(
    request: Request,
    workflow_name: str,
    execution_id: str
) -> WorkflowExecutionResponse:
    """
    Get the status of a workflow execution.
    
    Args:
        workflow_name: Name of the workflow
        execution_id: Execution ID to check
        
    Returns:
        Current execution status
    """
    tiger_user_id = get_current_tiger_user_id(request)
    if tiger_user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    execution = workflow_engine.get_execution(execution_id)
    
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")
    
    if execution.workflow_name != workflow_name:
        raise HTTPException(status_code=400, detail="Workflow name mismatch")
    
    if execution.user_id != tiger_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this execution")
    
    completed = sum(1 for s in execution.steps if s.status.value == "completed")
    
    return WorkflowExecutionResponse(
        execution_id=execution.execution_id,
        workflow_name=execution.workflow_name,
        status=execution.status,
        started_at=execution.started_at.isoformat(),
        completed_at=execution.completed_at.isoformat() if execution.completed_at else None,
        steps_completed=completed,
        steps_total=len(execution.steps),
        results=execution.get_completed_results()
    )

