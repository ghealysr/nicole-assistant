"""
Alphawave Image Generation Service

Goals:
- Unified API across models (Recraft via MCP bridge, FLUX/Ideogram via Replicate)
- Persist jobs/variants with metadata (cost, timing, seeds, parameters)
- Support batch generation and prompt enhancement hook (placeholder)
- Be robust to provider response shapes and validate inputs
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator, Any

import httpx

from app.config import settings
from app.database import db_manager

try:
    import replicate  # type: ignore
except ImportError:
    replicate = None


class ImageGenerationService:
    RECART_MODEL_DEFAULT = "recraftv3"
    DEFAULT_WIDTH = 1024
    DEFAULT_HEIGHT = 1024

    MODEL_COSTS = {
        "recraft": 0.05,      # per image (approx)
        "flux_pro": 0.05,
        "flux_schnell": 0.003,
        "ideogram": 0.08,
    }

    MODEL_CONFIGS = {
        "recraft": {
            "mode": "mcp",  # via MCP bridge tool
            "supports_batch": True,
        },
        "flux_pro": {
            "mode": "replicate",
            "replicate_model": "black-forest-labs/flux-1.1-pro",
            "supports_batch": False,
        },
        "flux_schnell": {
            "mode": "replicate",
            "replicate_model": "black-forest-labs/flux-schnell",
            "supports_batch": False,
        },
        "ideogram": {
            "mode": "replicate",
            "replicate_model": "ideogram-ai/ideogram-v2",
            "supports_batch": False,
        },
    }

    def __init__(self):
        self.gateway_url = getattr(settings, "MCP_GATEWAY_URL", "http://127.0.0.1:3100")
        self.client = httpx.AsyncClient(timeout=60.0)
        self.replicate_client = replicate.Client(api_token=settings.REPLICATE_API_TOKEN) if replicate else None

    async def shutdown(self):
        await self.client.aclose()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    async def _call_mcp_tool(self, name: str, arguments: Dict) -> Dict:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        resp = await self.client.post(f"{self.gateway_url}/rpc", json=payload)
        data = resp.json()
        if "error" in data:
            raise RuntimeError(data["error"].get("message", "Unknown MCP error"))
        return data.get("result", {})

    def _validate_batch(self, batch_count: int, supports_batch: bool) -> int:
        if supports_batch:
            return max(1, min(batch_count, 4))
        return max(1, batch_count)

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
    ) -> Dict:
        if model_key not in self.MODEL_CONFIGS:
            raise ValueError(f"Unsupported model_key: {model_key}")

        model_cfg = self.MODEL_CONFIGS[model_key]
        batch_count = self._validate_batch(batch_count, model_cfg.get("supports_batch", False))

        if job_id is None:
            title = f"{use_case or model_key} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            job = await self.create_job(user_id, title, project, use_case, preset_used)
            job_id = job["job_id"]

        if model_cfg["mode"] == "mcp":
            return await self._generate_recraft_via_mcp(
                user_id=user_id,
                job_id=job_id,
                prompt=prompt,
                parameters=parameters,
                batch_count=batch_count,
                model_key=model_key,
            )
        else:
            if not self.replicate_client:
                raise RuntimeError("Replicate client not configured")
            return await self._generate_via_replicate(
                user_id=user_id,
                job_id=job_id,
                prompt=prompt,
                parameters=parameters,
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
        parameters: Dict,
        batch_count: int,
        model_key: str,
    ) -> Dict:
        start_time = datetime.utcnow()
        args = {
            "prompt": prompt,
            "style": parameters.get("style", "realistic_image"),
            "model": parameters.get("model", self.RECART_MODEL_DEFAULT),
            "n": batch_count,
        }
        result = await self._call_mcp_tool("recraft_generate_image", args)
        images = result.get("content") or []
        urls: List[str] = []
        # Parse response flexibly
        for item in images:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    parsed = json.loads(item.get("text", "{}"))
                    for img in parsed.get("images", []):
                        if img.get("url"):
                            urls.append(img["url"])
                except Exception:
                    continue
            elif isinstance(item, dict) and item.get("url"):
                urls.append(item["url"])

        variants: List[Dict] = []
        width = parameters.get("width", self.DEFAULT_WIDTH)
        height = parameters.get("height", self.DEFAULT_HEIGHT)
        elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        cost_total = self.MODEL_COSTS.get(model_key, 0.0) * max(1, len(urls))

        version_number = 1
        for url in urls:
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
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16
                )
                RETURNING *
                """,
                job_id,
                user_id,
                version_number,
                model_key,
                parameters.get("model", self.RECART_MODEL_DEFAULT),
                prompt,
                parameters.get("enhanced_prompt"),
                parameters,
                url,
                url,  # thumbnail: same as main for now
                width,
                height,
                parameters.get("seed"),
                elapsed_ms,
                cost_total / max(1, len(urls)),
                image_hash,
            )
            variants.append(dict(variant))
            version_number += 1

        return {
            "job_id": job_id,
            "variants": variants,
            "count": len(variants),
            "model_key": model_key,
            "elapsed_ms": elapsed_ms,
        }

    # ------------------------------------------------------------------ #
    # Replicate-based generation (Flux/Ideogram)
    # ------------------------------------------------------------------ #
    async def _generate_via_replicate(
        self,
        user_id: int,
        job_id: int,
        prompt: str,
        parameters: Dict,
        batch_count: int,
        model_key: str,
        replicate_model: str,
    ) -> Dict:
        start_time = datetime.utcnow()
        variants: List[Dict] = []
        width = int(parameters.get("width", self.DEFAULT_WIDTH))
        height = int(parameters.get("height", self.DEFAULT_HEIGHT))
        cost_total = self.MODEL_COSTS.get(model_key, 0.0) * batch_count

        for i in range(batch_count):
            params = {**parameters, "prompt": prompt}
            prediction = await self._run_replicate(replicate_model, params)
            output_url = prediction[0] if isinstance(prediction, list) else prediction
            image_hash = hashlib.sha256(str(output_url).encode("utf-8")).hexdigest()[:12]
            elapsed_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

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
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                    $11, $12, $13, $14, $15, $16
                )
                RETURNING *
                """,
                job_id,
                user_id,
                i + 1,
                model_key,
                replicate_model,
                prompt,
                parameters.get("enhanced_prompt"),
                params,
                output_url,
                output_url,
                width,
                height,
                params.get("seed"),
                elapsed_ms,
                cost_total / max(1, batch_count),
                image_hash,
            )
            variants.append(dict(variant))

        return {
            "job_id": job_id,
            "variants": variants,
            "count": len(variants),
            "model_key": model_key,
            "elapsed_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
        }

    async def _run_replicate(self, model: str, params: Dict) -> Any:
        if not self.replicate_client:
            raise RuntimeError("Replicate client not configured")
        # replicate.run is blocking; offload to thread
        return await httpx.AsyncClient().run_in_threadpool(
            self.replicate_client.run,
            model,
            input=params,
        )


image_service = ImageGenerationService()

