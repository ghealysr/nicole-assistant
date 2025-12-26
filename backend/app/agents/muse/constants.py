"""
Muse Design Research Agent - Configuration Constants

Centralized configuration for the Muse agent system, including:
- Model configuration
- Generation parameters
- Timeouts and limits
- Feature flags
"""

from typing import Final

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

# Primary model for complex reasoning (research, analysis, style guides)
MUSE_PRIMARY_MODEL: Final[str] = "gemini-3-pro-preview"

# Fast model for simpler tasks (JSON extraction, quick analysis)
MUSE_FAST_MODEL: Final[str] = "gemini-2.0-flash-exp"

# Image generation model (Imagen 3)
IMAGEN_MODEL: Final[str] = "imagen-3.0-generate-001"
IMAGEN_FAST_MODEL: Final[str] = "imagen-3.0-fast-generate-001"

# ============================================================================
# GENERATION PARAMETERS
# ============================================================================

# Mood board generation
MOODBOARD_COUNT_DEFAULT: Final[int] = 4
MOODBOARD_COUNT_MIN: Final[int] = 2
MOODBOARD_COUNT_MAX: Final[int] = 6
MOODBOARD_TEMPERATURE: Final[float] = 0.9  # Higher for creative diversity
MOODBOARD_MAX_TOKENS: Final[int] = 3000

# Style guide generation
STYLEGUIDE_TEMPERATURE: Final[float] = 0.7
STYLEGUIDE_MAX_TOKENS: Final[int] = 8000

# Brief analysis
BRIEF_ANALYSIS_MAX_TOKENS: Final[int] = 2000

# Web research
WEB_RESEARCH_MAX_URLS: Final[int] = 10
WEB_RESEARCH_TIMEOUT_SECONDS: Final[int] = 30

# ============================================================================
# IMAGE GENERATION
# ============================================================================

# Preview image generation
PREVIEW_IMAGE_ASPECT_RATIO: Final[str] = "16:9"
PREVIEW_IMAGE_MAX_RETRIES: Final[int] = 2
PREVIEW_IMAGE_RETRY_DELAY_SECONDS: Final[float] = 2.0
PREVIEW_IMAGE_CONCURRENCY: Final[int] = 2

# Cost tracking (per image)
IMAGEN_COST_PER_IMAGE: Final[float] = 0.04
IMAGEN_FAST_COST_PER_IMAGE: Final[float] = 0.02

# ============================================================================
# KNOWLEDGE BASE
# ============================================================================

# Maximum tokens for knowledge context in prompts
KB_CONTEXT_MAX_TOKENS: Final[int] = 6000
KB_CONTEXT_MAX_SECTIONS: Final[int] = 8

# Search parameters
KB_SEARCH_LIMIT: Final[int] = 10

# ============================================================================
# A/B TESTING & ANALYTICS
# ============================================================================

# Historical preferences lookback period (days)
ANALYTICS_LOOKBACK_DAYS: Final[int] = 90

# Minimum selections required to consider data sufficient
ANALYTICS_MIN_SELECTIONS: Final[int] = 2

# Maximum aesthetics to consider in preferences
ANALYTICS_TOP_AESTHETICS_LIMIT: Final[int] = 10

# ============================================================================
# TIMEOUTS & LIMITS
# ============================================================================

# Session timeout (hours)
SESSION_TIMEOUT_HOURS: Final[int] = 24

# Maximum inspirations per session
MAX_INSPIRATIONS_PER_SESSION: Final[int] = 10

# Maximum concurrent API requests
MAX_CONCURRENT_REQUESTS: Final[int] = 3

# ============================================================================
# FEATURE FLAGS
# ============================================================================

# Enable A/B testing analytics
ENABLE_AB_TESTING: Final[bool] = True

# Enable Imagen preview generation
ENABLE_IMAGEN_PREVIEWS: Final[bool] = True

# Enable historical preferences in generation
ENABLE_HISTORICAL_PREFERENCES: Final[bool] = True

# Enable web research phase
ENABLE_WEB_RESEARCH: Final[bool] = True

# ============================================================================
# EXPORT CONFIGURATION
# ============================================================================

# Supported export formats
EXPORT_FORMAT_FIGMA_TOKENS: Final[str] = "figma_tokens"
EXPORT_FORMAT_CSS_VARIABLES: Final[str] = "css_variables"
EXPORT_FORMAT_TAILWIND_CONFIG: Final[str] = "tailwind_config"
EXPORT_FORMAT_DESIGN_TOKENS: Final[str] = "design_tokens_json"

SUPPORTED_EXPORT_FORMATS: Final[tuple] = (
    EXPORT_FORMAT_FIGMA_TOKENS,
    EXPORT_FORMAT_CSS_VARIABLES,
    EXPORT_FORMAT_TAILWIND_CONFIG,
    EXPORT_FORMAT_DESIGN_TOKENS,
)

# Cache TTL for exports (hours)
EXPORT_CACHE_TTL_HOURS: Final[int] = 24

# ============================================================================
# SESSION STATUS VALUES
# ============================================================================

SESSION_STATUS_INTAKE: Final[str] = "intake"
SESSION_STATUS_PLANNING: Final[str] = "planning"
SESSION_STATUS_ANALYZING_BRIEF: Final[str] = "analyzing_brief"
SESSION_STATUS_ANALYZING_INSPIRATION: Final[str] = "analyzing_inspiration"
SESSION_STATUS_WEB_RESEARCH: Final[str] = "web_research"
SESSION_STATUS_GENERATING_MOODBOARDS: Final[str] = "generating_moodboards"
SESSION_STATUS_STREAMING_MOODBOARDS: Final[str] = "streaming_moodboards"
SESSION_STATUS_AWAITING_SELECTION: Final[str] = "awaiting_selection"
SESSION_STATUS_GENERATING_DESIGN: Final[str] = "generating_design"
SESSION_STATUS_AWAITING_APPROVAL: Final[str] = "awaiting_approval"
SESSION_STATUS_APPROVED: Final[str] = "approved"
SESSION_STATUS_REVISING_DESIGN: Final[str] = "revising_design"
SESSION_STATUS_HANDED_OFF: Final[str] = "handed_off"
SESSION_STATUS_FAILED: Final[str] = "failed"
SESSION_STATUS_CANCELLED: Final[str] = "cancelled"

# Active statuses (not terminal)
ACTIVE_SESSION_STATUSES: Final[tuple] = (
    SESSION_STATUS_INTAKE,
    SESSION_STATUS_PLANNING,
    SESSION_STATUS_ANALYZING_BRIEF,
    SESSION_STATUS_ANALYZING_INSPIRATION,
    SESSION_STATUS_WEB_RESEARCH,
    SESSION_STATUS_GENERATING_MOODBOARDS,
    SESSION_STATUS_STREAMING_MOODBOARDS,
    SESSION_STATUS_AWAITING_SELECTION,
    SESSION_STATUS_GENERATING_DESIGN,
    SESSION_STATUS_AWAITING_APPROVAL,
    SESSION_STATUS_REVISING_DESIGN,
)

# Terminal statuses
TERMINAL_SESSION_STATUSES: Final[tuple] = (
    SESSION_STATUS_APPROVED,
    SESSION_STATUS_HANDED_OFF,
    SESSION_STATUS_FAILED,
    SESSION_STATUS_CANCELLED,
)

