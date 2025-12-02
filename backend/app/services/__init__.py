"""
Nicole V7 Services Package

Core services for Nicole's functionality including:
- Memory management
- Document processing
- AI integrations
- Tool orchestration (NEW: Think Tool, Tool Search, Workflows)
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

# NEW: Agent Architecture Services (Anthropic Patterns)
from app.services.think_tool import think_tool_service, ThinkingStep, ThinkingSession
from app.services.tool_search_service import tool_search_service, ToolCategory
from app.services.tool_examples import tool_examples_service
from app.services.workflow_engine import workflow_engine, WorkflowExecution

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
    
    # Agent Architecture (NEW)
    "think_tool_service",
    "ThinkingStep",
    "ThinkingSession",
    "tool_search_service",
    "ToolCategory",
    "tool_examples_service",
    "workflow_engine",
    "WorkflowExecution",
]

