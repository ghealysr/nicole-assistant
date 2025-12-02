"""
Nicole V7 - Prompt Templates
============================

This module contains all system prompts and prompt templates for Nicole.
"""

from app.prompts.nicole_system_prompt import (
    build_nicole_system_prompt,
    build_memory_context,
    build_document_context,
)

__all__ = [
    "build_nicole_system_prompt",
    "build_memory_context",
    "build_document_context",
]

