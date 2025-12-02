"""
Nicole V7 Workflows Package

Contains YAML workflow definitions for automated multi-step processes.

Available Workflows:
- sports_oracle: Daily sports predictions and analysis
- morning_briefing: Personalized morning briefing 
- memory_consolidation: Nightly memory maintenance

Usage:
    from app.services import workflow_engine
    from pathlib import Path
    
    # Load a workflow
    workflow_path = Path(__file__).parent / "sports_oracle.yaml"
    workflow_engine.load_workflow_file(str(workflow_path))
    
    # Execute
    result = await workflow_engine.execute(
        workflow_name="sports_oracle_daily",
        user_id=1,
        context={"user": {"location": "New York"}}
    )
"""

from pathlib import Path

WORKFLOWS_DIR = Path(__file__).parent

# Available workflow files
AVAILABLE_WORKFLOWS = {
    "sports_oracle": WORKFLOWS_DIR / "sports_oracle.yaml",
    "morning_briefing": WORKFLOWS_DIR / "morning_briefing.yaml",
    "memory_consolidation": WORKFLOWS_DIR / "memory_consolidation.yaml",
}


def get_workflow_path(name: str) -> Path:
    """Get the path to a workflow file by name."""
    if name in AVAILABLE_WORKFLOWS:
        return AVAILABLE_WORKFLOWS[name]
    raise ValueError(f"Unknown workflow: {name}. Available: {list(AVAILABLE_WORKFLOWS.keys())}")


def list_workflows() -> list:
    """List all available workflow names."""
    return list(AVAILABLE_WORKFLOWS.keys())

