"""
Muse Design Research Agent.

A world-class Design Research Agent powered by Gemini 2.5 Pro that conducts
deep design research, generates mood boards, and creates agency-quality 
design specifications before any code is written.
"""

from app.agents.muse.core import MuseAgent, muse_agent
from app.agents.muse.prompts import MUSE_SYSTEM_PROMPT
from app.agents.muse import constants

__all__ = ["MuseAgent", "muse_agent", "MUSE_SYSTEM_PROMPT", "constants"]

