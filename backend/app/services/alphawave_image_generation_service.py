"""
Alphawave Image Generation Service

Unified image generation across multiple providers:
- Recraft V3: Vector illustrations, logos, icons (via MCP bridge)
- FLUX Pro/Schnell: Photorealistic, fast iterations (via Replicate)
- Ideogram V2: Text rendering, design (via Replicate)

Features:
- Persistent jobs/variants with full metadata (cost, timing, seeds, parameters)
- Prompt enhancement via Claude
- Model-specific parameter validation and clamping
- Batch generation support
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

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


class ImageGenerationService:
    """
    Unified interface for all image generation models.
    
    Supports:
    - Recraft V3 (via MCP bridge): logos, icons, vectors
    - FLUX Pro (via Replicate): high-quality photorealistic
    - FLUX Schnell (via Replicate): fast iterations
    - Ideogram V2 (via Replicate): text rendering, design
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
        "imagen4": 0.04,  # Imagen 4 standard
        "imagen4_ultra": 0.06,  # Imagen 4 Ultra (higher precision)
        "gemini": 0.134,  # Legacy Gemini 3 Pro Image
    }

    # Model configurations with provider-specific settings
    MODEL_CONFIGS = {
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
        },
        "ideogram": {
            "name": "Ideogram V2",
            "mode": "replicate",
            "replicate_model": "ideogram-ai/ideogram-v2",
            "supports_batch": False,
            "default_params": {
                "aspect_ratio": "1:1",
                "style_type": "Auto",
                "magic_prompt_option": "Auto",
            },
            "style_types": ["Auto", "General", "Realistic", "Design", "Render 3D", "Anime"],
        },
        "imagen4": {
            "name": "Imagen 4",
            "mode": "gemini",
            "gemini_model": "imagen-4",
            "supports_batch": True,
            "max_batch": 4,
            "supports_thinking": False,
            "supports_image_input": True,
            "default_params": {
                "aspect_ratio": "1:1",
            },
            "aspect_ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"],
            "cost_per_image": 0.04,  # $0.04 per output image
        },
        "imagen4_ultra": {
            "name": "Imagen 4 Ultra",
            "mode": "gemini",
            "gemini_model": "imagen-4-ultra",
            "supports_batch": True,
            "max_batch": 4,
            "supports_thinking": False,
            "supports_image_input": True,
            "default_params": {
                "aspect_ratio": "1:1",
            },
            "aspect_ratios": ["1:1", "16:9", "9:16", "4:3", "3:4"],
            "cost_per_image": 0.06,  # $0.06 per output image (higher precision)
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
    }

    def __init__(self):
        self.gateway_url = getattr(settings, "MCP_GATEWAY_URL", "http://127.0.0.1:3100")
        self.client = httpx.AsyncClient(timeout=120.0)  # Increased for image gen
        
        # Initialize Replicate client
        replicate_token = getattr(settings, "REPLICATE_API_TOKEN", "")
        if replicate and replicate_token:
            self.replicate_client = replicate.Client(api_token=replicate_token)
            logger.info("[IMAGE] Replicate client initialized")
        else:
            self.replicate_client = None
            logger.warning("[IMAGE] Replicate client NOT configured (missing token or library)")
        
        # Initialize Anthropic client for prompt enhancement
        anthropic_key = getattr(settings, "ANTHROPIC_API_KEY", "")
        if AsyncAnthropic and anthropic_key:
            self.anthropic = AsyncAnthropic(api_key=anthropic_key)
            logger.info("[IMAGE] Anthropic client initialized for prompt enhancement")
        else:
            self.anthropic = None
            logger.warning("[IMAGE] Anthropic client NOT configured (prompt enhancement disabled)")

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

    async def enhance_prompt(
        self,
        original_prompt: str,
        model_key: str,
        use_case: Optional[str] = None,
    ) -> str:
        """
        Use Claude to enhance the prompt with model-specific optimizations.
        
        Returns enhanced prompt or original if enhancement fails/disabled.
        """
        if not self.anthropic:
            logger.debug("[IMAGE] Prompt enhancement skipped (no Anthropic client)")
            return original_prompt
        
        model_hints = {
            "recraft": "Recraft V3 excels at vector illustrations, logos, icons. Be specific about style, colors (hex codes), composition.",
            "flux_pro": "FLUX Pro creates photorealistic images. Include lighting, atmosphere, camera angle, subject details.",
            "flux_schnell": "FLUX Schnell is fast but lower detail. Keep prompts focused on key elements.",
            "ideogram": "Ideogram V2 handles text rendering well. If text is needed, specify exact wording in quotes.",
        }
        
        use_case_hints = {
            "logo": "Focus on clean lines, scalability, brand identity. Specify background (transparent if needed).",
            "hero": "Wide composition, dynamic lighting, professional quality, suitable for landing pages.",
            "social": "Eye-catching, centered subject, works at small sizes, vibrant colors.",
            "poster": "Dramatic composition, text placement areas, high contrast.",
            "icon": "Simple, recognizable at small sizes, minimal detail, clear silhouette.",
        }
        
        system = f"""You are an expert image generation prompt engineer.

Model being used: {model_key}
{model_hints.get(model_key, '')}

{f"Use case: {use_case}" if use_case else ""}
{use_case_hints.get(use_case, '') if use_case else ""}

Your task: Transform the user's prompt into an optimal technical prompt for {model_key}.

Rules:
1. Preserve the core intent and subject
2. Add technical details: composition, lighting, style, perspective
3. Be specific about colors (use hex codes when relevant)
4. Include quality markers appropriate for the model
5. Keep it under 500 characters
6. Output ONLY the enhanced prompt, no explanation or quotes"""

        try:
            response = await self.anthropic.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=300,
                system=system,
                messages=[{"role": "user", "content": original_prompt}],
            )
            enhanced = response.content[0].text.strip()
            logger.info(f"[IMAGE] Prompt enhanced: {len(original_prompt)} -> {len(enhanced)} chars")
            return enhanced
        except Exception as e:
            logger.warning(f"[IMAGE] Prompt enhancement failed: {e}")
            return original_prompt

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
        if model_cfg["mode"] == "mcp":
            return await self._generate_recraft_via_mcp(
                user_id=user_id,
                job_id=job_id,
                prompt=enhanced_prompt,
                original_prompt=prompt,
                parameters=validated_params,
                batch_count=batch_count,
                model_key=model_key,
            )
        elif model_cfg["mode"] == "gemini":
            return await self._generate_via_gemini(
                user_id=user_id,
                job_id=job_id,
                prompt=enhanced_prompt,
                original_prompt=prompt,
                parameters=validated_params,
                batch_count=batch_count,
                model_key=model_key,
            )
        else:
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
        """Generate images using Imagen 4 or legacy Gemini 3 Pro Image."""
        import time
        from app.integrations.alphawave_gemini import gemini_client
        from app.services.alphawave_cloudinary_service import cloudinary_service
        import base64
        
        start_time = time.time()
        model_cfg = self.MODEL_CONFIGS[model_key]
        
        # Get the actual Gemini model name
        gemini_model = model_cfg.get("gemini_model", "imagen-4")
        
        # Get cost per image
        cost_config = model_cfg.get("cost_per_image")
        if isinstance(cost_config, dict):
            cost_per_image = cost_config.get(parameters.get("size", "1024x1024"), 0.134)
        else:
            cost_per_image = cost_config or 0.04
        
        variants = []
        
        # For Imagen 4, we can generate multiple images in one call
        is_imagen4 = gemini_model.startswith("imagen-4")
        
        if is_imagen4:
            # Imagen 4 supports batch generation natively
            try:
                result = await gemini_client.generate_image(
                    prompt=prompt,
                    model=gemini_model,
                    aspect_ratio=parameters.get("aspect_ratio", "1:1"),
                    style=parameters.get("style"),
                    num_images=batch_count
                )
                
                if not result.get("success"):
                    logger.warning(f"[IMAGE] Imagen 4 generation failed: {result.get('error')}")
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
                                public_id=f"imagen4_{job_id}_{i+1}"
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
                        logger.info(f"[IMAGE] Imagen 4 variant {i+1}/{len(images)} uploaded")
                        
                    except Exception as e:
                        logger.error(f"[IMAGE] Failed to process Imagen 4 image {i+1}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"[IMAGE] Imagen 4 generation error: {e}", exc_info=True)
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
            if isinstance(prediction, list):
                output_url = prediction[0] if prediction else None
            elif isinstance(prediction, str):
                output_url = prediction
            elif hasattr(prediction, 'output'):
                output_url = prediction.output[0] if prediction.output else None
            else:
                output_url = str(prediction)
            
            if not output_url:
                logger.error(f"[IMAGE] Replicate returned no output for iteration {i+1}")
                continue
            
            image_hash = hashlib.sha256(str(output_url).encode("utf-8")).hexdigest()[:12]
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

