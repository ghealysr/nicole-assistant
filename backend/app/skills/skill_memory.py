"""
Helpers for logging skill usage into Nicole's memory system.

This module provides:
1. Knowledge base creation per skill (for organizing skill-related memories)
2. Memory recording for skill runs (success/failure tracking)
3. History logging for audit trail
"""

from __future__ import annotations

import logging
from typing import Optional
from textwrap import shorten
from datetime import datetime

from app.services.alphawave_memory_service import memory_service
from app.skills.registry import SkillMetadata, SkillRegistry
from app.skills.skill_history import append_history

logger = logging.getLogger(__name__)


class SkillMemoryManager:
    """
    Manages memory integration for skill executions.
    
    Responsibilities:
    - Create/retrieve knowledge bases for skills
    - Record skill run results as memories
    - Maintain audit trail via history file
    """
    
    def __init__(self, registry: SkillRegistry):
        self.registry = registry
        logger.info("[SKILL MEMORY] Manager initialized")

    async def ensure_skill_kb(self, user_id: int, skill: SkillMetadata) -> Optional[int]:
        """
        Ensure a knowledge base exists for this skill.
        
        Creates one if it doesn't exist and updates the skill metadata.
        Returns the KB ID or None if creation failed.
        """
        # Return existing KB if already set
        if skill.knowledge_base_id:
            return skill.knowledge_base_id
        
        try:
            kb = await memory_service.create_knowledge_base(
                user_id=user_id,
                kb_data={
                    "name": f"{skill.name} Skill",
                    "description": f"Knowledge base for {skill.name} skill. {skill.description}",
                    "kb_type": "skill",
                    "icon": "🧠",
                    "color": "#B8A8D4",
                },
            )
            
            if kb and kb.get("kb_id"):
                skill.knowledge_base_id = kb["kb_id"]
                try:
                    self.registry.update_skill(skill)
                    logger.info(f"[SKILL MEMORY] Created KB {kb['kb_id']} for skill {skill.id}")
                except Exception as update_err:
                    logger.warning(f"[SKILL MEMORY] Failed to persist KB ID to registry: {update_err}")
                return kb["kb_id"]
            else:
                logger.warning(f"[SKILL MEMORY] KB creation returned no kb_id for skill {skill.id}")
                return None
                
        except Exception as e:
            logger.error(f"[SKILL MEMORY] Failed to create KB for skill {skill.id}: {e}")
            return None

    async def record_run(
        self,
        user_id: int,
        conversation_id: Optional[int],
        skill: SkillMetadata,
        result_status: str,
        output: Optional[str],
        log_file: str,
    ) -> None:
        """
        Record a skill execution in Nicole's memory system.
        
        Creates a memory entry with the run result and updates the history file.
        """
        # Try to get/create KB, but don't fail if we can't
        kb_id = None
        try:
            kb_id = await self.ensure_skill_kb(user_id, skill)
        except Exception as kb_err:
            logger.warning(f"[SKILL MEMORY] KB creation failed, continuing without: {kb_err}")
        
        # Build memory content
        snippet = shorten(output or "", width=400, placeholder="…")
        content = (
            f"Skill {skill.name} ({skill.id}) run {result_status}. "
            f"Log: {log_file}. Output snippet: {snippet}"
        )
        
        # Save to memory system
        try:
            await memory_service.save_memory(
                user_id=user_id,
                memory_type="workflow",
                content=content,
                context="skill_run",
                importance=0.6 if result_status != "failed" else 0.8,
                knowledge_base_id=kb_id,
                source="nicole",
                related_conversation=conversation_id,
            )
            logger.debug(f"[SKILL MEMORY] Recorded run for skill {skill.id}")
        except Exception as mem_err:
            logger.error(f"[SKILL MEMORY] Failed to save memory for skill {skill.id}: {mem_err}")
        
        # Always append to history file (local, doesn't depend on DB)
        try:
            append_history(
                {
                    "skill_id": skill.id,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "status": result_status,
                    "log": log_file,
                }
            )
        except Exception as hist_err:
            logger.warning(f"[SKILL MEMORY] Failed to append history: {hist_err}")


skill_memory_manager: Optional[SkillMemoryManager] = None


def get_skill_memory_manager(registry: SkillRegistry) -> SkillMemoryManager:
    global skill_memory_manager
    if not skill_memory_manager:
        skill_memory_manager = SkillMemoryManager(registry)
    return skill_memory_manager

