"""
Faz Code Agent Team

Multi-model agent pipeline for AI-powered web development.

Agent Hierarchy:
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NICOLE (Orchestrator)                              │
│                    Routes intent, manages pipeline                           │
├─────────────────┬─────────────────┬──────────────────┬──────────────────────┤
│ PLANNING AGENT  │ RESEARCH AGENT  │  CODING AGENT    │    QA AGENT          │
│ (Opus 4.5)      │ (Gemini 3 Pro)  │  (Gemini 3 Pro)  │  (Sonnet 4.5)        │
├─────────────────┼─────────────────┼──────────────────┼──────────────────────┤
│ Architecture    │ Web Search      │ Code Generation  │ Quality Checks       │
│ File Structure  │ Screenshots     │ Styling          │ Accessibility        │
│ Component Design│ Inspiration     │ Components       │ Performance          │
└─────────────────┴─────────────────┴──────────────────┴──────────────────────┘
"""

from .base_agent import BaseAgent, AgentResult
from .nicole import NicoleAgent
from .planning import PlanningAgent
from .research import ResearchAgent
from .design import DesignAgent
from .coding import CodingAgent
from .qa import QAAgent
from .review import ReviewAgent
from .memory import MemoryAgent

__all__ = [
    "BaseAgent",
    "AgentResult",
    "NicoleAgent",
    "PlanningAgent",
    "ResearchAgent",
    "DesignAgent",
    "CodingAgent",
    "QAAgent",
    "ReviewAgent",
    "MemoryAgent",
]

