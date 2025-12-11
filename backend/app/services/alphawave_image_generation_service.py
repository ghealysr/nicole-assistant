"""
Alphawave Image Generation Service (Recraft-first, MCP bridge)

Minimal implementation that:
- Calls the MCP HTTP bridge tool `recraft_generate_image`
- Stores generated variants in image_variants table
- Creates jobs if needed via helper

Note: This is synchronous (no SSE) and focuses on Recraft. Extend to FLUX/Ideogram later.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional

import httpx
from datetime import datetime

from app.config import settings
from app.database import db_manager


class ImageGenerationService:
    RECART_MODEL_DEFAULT = "recraftv3"
    DEFAULT_WIDTH = 1024
    DEFAULT_HEIGHT = 1024
    MODEL_COSTS = {
        "recraft": 0.05,
        "flux_pro": 0.05,
        "flux_schnell": 0.003,
        "ideogram": 0.08,
    }

    def __init__(self):
        self.gateway_url = getattr(settings, "MCP_GATEWAY_URL", "http://127.0.0.1:3100")
        self.client = httpx.AsyncClient(timeout=60.0)

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
        if model_key != "recraft":
            raise ValueError("Currently only 'recraft' is supported in this bridge-based path.")

        if job_id is None:
            title = f"{use_case or model_key} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
            job = await self.create_job(user_id, title, project, use_case, preset_used)
            job_id = job["job_id"]

        variants: List[Dict] = []
        # Clamp batch count 1-4
        n = max(1, min(batch_count, 4))

        recraft_args = {
            "prompt": prompt,
            "style": parameters.get("style", "realistic_image"),
            "model": parameters.get("model", self.RECART_MODEL_DEFAULT),
            "n": n,
        }

        result = await self._call_mcp_tool("recraft_generate_image", recraft_args)
        images = result.get("content") or []
        # result.content is list of {type:"text", text: json}; parse if needed
        urls: List[str] = []
        for item in images:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    import json

                    parsed = json.loads(item.get("text", "{}"))
                    for img in parsed.get("images", []):
                        if img.get("url"):
                            urls.append(img["url"])
                except Exception:
                    continue

        # Fallback: if already structured
        if not urls:
            for item in images:
                if isinstance(item, dict) and item.get("url"):
                    urls.append(item["url"])

        now = datetime.utcnow()
        width = parameters.get("width", self.DEFAULT_WIDTH)
        height = parameters.get("height", self.DEFAULT_HEIGHT)
        cost = self.MODEL_COSTS.get(model_key, 0.0) * max(1, len(urls))

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
                url,  # thumbnail same as main for now
                width,
                height,
                parameters.get("seed"),
                0,  # generation_time_ms unknown in this path
                cost / max(1, len(urls)),
                image_hash,
            )
            variants.append(dict(variant))
            version_number += 1

        return {
            "job_id": job_id,
            "variants": variants,
            "count": len(variants),
            "model_key": model_key,
        }


image_service = ImageGenerationService()

