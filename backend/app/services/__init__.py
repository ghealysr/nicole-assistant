"""
Nicole V7 Services Package

Core services for Nicole's functionality including:
- Memory management
- Document processing
- AI integrations
- Tool orchestration (Think Tool, Tool Search, Workflows)
- Agent Orchestration
"""

# Core services
from app.services.alphawave_memory_service import memory_service
from app.services.alphawave_document_service import document_service
from app.services.alphawave_embedding_service import embedding_service
from app.services.alphawave_search_service import search_service

# Intelligence services
from app.services.memory_intelligence import memory_intelligence_service
from app.services.alphawave_pattern_detection import pattern_detection_service
from app.services.alphawave_correction_service import correction_service

# Processing services
from app.services.alphawave_file_processor import file_processor
from app.services.alphawave_link_processor import link_processor

# Media/Storage services
from app.services.alphawave_cloudinary_service import cloudinary_service

# Agent Architecture Services (Anthropic Patterns)
from app.services.think_tool import think_tool_service, ThinkingStep, ThinkingSession
from app.services.tool_search_service import tool_search_service, ToolCategory
from app.services.tool_examples import tool_examples_service
from app.services.workflow_engine import (
    WorkflowRegistry,
    WorkflowExecutor,
    WorkflowDefinition,
    WorkflowState,
    WorkflowStepDefinition,
    WorkflowStepState,
)

# Agent Orchestration (Integration Layer)
from app.services.agent_orchestrator import agent_orchestrator

# Workflow Scheduling
from app.services.workflow_scheduler import workflow_scheduler

__all__ = [
    # Core
    "memory_service",
    "document_service",
    "embedding_service",
    "search_service",
    
    # Intelligence
    "memory_intelligence_service",
    "pattern_detection_service",
    "correction_service",
    
    # Processing
    "file_processor",
    "link_processor",
    
    # Media/Storage
    "cloudinary_service",
    
    # Agent Architecture
    "think_tool_service",
    "ThinkingStep",
    "ThinkingSession",
    "tool_search_service",
    "ToolCategory",
    "tool_examples_service",
    "WorkflowRegistry",
    "WorkflowExecutor",
    "WorkflowDefinition",
    "WorkflowState",
    "WorkflowStepDefinition",
    "WorkflowStepState",
    
    # Orchestration
    "agent_orchestrator",
    "workflow_scheduler",
]

