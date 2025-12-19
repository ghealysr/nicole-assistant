"""
Alphawave Image Generation Service - Multi-Agent Architecture

Advanced image generation with 3-agent architecture:
1. Task Analyzer Agent - Analyzes request and selects optimal model
2. Prompt Enhancer Agent - Optimizes prompts per provider
3. Quality Router Agent - Handles quality control and preference learning

Supported Providers:
- Gemini 3 Pro Image (Nano Banana Pro): 4K, thinking, 14 ref images, Google Search grounding
- GPT Image 1.5: 4x faster, precise edits, improved text
- Seedream 4.5: High-quality via Replicate
- Recraft V3: Vector illustrations, logos, icons
- FLUX Pro/Schnell: Photorealistic via Replicate
- Ideogram V2: Text rendering, design

Features:
- Intelligent model selection based on task analysis
- Provider-optimized prompt enhancement
- Parallel generation across multiple models
- Quality routing with preference learning
- Persistent jobs/variants with full metadata
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

import httpx

from app.config import settings
from app.database import db as db_manager

try:
    import replicate  # type: ignore
except ImportError:
    replicate = None

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND TASK ANALYSIS
# =============================================================================

class TaskComplexity(str, Enum):
    """Complexity levels for image generation tasks."""
    SIMPLE = "simple"           # Single object, basic scene
    MEDIUM = "medium"           # Multiple objects, some composition
    COMPLEX = "complex"         # Multi-object, complex scene, specific requirements


class GenerationStrategy(str, Enum):
    """Strategy for generation execution."""
    SINGLE = "single"           # Use single best model
    PARALLEL = "parallel"       # Generate with multiple models in parallel
    SEQUENTIAL = "sequential"   # Try models in sequence until success


class TaskAnalysis:
    """Result of task analysis for model routing."""
    
    def __init__(
        self,
        complexity: TaskComplexity,
        text_in_image: bool,
        multi_object: bool,
        complex_scene: bool,
        needs_speed: bool,
        precise_edits: bool,
        artistic_style: bool,
        enterprise_quality: bool,
        recommended_model: str,
        fallback_model: str,
        strategy: GenerationStrategy,
        confidence: float
    ):
        self.complexity = complexity
        self.text_in_image = text_in_image
        self.multi_object = multi_object
        self.complex_scene = complex_scene
        self.needs_speed = needs_speed
        self.precise_edits = precise_edits
        self.artistic_style = artistic_style
        self.enterprise_quality = enterprise_quality
        self.recommended_model = recommended_model
        self.fallback_model = fallback_model
        self.strategy = strategy
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "complexity": self.complexity.value,
            "text_in_image": self.text_in_image,
            "multi_object": self.multi_object,
            "complex_scene": self.complex_scene,
            "needs_speed": self.needs_speed,
            "precise_edits": self.precise_edits,
            "artistic_style": self.artistic_style,
            "enterprise_quality": self.enterprise_quality,
            "recommended_model": self.recommended_model,
            "fallback_model": self.fallback_model,
            "strategy": self.strategy.value,
            "confidence": self.confidence
        }


class ImageGenerationService:
    """
    Unified interface for all image generation models with 3-agent architecture.
    
    Tier 1 - Primary Workhorses:
    - gemini_3_pro_image: Nano Banana Pro - Best overall (4K, thinking, grounding)
    - gpt_image: GPT Image 1.5 - Speed + precision
    - flux_2_pro: FLUX 2 Pro - Enterprise production
    - ideogram: Ideogram 3 - Best text rendering
    
    Tier 2 - Specialized:
    - seedream: Seedream 4.5 - Creative exploration
    - recraft: Vector illustrations, logos, icons
    - flux_schnell: Fast iterations
    """
    
    RECRAFT_MODEL_DEFAULT = "recraftv3"
    DEFAULT_WIDTH = 1024
    DEFAULT_HEIGHT = 1024

    # Cost per image (USD, approximate)
    MODEL_COSTS = {
        "recraft": 0.04,
        "flux_pro": 0.055,
        "flux_schnell": 0.003,
        "ideogram": 0.08,
        "imagen3": 0.04,
        "imagen3_fast": 0.02,
        "gemini_3_pro_image": 0.134,  # 1K-2K
        "gemini_3_pro_image_4k": 0.24,  # 4K
        "gpt_image": 0.04,  # GPT Image 1.5
        "seedream": 0.03,  # Seedream 4.5 via Replicate
    }

    # Model configurations with provider-specific settings
    MODEL_CONFIGS = {
        # =====================================================================
        # TIER 1: PRIMARY WORKHORSES
        # =====================================================================
        "gemini_3_pro_image": {
            "name": "Gemini 3 Pro Image (Nano Banana Pro)",
            "mode": "gemini",
            "gemini_model": "gemini-3-pro-image-preview",
            "supports_batch": True,
            "max_batch": 4,
            "supports_thinking": True,
            "supports_image_input": True,
            "supports_grounding": True,
            "max_reference_images": 14,
            "default_params": {
                "aspect_ratio": "1:1",
                "resolution": "2K",  # "1K", "2K", "4K"
            },
            "resolutions": ["1K", "2K", "4K"],
            "aspect_ratios": ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
            "strengths": ["multi_object", "complex_scene", "thinking", "grounding", "4k_output", "reference_images"],
            "cost_per_image": {"1K": 0.134, "2K": 0.134, "4K": 0.24},
            "description": "Best overall - 4K output, thinking mode, up to 14 reference images, Google Search grounding"
        },
        "gpt_image": {
            "name": "GPT Image 1.5",
            "mode": "openai",
            "model": "gpt-image-1",
            "supports_batch": True,
            "max_batch": 4,
            "supports_editing": True,
            "max_input_images": 16,
            "default_params": {
                "size": "1024x1024",
                "quality": "hd",
            },
            "sizes": ["1024x1024", "1792x1024", "1024x1792"],
            "qualities": ["standard", "hd"],
            "strengths": ["speed", "precise_edits", "text_rendering", "face_consistency"],
            "cost_per_image": 0.04,
            "description": "4x faster, precise editing, improved text rendering, maintains facial likeness"
        },
        "flux_pro": {
            "name": "FLUX 1.1 Pro",
            "mode": "replicate",
            "replicate_model": "black-forest-labs/flux-1.1-pro",
            "supports_batch": False,
            "default_params": {
                "aspect_ratio": "1:1",
                "output_quality": 100,
                "safety_tolerance": 2,
                "steps": 25,
                "guidance": 3.5,
            },
            "param_limits": {
                "steps": (1, 50),
                "guidance": (1.0, 10.0),
                "output_quality": (50, 100),
            },
            "strengths": ["photorealistic", "enterprise_quality"],
            "cost_per_image": 0.055,
            "description": "Enterprise production quality photorealistic images"
        },
        "ideogram": {
            "name": "Ideogram V3",
            "mode": "replicate",
            "replicate_model": "ideogram-ai/ideogram-v3",
            "supports_batch": False,
            "default_params": {
                "aspect_ratio": "1:1",
                "style_type": "Auto",
                "magic_prompt_option": "Auto",
            },
            "style_types": ["Auto", "General", "Realistic", "Design", "Render 3D", "Anime"],
            "strengths": ["text_in_image", "typography", "design"],
            "cost_per_image": 0.08,
            "description": "Best for text rendering in images, infographics, typography"
        },
        
        # =====================================================================
        # TIER 2: SPECIALIZED
        # =====================================================================
        "seedream": {
            "name": "Seedream 4.5",
            "mode": "replicate",
            "replicate_model": "bytedance/seedream-4.5",
            "supports_batch": False,
            "default_params": {
                "aspect_ratio": "1:1",
                "num_outputs": 1,
            },
            "strengths": ["artistic", "creative", "cinematic", "spatial_reasoning"],
            "cost_per_image": 0.03,
            "description": "Cinematic aesthetics, strong spatial reasoning, industry-ready"
        },
        "recraft": {
            "name": "Recraft V3",
            "mode": "mcp",
            "supports_batch": True,
            "max_batch": 4,
            "styles": [
                "realistic_image", "digital_illustration", "vector_illustration",
                "3d_render", "pixel_art", "anime", "logo", "icon"
            ],
            "default_style": "realistic_image",
            "strengths": ["vector", "logo", "icon", "illustration"],
            "cost_per_image": 0.04,
            "description": "Vector illustrations, logos, icons, scalable graphics"
        },
        "flux_schnell": {
            "name": "FLUX Schnell",
            "mode": "replicate",
            "replicate_model": "black-forest-labs/flux-schnell",
            "supports_batch": False,
            "default_params": {
                "aspect_ratio": "1:1",
                "output_quality": 90,
            },
            "param_limits": {
                "output_quality": (50, 100),
            },
            "strengths": ["speed", "iteration"],
            "cost_per_image": 0.003,
            "description": "Ultra-fast iterations for rapid prototyping"
        },
        
        # =====================================================================
        # LEGACY (kept for backwards compatibility)
        # =====================================================================
        "imagen3": {
            "name": "Imagen 3",
            "mode": "gemini",
            "gemini_model": "imagen-3.0-generate-001",
            "supports_batch": True,
            "max_batch": 4,
            "supports_thinking": False,
            "supports_image_input": False,
            "default_params": {
                "aspect_ratio": "1:1",
            },
            "aspect_ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"],
            "cost_per_image": 0.04,
        },
        "imagen3_fast": {
            "name": "Imagen 3 Fast",
            "mode": "gemini",
            "gemini_model": "imagen-3.0-fast-generate-001",
            "supports_batch": True,
            "max_batch": 4,
            "supports_thinking": False,
            "supports_image_input": False,
            "default_params": {
                "aspect_ratio": "1:1",
            },
            "aspect_ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"],
            "cost_per_image": 0.02,
        },
        "gemini": {
            "name": "Gemini 3 Pro Image (Legacy)",
            "mode": "gemini",
            "gemini_model": "gemini-3-pro-image-preview",
            "supports_batch": False,
            "supports_thinking": True,
            "supports_image_input": True,
            "default_params": {
                "size": "1024x1024",
            },
            "sizes": ["1024x1024", "2048x2048", "4096x4096"],
            "cost_per_image": {
                "1024x1024": 0.134,
                "2048x2048": 0.134,
                "4096x4096": 0.24,
            },
        },
    }

    # Aspect ratio to pixel dimensions mapping
    ASPECT_RATIOS = {
        "1:1": (1024, 1024),
        "16:9": (1344, 768),
        "9:16": (768, 1344),
        "4:3": (1152, 896),
        "3:4": (896, 1152),
        "3:2": (1216, 832),
        "2:3": (832, 1216),
        "4:5": (896, 1120),
        "5:4": (1120, 896),
        "21:9": (1536, 640),
    }
    
    # Resolution to pixels mapping for Gemini 3 Pro Image
    RESOLUTION_PIXELS = {
        "1K": 1024,
        "2K": 2048,
        "4K": 4096,
    }
    
    # Patterns for task analysis
    TEXT_PATTERNS = [
        r'\btext\b', r'\btypo', r'\bfont\b', r'\bletter', r'\bword\b', r'\bslogan\b',
        r'\bheadline\b', r'\btitle\b', r'\blabel\b', r'\bcaption\b', r'\bquote\b',
        r'\bsign\b', r'\bposter\b', r'\bbanner\b', r'\blogo\b', r'\binfographic\b'
    ]
    MULTI_OBJECT_PATTERNS = [
        r'\band\b', r'\bwith\b', r'\bmultiple\b', r'\bseveral\b', r'\bgroup\b',
        r'\bteam\b', r'\bfamily\b', r'\bcollection\b', r'\barrangement\b'
    ]
    ARTISTIC_PATTERNS = [
        r'\bartistic\b', r'\babstract\b', r'\bsurreal\b', r'\bdream', r'\bfantasy\b',
        r'\bimpression', r'\bpainting\b', r'\bwatercolor\b', r'\boil\b', r'\bsketch\b'
    ]
    SPEED_PATTERNS = [
        r'\bquick\b', r'\bfast\b', r'\brapid\b', r'\bdraft\b', r'\brough\b', r'\btest\b'
    ]

    def __init__(self):
        self.gateway_url = getattr(settings, "MCP_GATEWAY_URL", "http://127.0.0.1:3100")
        self.client = httpx.AsyncClient(timeout=180.0)  # Increased for 4K image gen
        
        # Initialize Replicate client (FLUX, Ideogram, Seedream)
        replicate_token = getattr(settings, "REPLICATE_API_TOKEN", "")
        if replicate and replicate_token:
            self.replicate_client = replicate.Client(api_token=replicate_token)
            logger.info("[IMAGE] Replicate client initialized (FLUX, Ideogram, Seedream)")
        else:
            self.replicate_client = None
            logger.warning("[IMAGE] Replicate client NOT configured")
        
        # Initialize Anthropic client for agent intelligence
        anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", "")
        if AsyncAnthropic and anthropic_key:
            self.anthropic = AsyncAnthropic(api_key=anthropic_key)
            logger.info("[IMAGE] Anthropic client initialized (Task Analyzer, Prompt Enhancer)")
        else:
            self.anthropic = None
            logger.warning("[IMAGE] Anthropic client NOT configured (agents disabled)")
        
        # OpenAI client for GPT Image 1.5
        try:
            from app.integrations.alphawave_openai import openai_client
            self.openai_client = openai_client
            logger.info("[IMAGE] OpenAI client initialized (GPT Image 1.5)")
        except Exception as e:
            self.openai_client = None
            logger.warning(f"[IMAGE] OpenAI client NOT configured: {e}")
        
        # User preference tracking for Quality Router Agent
        self.user_preferences: Dict[int, Dict[str, Any]] = {}
    
    # =========================================================================
    # AGENT 1: TASK ANALYZER
    # =========================================================================
    
    async def analyze_task(
        self,
        prompt: str,
        use_case: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> TaskAnalysis:
        """
        Task Analyzer Agent: Analyzes the request and recommends optimal model.
        
        Evaluates:
        - Subject complexity (single vs multi-object)
        - Text requirements (in-image typography)
        - Style preference (photorealistic vs artistic)
        - Speed requirements (iterative workflow vs final)
        - Output use (social, print, product, concept)
        
        Returns:
            TaskAnalysis with recommended model, fallback, and strategy
        """
        prompt_lower = prompt.lower()
        
        # Detect text-in-image requirements
        text_in_image = any(re.search(p, prompt_lower) for p in self.TEXT_PATTERNS)
        
        # Detect multi-object/complex scene
        multi_object = any(re.search(p, prompt_lower) for p in self.MULTI_OBJECT_PATTERNS)
        complex_scene = multi_object or len(prompt.split()) > 30
        
        # Detect artistic style
        artistic_style = any(re.search(p, prompt_lower) for p in self.ARTISTIC_PATTERNS)
        
        # Detect speed requirements
        needs_speed = any(re.search(p, prompt_lower) for p in self.SPEED_PATTERNS)
        
        # Use case analysis
        precise_edits = use_case in ("product", "hero", "banner")
        enterprise_quality = use_case in ("enterprise", "print", "campaign")
        
        # Determine complexity
        if complex_scene or len(prompt.split()) > 50:
            complexity = TaskComplexity.COMPLEX
        elif multi_object or len(prompt.split()) > 20:
            complexity = TaskComplexity.MEDIUM
        else:
            complexity = TaskComplexity.SIMPLE
        
        # Model selection logic
        if text_in_image:
            # Ideogram is still best for text rendering
            recommended = "ideogram"
            fallback = "gemini_3_pro_image"  # Gemini 3 Pro has improved text
            confidence = 0.9
        elif needs_speed:
            recommended = "gpt_image"  # 4x faster
            fallback = "flux_schnell"
            confidence = 0.85
        elif precise_edits:
            recommended = "gpt_image"  # Precise editing
            fallback = "gemini_3_pro_image"
            confidence = 0.85
        elif multi_object or complex_scene:
            recommended = "gemini_3_pro_image"  # Best for complex scenes
            fallback = "gpt_image"
            confidence = 0.9
        elif artistic_style:
            recommended = "seedream"  # Cinematic/artistic
            fallback = "gemini_3_pro_image"
            confidence = 0.8
        elif enterprise_quality:
            recommended = "flux_pro"  # Enterprise production
            fallback = "gemini_3_pro_image"
            confidence = 0.85
        elif use_case in ("logo", "icon", "vector"):
            recommended = "recraft"
            fallback = "ideogram"
            confidence = 0.95
        else:
            # Default: Gemini 3 Pro Image (best overall)
            recommended = "gemini_3_pro_image"
            fallback = "gpt_image"
            confidence = 0.75
        
        # Check user preferences (Quality Router learning)
        if user_id and user_id in self.user_preferences:
            prefs = self.user_preferences[user_id]
            if use_case and use_case in prefs.get("preferred_models", {}):
                preferred = prefs["preferred_models"][use_case]
                if preferred in self.MODEL_CONFIGS:
                    recommended = preferred
                    confidence = min(confidence + 0.1, 1.0)
                    logger.info(f"[IMAGE] Using user preference: {preferred} for {use_case}")
        
        # Determine strategy
        if complexity == TaskComplexity.COMPLEX:
            strategy = GenerationStrategy.PARALLEL  # Try multiple in parallel
        elif confidence < 0.7:
            strategy = GenerationStrategy.SEQUENTIAL  # Fallback if needed
        else:
            strategy = GenerationStrategy.SINGLE
        
        analysis = TaskAnalysis(
            complexity=complexity,
            text_in_image=text_in_image,
            multi_object=multi_object,
            complex_scene=complex_scene,
            needs_speed=needs_speed,
            precise_edits=precise_edits,
            artistic_style=artistic_style,
            enterprise_quality=enterprise_quality,
            recommended_model=recommended,
            fallback_model=fallback,
            strategy=strategy,
            confidence=confidence
        )
        
        logger.info(
            f"[IMAGE] Task Analysis: {recommended} (conf={confidence:.2f}), "
            f"fallback={fallback}, strategy={strategy.value}"
        )
        
        return analysis

    async def shutdown(self):
        """Clean up HTTP client."""
        await self.client.aclose()
        logger.info("[IMAGE] Service shutdown complete")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    async def _call_mcp_tool(self, name: str, arguments: Dict) -> Dict:
        """Call a tool via the MCP HTTP bridge."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        try:
            resp = await self.client.post(f"{self.gateway_url}/rpc", json=payload)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise RuntimeError(data["error"].get("message", "Unknown MCP error"))
            return data.get("result", {})
        except httpx.HTTPError as e:
            logger.error(f"[IMAGE] MCP tool call failed: {e}")
            raise RuntimeError(f"MCP bridge error: {e}")

    def _validate_batch(self, batch_count: int, model_key: str) -> int:
        """Validate and clamp batch count per model capabilities."""
        cfg = self.MODEL_CONFIGS.get(model_key, {})
        if cfg.get("supports_batch"):
            max_batch = cfg.get("max_batch", 4)
            return max(1, min(batch_count, max_batch))
        return 1  # Non-batch models always return 1

    def _validate_params(self, model_key: str, parameters: Dict) -> Dict:
        """Validate and clamp parameters per model limits."""
        cfg = self.MODEL_CONFIGS.get(model_key, {})
        validated = dict(parameters)
        
        # Apply default params first
        defaults = cfg.get("default_params", {})
        for key, value in defaults.items():
            if key not in validated:
                validated[key] = value
        
        # Clamp numeric params to limits
        limits = cfg.get("param_limits", {})
        for key, (min_val, max_val) in limits.items():
            if key in validated:
                validated[key] = max(min_val, min(validated[key], max_val))
        
        # Validate style for Recraft
        if model_key == "recraft":
            style = validated.get("style", cfg.get("default_style", "realistic_image"))
            if style not in cfg.get("styles", []):
                style = cfg.get("default_style", "realistic_image")
            validated["style"] = style
        
        # Validate style_type for Ideogram
        if model_key == "ideogram":
            style_type = validated.get("style_type", "Auto")
            if style_type not in cfg.get("style_types", []):
                validated["style_type"] = "Auto"
        
        # Resolve aspect ratio to dimensions
        aspect = validated.get("aspect_ratio", "1:1")
        if aspect in self.ASPECT_RATIOS:
            validated["width"], validated["height"] = self.ASPECT_RATIOS[aspect]
        else:
            validated["width"] = validated.get("width", self.DEFAULT_WIDTH)
            validated["height"] = validated.get("height", self.DEFAULT_HEIGHT)
        
        return validated

    # =========================================================================
    # AGENT 2: PROMPT ENHANCER
    # =========================================================================
    
    async def enhance_prompt(
        self,
        original_prompt: str,
        model_key: str,
        use_case: Optional[str] = None,
        task_analysis: Optional[TaskAnalysis] = None,
    ) -> str:
        """
        Prompt Enhancer Agent: Transforms user intent into provider-optimized prompts.
        
        Enhancements include:
        - Model-specific syntax and markers
        - Lighting and composition details
        - Quality and style coherence
        - Text rendering instructions (when detected)
        
        Returns enhanced prompt or original if enhancement fails/disabled.
        """
        if not self.anthropic:
            logger.debug("[IMAGE] Prompt enhancement skipped (no Anthropic client)")
            return original_prompt
        
        # Comprehensive model-specific guidance
        model_guidance = {
            "gemini_3_pro_image": """
                Gemini 3 Pro Image is Google's most advanced model with "thinking" mode.
                - Supports up to 14 reference images
                - Can generate 1K, 2K, 4K resolution
                - Has grounding with Google Search for real-time data
                - Excellent at complex multi-object scenes
                - Strong at text rendering (improved from previous)
                Prompt style: Detailed, descriptive, can include real-world references
                Quality markers: "ultra high quality", "4K resolution", "professional"
            """,
            "gpt_image": """
                GPT Image 1.5 is OpenAI's latest model (4x faster than DALL-E 3).
                - Best for precise edits and instruction following
                - Strong at multi-image workflows
                - Improved text rendering
                - Quick iteration cycles
                Prompt style: Clear, instructional, precise descriptions
                Quality markers: "highly detailed", "professional quality", "sharp focus"
            """,
            "flux_pro": """
                FLUX.2 Pro is enterprise-grade photorealistic generation.
                - Maximum photorealism achievable
                - Strong at human faces and hands
                - Excellent lighting and shadow handling
                Prompt style: Photography-focused, camera angles, lens types
                Quality markers: "8K UHD", "RAW photo", "DSLR quality"
            """,
            "ideogram": """
                Ideogram V3 is SPECIALIZED for text-in-image rendering.
                - Put any text you want rendered in "quotes"
                - Specify font style (bold, italic, serif, sans-serif)
                - Define text placement (centered, top, banner, etc.)
                Prompt style: Text in quotes + visual context
                Quality markers: "crisp text", "readable font", "high contrast"
            """,
            "seedream": """
                Seedream 4.5 by ByteDance excels at cinematic aesthetics.
                - Strong spatial reasoning and 3D understanding
                - Rich world knowledge (can reference films, art styles)
                - Artistic and creative interpretations
                Prompt style: Cinematic, atmospheric, story-driven
                Quality markers: "cinematic", "film still", "dramatic lighting"
            """,
            "recraft": """
                Recraft V3 specializes in vector graphics and logos.
                - Outputs clean, scalable graphics
                - Excellent for icons, logos, illustrations
                - Supports transparent backgrounds
                Prompt style: Design-focused, geometric, style specifications
                Quality markers: "vector style", "clean lines", "flat design"
            """,
            "flux_schnell": """
                FLUX Schnell is ultra-fast for rapid prototyping.
                - Speed over detail
                - Good for exploring concepts quickly
                Prompt style: Keep it simple, focus on key elements
                Quality markers: "concept art", "quick sketch"
            """,
        }
        
        use_case_guidance = {
            "logo": "Focus on brand identity, clean lines, scalability. Specify if transparent background needed. Minimal colors (3-4 max). Strong silhouette.",
            "hero": "Wide composition (16:9), dynamic lighting, professional quality, suitable for landing page header. Negative space for text overlay.",
            "social": "Eye-catching, centered subject, works at small sizes (1:1 or 4:5), vibrant colors, high contrast for mobile viewing.",
            "poster": "Dramatic composition, areas for text placement, high contrast, movie poster style.",
            "icon": "Simple, recognizable at 64x64, minimal detail, clear silhouette, works in monochrome.",
            "product": "Clean background (white/gradient), professional lighting, multiple angles, e-commerce ready.",
            "banner": "Wide aspect (21:9 or 16:9), text-safe zones, brand-consistent colors.",
            "avatar": "Square (1:1), centered face/subject, works at small sizes, distinctive.",
            "thumbnail": "High contrast, recognizable at 320px, bold subject, YouTube-optimized.",
            "concept": "Exploratory, artistic freedom, moodboard-style, convey idea over perfection.",
        }
        
        # Build analysis context if provided
        analysis_context = ""
        if task_analysis:
            analysis_context = f"""
Task Analysis Insights:
- Complexity: {task_analysis.complexity.value}
- Text in image required: {task_analysis.text_in_image}
- Multi-object scene: {task_analysis.multi_object}
- Artistic style: {task_analysis.artistic_style}
- Speed priority: {task_analysis.needs_speed}
"""
        
        system = f"""You are an expert image generation prompt engineer for the {model_key} model.

{model_guidance.get(model_key, 'Optimize for high-quality image generation.')}

{f"Use case: {use_case}" if use_case else ""}
{use_case_guidance.get(use_case, '') if use_case else ""}

{analysis_context}

Your task: Transform the user's prompt into an optimal prompt specifically for {model_key}.

CRITICAL RULES:
1. PRESERVE the core intent and subject - don't change what they're asking for
2. ADD technical details: composition, lighting, style, perspective, colors
3. USE model-specific syntax (e.g., "quotes for text" in Ideogram)
4. INCLUDE appropriate quality markers for the model
5. KEEP it under 600 characters
6. OUTPUT ONLY the enhanced prompt - no explanation, no quotes around it
7. If text rendering is needed, format it appropriately for the model

Your output will be sent directly to the image generation API."""

        try:
            response = await self.anthropic.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=400,
                system=system,
                messages=[{"role": "user", "content": original_prompt}],
            )
            enhanced = response.content[0].text.strip()
            # Remove quotes if the model wrapped it in quotes
            if enhanced.startswith('"') and enhanced.endswith('"'):
                enhanced = enhanced[1:-1]
            
            logger.info(f"[IMAGE] Prompt enhanced for {model_key}: {len(original_prompt)} -> {len(enhanced)} chars")
            return enhanced
        except Exception as e:
            logger.warning(f"[IMAGE] Prompt enhancement failed: {e}")
            return original_prompt
    
    # =========================================================================
    # AGENT 3: QUALITY ROUTER
    # =========================================================================
    
    async def evaluate_result(
        self,
        user_id: int,
        variant_id: int,
        image_url: str,
        original_prompt: str,
        model_key: str,
        feedback: Optional[str] = None,  # "accept", "reject", "edit"
    ) -> Dict[str, Any]:
        """
        Quality Router Agent: Evaluates generation results and learns preferences.
        
        Responsibilities:
        - Evaluate technical quality (resolution, artifacts)
        - Track success patterns per user
        - Learn model preferences for use cases
        - Decide on regeneration vs editing vs acceptance
        
        Args:
            user_id: User providing feedback
            variant_id: Image variant ID
            image_url: URL of generated image
            original_prompt: What the user asked for
            model_key: Model that generated this
            feedback: User's explicit feedback if any
            
        Returns:
            Evaluation with recommendations
        """
        evaluation = {
            "variant_id": variant_id,
            "model_key": model_key,
            "user_id": user_id,
            "status": "pending",
            "recommendation": None,
        }
        
        # Track user feedback for preference learning
        if feedback:
            if user_id not in self.user_preferences:
                self.user_preferences[user_id] = {
                    "model_scores": {},  # model_key -> success rate
                    "preferred_models": {},  # use_case -> model_key
                    "feedback_count": 0,
                }
            
            prefs = self.user_preferences[user_id]
            prefs["feedback_count"] += 1
            
            if model_key not in prefs["model_scores"]:
                prefs["model_scores"][model_key] = {"accepts": 0, "rejects": 0}
            
            if feedback == "accept":
                prefs["model_scores"][model_key]["accepts"] += 1
                evaluation["status"] = "accepted"
                evaluation["recommendation"] = "complete"
                logger.info(f"[IMAGE] User {user_id} accepted {model_key} result")
                
            elif feedback == "reject":
                prefs["model_scores"][model_key]["rejects"] += 1
                evaluation["status"] = "rejected"
                
                # Suggest alternative model
                task_analysis = await self.analyze_task(original_prompt, user_id=user_id)
                if task_analysis.fallback_model != model_key:
                    evaluation["recommendation"] = "regenerate"
                    evaluation["suggested_model"] = task_analysis.fallback_model
                else:
                    evaluation["recommendation"] = "edit_prompt"
                    
                logger.info(f"[IMAGE] User {user_id} rejected {model_key}, suggesting {evaluation.get('suggested_model', 'prompt edit')}")
                
            elif feedback == "edit":
                evaluation["status"] = "editing"
                evaluation["recommendation"] = "edit_image"
        
        # Calculate success rate for model
        if user_id in self.user_preferences:
            scores = self.user_preferences[user_id]["model_scores"].get(model_key, {})
            accepts = scores.get("accepts", 0)
            rejects = scores.get("rejects", 0)
            total = accepts + rejects
            if total > 0:
                evaluation["model_success_rate"] = accepts / total
        
        return evaluation
    
    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get learned preferences for a user."""
        if user_id not in self.user_preferences:
            return {"message": "No preference history yet"}
        
        prefs = self.user_preferences[user_id]
        
        # Calculate model rankings
        rankings = []
        for model_key, scores in prefs.get("model_scores", {}).items():
            accepts = scores.get("accepts", 0)
            rejects = scores.get("rejects", 0)
            total = accepts + rejects
            if total > 0:
                rankings.append({
                    "model": model_key,
                    "success_rate": accepts / total,
                    "total_uses": total,
                })
        
        rankings.sort(key=lambda x: x["success_rate"], reverse=True)
        
        return {
            "user_id": user_id,
            "feedback_count": prefs.get("feedback_count", 0),
            "model_rankings": rankings,
            "preferred_models": prefs.get("preferred_models", {}),
        }

    async def create_job(
        self,
        user_id: int,
        title: str,
        project: Optional[str] = None,
        use_case: Optional[str] = None,
        preset_used: Optional[str] = None,
    ) -> Dict:
        job = await db_manager.pool.fetchrow(
            """
            INSERT INTO image_jobs (user_id, title, project, use_case, preset_used)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            user_id,
            title,
            project,
            use_case,
            preset_used,
        )
        return dict(job)

    # ------------------------------------------------------------------ #
    # Generation entrypoints
    # ------------------------------------------------------------------ #
    async def generate(
        self,
        user_id: int,
        prompt: str,
        model_key: str,
        parameters: Dict,
        batch_count: int = 1,
        job_id: Optional[int] = None,
        project: Optional[str] = None,
        use_case: Optional[str] = None,
        preset_used: Optional[str] = None,
        enhance_prompt_enabled: bool = True,
    ) -> Dict:
        """
        Generate image(s) using the specified model.
        
        Args:
            user_id: Owner of the generated images
            prompt: Text description of desired image
            model_key: One of 'recraft', 'flux_pro', 'flux_schnell', 'ideogram'
            parameters: Model-specific parameters (style, aspect_ratio, etc.)
            batch_count: Number of variants to generate (clamped per model)
            job_id: Existing job ID or None to create new
            project: Project name for organization
            use_case: Type of image (logo, hero, social, poster, icon)
            preset_used: Preset key if using a saved preset
            enhance_prompt_enabled: Whether to enhance prompt via Claude
            
        Returns:
            Dict with job_id, variants list, count, model_key, elapsed_ms
        """
        if model_key not in self.MODEL_CONFIGS:
            raise ValueError(f"Unsupported model_key: {model_key}. Valid: {list(self.MODEL_CONFIGS.keys())}")

        model_cfg = self.MODEL_CONFIGS[model_key]
        
        # Validate and clamp parameters
        validated_params = self._validate_params(model_key, parameters)
        batch_count = self._validate_batch(batch_count, model_key)
        
        logger.info(f"[IMAGE] Generating {batch_count}x {model_key} for user {user_id}")

        # Enhance prompt if enabled
        enhanced_prompt = prompt
        if enhance_prompt_enabled:
            enhanced_prompt = await self.enhance_prompt(prompt, model_key, use_case)
            validated_params["enhanced_prompt"] = enhanced_prompt

        # Create job if not provided
        if job_id is None:
            title = f"{use_case or model_key} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            job = await self.create_job(user_id, title, project, use_case, preset_used)
            job_id = job["job_id"]
            logger.info(f"[IMAGE] Created job {job_id}")

        # Route to appropriate provider
        mode = model_cfg["mode"]
        
        if mode == "mcp":
            return await self._generate_recraft_via_mcp(
                user_id=user_id,
                job_id=job_id,
                prompt=enhanced_prompt,
                original_prompt=prompt,
                parameters=validated_params,
                batch_count=batch_count,
                model_key=model_key,
            )
        elif mode == "gemini":
            return await self._generate_via_gemini(
                user_id=user_id,
                job_id=job_id,
                prompt=enhanced_prompt,
                original_prompt=prompt,
                parameters=validated_params,
                batch_count=batch_count,
                model_key=model_key,
            )
        elif mode == "openai":
            if not self.openai_client:
                raise RuntimeError(
                    "OpenAI client not configured. "
                    "Set OPENAI_API_KEY in environment."
                )
            return await self._generate_via_openai(
                user_id=user_id,
                job_id=job_id,
                prompt=enhanced_prompt,
                original_prompt=prompt,
                parameters=validated_params,
                batch_count=batch_count,
                model_key=model_key,
            )
        elif mode == "replicate":
            if not self.replicate_client:
                raise RuntimeError(
                    "Replicate client not configured. "
                    "Set REPLICATE_API_TOKEN in environment."
                )
            return await self._generate_via_replicate(
                user_id=user_id,
                job_id=job_id,
                prompt=enhanced_prompt,
                original_prompt=prompt,
                parameters=validated_params,
                batch_count=batch_count,
                model_key=model_key,
                replicate_model=model_cfg["replicate_model"],
            )
        else:
            raise ValueError(f"Unknown generation mode: {mode}")

    # ------------------------------------------------------------------ #
    # Recraft via MCP bridge
    # ------------------------------------------------------------------ #
    async def _generate_recraft_via_mcp(
        self,
        user_id: int,
        job_id: int,
        prompt: str,
        original_prompt: str,
        parameters: Dict,
        batch_count: int,
        model_key: str,
    ) -> Dict:
        """Generate images using Recraft V3 via MCP HTTP bridge."""
        start_time = datetime.utcnow()
        
        args = {
            "prompt": prompt,
            "style": parameters.get("style", "realistic_image"),
            "model": parameters.get("model", self.RECRAFT_MODEL_DEFAULT),
            "n": batch_count,
        }
        
        logger.info(f"[IMAGE] Calling Recraft: style={args['style']}, n={args['n']}")
        
        result = await self._call_mcp_tool("recraft_generate_image", args)
        
        # Parse response flexibly (MCP bridge returns content array)
        images_data = result.get("content") or []
        urls: List[str] = []
        revised_prompts: List[str] = []
        
        for item in images_data:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    parsed = json.loads(item.get("text", "{}"))
                    if parsed.get("success"):
                        for img in parsed.get("images", []):
                            if img.get("url"):
                                urls.append(img["url"])
                                revised_prompts.append(img.get("revised_prompt", prompt))
                    else:
                        logger.error(f"[IMAGE] Recraft returned error: {parsed}")
                except json.JSONDecodeError as e:
                    logger.warning(f"[IMAGE] Failed to parse Recraft response: {e}")
            elif isinstance(item, dict) and item.get("url"):
                urls.append(item["url"])
                revised_prompts.append(item.get("revised_prompt", prompt))

        if not urls:
            raise RuntimeError("Recraft returned no images. Check API key and prompt.")

        # Calculate metrics
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        cost_per_image = self.MODEL_COSTS.get(model_key, 0.04)
        
        width = parameters.get("width", self.DEFAULT_WIDTH)
        height = parameters.get("height", self.DEFAULT_HEIGHT)
        
        # Store variants in database
        variants: List[Dict] = []
        for i, url in enumerate(urls):
            image_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
            
            variant = await db_manager.pool.fetchrow(
                """
                INSERT INTO image_variants (
                    job_id, user_id, version_number,
                    model_key, model_version,
                    original_prompt, enhanced_prompt,
                    parameters, cdn_url, thumbnail_url,
                    width, height, seed,
                    generation_time_ms, cost_usd, image_hash
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10,
                    $11, $12, $13, $14, $15, $16
                )
                RETURNING *
                """,
                job_id,
                user_id,
                i + 1,
                model_key,
                args["model"],
                original_prompt,
                revised_prompts[i] if i < len(revised_prompts) else parameters.get("enhanced_prompt"),
                json.dumps(parameters),
                url,
                url,  # Thumbnail same as main for now
                width,
                height,
                parameters.get("seed"),
                elapsed_ms,
                cost_per_image,
                image_hash,
            )
            variants.append(dict(variant))
        
        logger.info(f"[IMAGE] Recraft generated {len(variants)} variants in {elapsed_ms}ms")

        return {
            "job_id": job_id,
            "variants": variants,
            "count": len(variants),
            "model_key": model_key,
            "elapsed_ms": elapsed_ms,
            "total_cost_usd": cost_per_image * len(variants),
        }

    # ------------------------------------------------------------------ #
    # Gemini/Imagen-based generation
    # ------------------------------------------------------------------ #
    async def _generate_via_gemini(
        self,
        user_id: int,
        job_id: int,
        prompt: str,
        original_prompt: str,
        parameters: Dict,
        batch_count: int,
        model_key: str,
    ) -> Dict:
        """Generate images using Imagen 3 or legacy Gemini 3 Pro Image."""
        import time
        from app.integrations.alphawave_gemini import gemini_client
        from app.services.alphawave_cloudinary_service import cloudinary_service
        import base64
        
        start_time = time.time()
        model_cfg = self.MODEL_CONFIGS[model_key]
        
        # Get the actual Gemini model name
        gemini_model = model_cfg.get("gemini_model", "imagen-3.0-generate-001")
        
        # Get cost per image
        cost_config = model_cfg.get("cost_per_image")
        if isinstance(cost_config, dict):
            cost_per_image = cost_config.get(parameters.get("size", "1024x1024"), 0.134)
        else:
            cost_per_image = cost_config or 0.04
        
        variants = []
        
        # For Imagen 3, we can generate multiple images in one call
        is_imagen = gemini_model.startswith("imagen-3")
        
        if is_imagen:
            # Imagen 3 supports batch generation natively
            try:
                result = await gemini_client.generate_image(
                    prompt=prompt,
                    model=gemini_model,
                    aspect_ratio=parameters.get("aspect_ratio", "1:1"),
                    style=parameters.get("style"),
                    num_images=batch_count
                )
                
                if not result.get("success"):
                    logger.warning(f"[IMAGE] Imagen 3 generation failed: {result.get('error')}")
                    return {
                        "job_id": job_id,
                        "variants": [],
                        "count": 0,
                        "model_key": model_key,
                        "elapsed_ms": int((time.time() - start_time) * 1000),
                        "total_cost_usd": 0,
                        "error": result.get("error")
                    }
                
                # Process all generated images
                images = result.get("images", [])
                for i, img in enumerate(images):
                    try:
                        image_data = img.get("data")
                        if image_data:
                            # Upload to Cloudinary
                            upload_result = cloudinary_service.upload_from_base64(
                                image_data,
                                folder=f"image_gen/{user_id}",
                                public_id=f"imagen3_{job_id}_{i+1}"
                            )
                            url = upload_result.get("secure_url") or upload_result.get("url", "")
                        else:
                            continue
                        
                        # Get dimensions from aspect ratio
                        aspect = parameters.get("aspect_ratio", "1:1")
                        width, height = self.ASPECT_RATIOS.get(aspect, (1024, 1024))
                        
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        
                        # Store variant
                        variant = await db_manager.pool.fetchrow(
                            """
                            INSERT INTO image_variants (
                                job_id, user_id, version_number,
                                model_key, model_version,
                                original_prompt, enhanced_prompt,
                                parameters, cdn_url, thumbnail_url,
                                width, height, seed,
                                generation_time_ms, cost_usd, image_hash
                            ) VALUES (
                                $1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10,
                                $11, $12, $13, $14, $15, $16
                            )
                            RETURNING *
                            """,
                            job_id,
                            user_id,
                            i + 1,
                            model_key,
                            gemini_model,
                            original_prompt,
                            parameters.get("enhanced_prompt", prompt),
                            json.dumps(parameters),
                            url,
                            url,
                            width,
                            height,
                            None,  # No seed for Imagen
                            elapsed_ms,
                            cost_per_image,
                            None,
                        )
                        variants.append(dict(variant))
                        logger.info(f"[IMAGE] Imagen 3 variant {i+1}/{len(images)} uploaded")
                        
                    except Exception as e:
                        logger.error(f"[IMAGE] Failed to process Imagen 3 image {i+1}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"[IMAGE] Imagen 3 generation error: {e}", exc_info=True)
        else:
            # Legacy Gemini 3 Pro Image - generate one at a time
            for i in range(batch_count):
                try:
                    result = await gemini_client.generate_image(
                        prompt=prompt,
                        model=gemini_model,
                        aspect_ratio=parameters.get("aspect_ratio", "1:1"),
                        style=parameters.get("style"),
                        enable_thinking=False
                    )
                    
                    if not result.get("success"):
                        logger.warning(f"[IMAGE] Gemini generation {i+1} failed: {result.get('error')}")
                        continue
                    
                    # Upload to Cloudinary
                    image_data = result.get("image_data")
                    if image_data:
                        upload_result = cloudinary_service.upload_from_base64(
                            image_data,
                            folder=f"image_gen/{user_id}",
                            public_id=f"gemini_{job_id}_{i+1}"
                        )
                        url = upload_result.get("secure_url") or upload_result.get("url", "")
                    else:
                        url = ""
                    
                    # Get dimensions
                    aspect = parameters.get("aspect_ratio", "1:1")
                    width, height = self.ASPECT_RATIOS.get(aspect, (1024, 1024))
                    
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    
                    # Store variant
                    variant = await db_manager.pool.fetchrow(
                        """
                        INSERT INTO image_variants (
                            job_id, user_id, version_number,
                            model_key, model_version,
                            original_prompt, enhanced_prompt,
                            parameters, cdn_url, thumbnail_url,
                            width, height, seed,
                            generation_time_ms, cost_usd, image_hash
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10,
                            $11, $12, $13, $14, $15, $16
                        )
                        RETURNING *
                        """,
                        job_id,
                        user_id,
                        i + 1,
                        model_key,
                        gemini_model,
                        original_prompt,
                        parameters.get("enhanced_prompt", prompt),
                        json.dumps(parameters),
                        url,
                        url,
                        width,
                        height,
                        None,
                        elapsed_ms,
                        cost_per_image,
                        None,
                    )
                    variants.append(dict(variant))
                    
                except Exception as e:
                    logger.error(f"[IMAGE] Gemini generation {i+1} error: {e}", exc_info=True)
                    continue
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[IMAGE] Generated {len(variants)} variants in {elapsed_ms}ms using {gemini_model}")
        
        return {
            "job_id": job_id,
            "variants": variants,
            "count": len(variants),
            "model_key": model_key,
            "elapsed_ms": elapsed_ms,
            "total_cost_usd": cost_per_image * len(variants),
        }

    # ------------------------------------------------------------------ #
    # Replicate-based generation (Flux/Ideogram)
    # ------------------------------------------------------------------ #
    async def _generate_via_replicate(
        self,
        user_id: int,
        job_id: int,
        prompt: str,
        original_prompt: str,
        parameters: Dict,
        batch_count: int,
        model_key: str,
        replicate_model: str,
    ) -> Dict:
        """Generate images using Replicate API (FLUX, Ideogram)."""
        start_time = datetime.utcnow()
        variants: List[Dict] = []
        
        width = int(parameters.get("width", self.DEFAULT_WIDTH))
        height = int(parameters.get("height", self.DEFAULT_HEIGHT))
        cost_per_image = self.MODEL_COSTS.get(model_key, 0.05)
        
        logger.info(f"[IMAGE] Calling Replicate {replicate_model}: batch={batch_count}")

        # Build model-specific input params
        model_input = self._build_replicate_input(model_key, prompt, parameters)

        for i in range(batch_count):
            iter_start = datetime.utcnow()
            
            # Run prediction (offloaded to thread since replicate.run is blocking)
            prediction = await self._run_replicate(replicate_model, model_input)
            
            # Extract URL from response (format varies by model)
            # Replicate can return FileOutput objects, lists, or strings
            if isinstance(prediction, list):
                raw_output = prediction[0] if prediction else None
            elif isinstance(prediction, str):
                raw_output = prediction
            elif hasattr(prediction, 'output'):
                raw_output = prediction.output[0] if prediction.output else None
            else:
                raw_output = prediction
            
            # Convert FileOutput or other objects to string URL
            if raw_output is None:
                logger.error(f"[IMAGE] Replicate returned no output for iteration {i+1}")
                continue
            
            # Handle replicate.helpers.FileOutput - it has a url attribute or can be cast to str
            if hasattr(raw_output, 'url'):
                output_url = str(raw_output.url)
            elif hasattr(raw_output, 'read'):
                # It's a file-like object, get URL if available
                output_url = str(raw_output)
            else:
                output_url = str(raw_output)
            
            if not output_url or output_url == 'None':
                logger.error(f"[IMAGE] Replicate returned invalid output for iteration {i+1}: {type(raw_output)}")
                continue
            
            image_hash = hashlib.sha256(output_url.encode("utf-8")).hexdigest()[:12]
            elapsed_ms = int((datetime.utcnow() - iter_start).total_seconds() * 1000)

            variant = await db_manager.pool.fetchrow(
                """
                INSERT INTO image_variants (
                    job_id, user_id, version_number,
                    model_key, model_version,
                    original_prompt, enhanced_prompt,
                    parameters, cdn_url, thumbnail_url,
                    width, height, seed,
                    generation_time_ms, cost_usd, image_hash
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10,
                    $11, $12, $13, $14, $15, $16
                )
                RETURNING *
                """,
                job_id,
                user_id,
                i + 1,
                model_key,
                replicate_model,
                original_prompt,
                parameters.get("enhanced_prompt"),
                json.dumps(model_input),
                output_url,
                output_url,  # Thumbnail same as main for now
                width,
                height,
                model_input.get("seed"),
                elapsed_ms,
                cost_per_image,
                image_hash,
            )
            variants.append(dict(variant))
            logger.info(f"[IMAGE] Replicate variant {i+1}/{batch_count} completed in {elapsed_ms}ms")

        total_elapsed = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        logger.info(f"[IMAGE] Replicate generated {len(variants)} variants in {total_elapsed}ms")

        return {
            "job_id": job_id,
            "variants": variants,
            "count": len(variants),
            "model_key": model_key,
            "elapsed_ms": total_elapsed,
            "total_cost_usd": cost_per_image * len(variants),
        }

    def _build_replicate_input(self, model_key: str, prompt: str, parameters: Dict) -> Dict:
        """Build model-specific input dictionary for Replicate."""
        base_input = {"prompt": prompt}
        
        if model_key == "flux_pro":
            base_input.update({
                "aspect_ratio": parameters.get("aspect_ratio", "1:1"),
                "output_quality": parameters.get("output_quality", 100),
                "safety_tolerance": parameters.get("safety_tolerance", 2),
                "prompt_upsampling": True,
            })
            if "steps" in parameters:
                base_input["num_inference_steps"] = parameters["steps"]
            if "guidance" in parameters:
                base_input["guidance_scale"] = parameters["guidance"]
            if "seed" in parameters:
                base_input["seed"] = parameters["seed"]
                
        elif model_key == "flux_schnell":
            base_input.update({
                "aspect_ratio": parameters.get("aspect_ratio", "1:1"),
                "output_quality": parameters.get("output_quality", 90),
            })
            if "seed" in parameters:
                base_input["seed"] = parameters["seed"]
                
        elif model_key == "ideogram":
            base_input.update({
                "aspect_ratio": parameters.get("aspect_ratio", "1:1"),
                "style_type": parameters.get("style_type", "Auto"),
                "magic_prompt_option": parameters.get("magic_prompt_option", "Auto"),
            })
            if parameters.get("negative_prompt"):
                base_input["negative_prompt"] = parameters["negative_prompt"]
            if "seed" in parameters:
                base_input["seed"] = parameters["seed"]
        
        elif model_key == "seedream":
            # Seedream 4.5 by ByteDance
            base_input.update({
                "aspect_ratio": parameters.get("aspect_ratio", "1:1"),
                "num_outputs": 1,  # Seedream generates one at a time
            })
            if parameters.get("negative_prompt"):
                base_input["negative_prompt"] = parameters["negative_prompt"]
            if "seed" in parameters:
                base_input["seed"] = parameters["seed"]
        
        return base_input

    async def _run_replicate(self, model: str, params: Dict) -> Any:
        """Execute Replicate prediction (blocking call offloaded to thread)."""
        if not self.replicate_client:
            raise RuntimeError("Replicate client not configured. Set REPLICATE_API_TOKEN.")
        
        # replicate.run is synchronous - offload to thread pool
        return await asyncio.to_thread(
            self.replicate_client.run,
            model,
            input=params,
        )
    
    # ------------------------------------------------------------------ #
    # OpenAI GPT Image 1.5 generation
    # ------------------------------------------------------------------ #
    async def _generate_via_openai(
        self,
        user_id: int,
        job_id: int,
        prompt: str,
        original_prompt: str,
        parameters: Dict,
        batch_count: int,
        model_key: str,
    ) -> Dict:
        """Generate images using OpenAI's GPT Image 1.5 (or DALL-E 3)."""
        import time
        from app.services.alphawave_cloudinary_service import cloudinary_service
        
        if not self.openai_client:
            raise RuntimeError("OpenAI client not configured. Set OPENAI_API_KEY.")
        
        start_time = time.time()
        model_cfg = self.MODEL_CONFIGS[model_key]
        
        # Get model name
        openai_model = model_cfg.get("openai_model", settings.OPENAI_IMAGE_MODEL)
        cost_per_image = model_cfg.get("cost_per_image", 0.04)
        
        variants = []
        
        # Map aspect ratio to size
        aspect = parameters.get("aspect_ratio", "1:1")
        size_map = {
            "1:1": "1024x1024",
            "16:9": "1792x1024",
            "9:16": "1024x1792",
            "4:3": "1024x1024",  # OpenAI doesn't have 4:3, use square
            "3:4": "1024x1024",
        }
        size = size_map.get(aspect, "1024x1024")
        
        # Quality setting
        quality = parameters.get("quality", "hd")
        style = parameters.get("style", "vivid")
        
        logger.info(f"[IMAGE] Calling OpenAI {openai_model}: batch={batch_count}, size={size}")
        
        try:
            # GPT Image 1.5 supports n parameter
            urls = await self.openai_client.generate_image(
                prompt=prompt,
                model=openai_model,
                n=batch_count,
                quality=quality,
                size=size,
                style=style,
            )
            
            for i, url in enumerate(urls):
                try:
                    # Download and upload to Cloudinary
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(url)
                        image_bytes = resp.content
                    
                    import base64
                    image_b64 = base64.b64encode(image_bytes).decode()
                    
                    upload_result = cloudinary_service.upload_from_base64(
                        image_b64,
                        folder=f"image_gen/{user_id}",
                        public_id=f"openai_{job_id}_{i+1}"
                    )
                    cdn_url = upload_result.get("secure_url") or upload_result.get("url", url)
                    
                    # Parse dimensions from size
                    parts = size.split("x")
                    width = int(parts[0])
                    height = int(parts[1])
                    
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    
                    # Store variant
                    variant = await db_manager.pool.fetchrow(
                        """
                        INSERT INTO image_variants (
                            job_id, user_id, version_number,
                            model_key, model_version,
                            original_prompt, enhanced_prompt,
                            parameters, cdn_url, thumbnail_url,
                            width, height, seed,
                            generation_time_ms, cost_usd, image_hash
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10,
                            $11, $12, $13, $14, $15, $16
                        )
                        RETURNING *
                        """,
                        job_id,
                        user_id,
                        i + 1,
                        model_key,
                        openai_model,
                        original_prompt,
                        parameters.get("enhanced_prompt", prompt),
                        json.dumps(parameters),
                        cdn_url,
                        cdn_url,
                        width,
                        height,
                        None,  # No seed from OpenAI
                        elapsed_ms,
                        cost_per_image,
                        hashlib.sha256(url.encode()).hexdigest()[:12],
                    )
                    variants.append(dict(variant))
                    logger.info(f"[IMAGE] OpenAI variant {i+1}/{len(urls)} uploaded")
                    
                except Exception as e:
                    logger.error(f"[IMAGE] Failed to process OpenAI image {i+1}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"[IMAGE] OpenAI generation error: {e}", exc_info=True)
            return {
                "job_id": job_id,
                "variants": [],
                "count": 0,
                "model_key": model_key,
                "elapsed_ms": int((time.time() - start_time) * 1000),
                "total_cost_usd": 0,
                "error": str(e)
            }
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[IMAGE] OpenAI generated {len(variants)} variants in {elapsed_ms}ms")
        
        return {
            "job_id": job_id,
            "variants": variants,
            "count": len(variants),
            "model_key": model_key,
            "elapsed_ms": elapsed_ms,
            "total_cost_usd": cost_per_image * len(variants),
        }

    # ------------------------------------------------------------------ #
    # Utility methods for frontend/API
    # ------------------------------------------------------------------ #
    async def get_job(self, job_id: int, user_id: int) -> Optional[Dict]:
        """Fetch a single job with variant count."""
        row = await db_manager.pool.fetchrow(
            """
            SELECT j.*, COUNT(v.variant_id) as variant_count
            FROM image_jobs j
            LEFT JOIN image_variants v ON j.job_id = v.job_id
            WHERE j.job_id = $1 AND j.user_id = $2
            GROUP BY j.job_id
            """,
            job_id,
            user_id,
        )
        return dict(row) if row else None

    async def list_jobs(
        self,
        user_id: int,
        project: Optional[str] = None,
        use_case: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """List jobs with optional filters."""
        query = """
            SELECT j.*, COUNT(v.variant_id) as variant_count
            FROM image_jobs j
            LEFT JOIN image_variants v ON j.job_id = v.job_id
            WHERE j.user_id = $1
        """
        params = [user_id]
        
        if project:
            params.append(project)
            query += f" AND j.project = ${len(params)}"
        if use_case:
            params.append(use_case)
            query += f" AND j.use_case = ${len(params)}"
        
        query += " GROUP BY j.job_id ORDER BY j.updated_at DESC"
        params.append(limit)
        query += f" LIMIT ${len(params)}"
        
        rows = await db_manager.pool.fetch(query, *params)
        return [dict(r) for r in rows]

    async def get_variants(self, job_id: int, user_id: int) -> List[Dict]:
        """Fetch all variants for a job."""
        rows = await db_manager.pool.fetch(
            """
            SELECT * FROM image_variants
            WHERE job_id = $1 AND user_id = $2
            ORDER BY version_number ASC
            """,
            job_id,
            user_id,
        )
        return [dict(r) for r in rows]

    async def toggle_favorite(self, variant_id: int, user_id: int, is_favorite: bool) -> bool:
        """Toggle favorite status on a variant."""
        result = await db_manager.pool.execute(
            """
            UPDATE image_variants
            SET is_favorite = $1
            WHERE variant_id = $2 AND user_id = $3
            """,
            is_favorite,
            variant_id,
            user_id,
        )
        return "UPDATE 1" in result

    async def rate_variant(self, variant_id: int, user_id: int, rating: int) -> bool:
        """Set user rating (1-5) on a variant."""
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")
        result = await db_manager.pool.execute(
            """
            UPDATE image_variants
            SET user_rating = $1
            WHERE variant_id = $2 AND user_id = $3
            """,
            rating,
            variant_id,
            user_id,
        )
        return "UPDATE 1" in result

    async def list_presets(self, user_id: int) -> List[Dict]:
        """List presets (system + user-created)."""
        rows = await db_manager.pool.fetch(
            """
            SELECT * FROM image_presets
            WHERE user_id = $1 OR is_system = TRUE
            ORDER BY is_system DESC, created_at DESC
            """,
            user_id,
        )
        return [dict(r) for r in rows]

    async def get_preset(self, preset_key: str, user_id: int) -> Optional[Dict]:
        """Fetch a specific preset by key."""
        row = await db_manager.pool.fetchrow(
            """
            SELECT * FROM image_presets
            WHERE preset_key = $1 AND (user_id = $2 OR is_system = TRUE)
            """,
            preset_key,
            user_id,
        )
        return dict(row) if row else None

    async def create_preset(
        self,
        user_id: int,
        preset_key: str,
        name: str,
        model_key: str,
        parameters: Dict,
        batch_count: int = 1,
        use_case: Optional[str] = None,
        smart_prompt_enabled: bool = True,
    ) -> Dict:
        """Create a new user preset."""
        row = await db_manager.pool.fetchrow(
            """
            INSERT INTO image_presets (
                user_id, preset_key, name, model_key, parameters,
                batch_count, smart_prompt_enabled, use_case, is_system
            ) VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, FALSE)
            ON CONFLICT (user_id, preset_key) DO UPDATE SET
                name = EXCLUDED.name,
                model_key = EXCLUDED.model_key,
                parameters = EXCLUDED.parameters,
                batch_count = EXCLUDED.batch_count,
                smart_prompt_enabled = EXCLUDED.smart_prompt_enabled,
                use_case = EXCLUDED.use_case
            RETURNING *
            """,
            user_id,
            preset_key,
            name,
            model_key,
            json.dumps(parameters),
            batch_count,
            smart_prompt_enabled,
            use_case,
        )
        return dict(row)


# Global instance
image_service = ImageGenerationService()

