"""
Image Generation Memory Service

Persists user preferences, successful patterns, and context for Nicole's understanding.
Enables learning across generations to improve future results.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from app.database import db
from app.integrations.alphawave_openai import openai_client

logger = logging.getLogger(__name__)


class ImageGenerationMemoryService:
    """
    Manages memory and learning for image generation system.
    
    Features:
    - Save generation preferences and patterns
    - Track model performance by use case
    - Store user feedback and approvals
    - Provide context to Nicole for improved assistance
    """
    
    async def save_generation_memory(
        self,
        user_id: int,
        job_id: int,
        prompt: str,
        enhanced_prompt: str,
        model_used: str,
        task_analysis: Dict[str, Any],
        quality_evaluation: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None,
        reference_images: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Save generation context to memory system.
        
        Args:
            user_id: User ID
            job_id: Image generation job ID
            prompt: Original user prompt
            enhanced_prompt: AI-enhanced prompt used for generation
            model_used: Model that generated the image
            task_analysis: Output from Task Analyzer agent
            quality_evaluation: Output from Quality Router agent
            user_feedback: Optional user feedback (approval, edits, rejection)
            reference_images: Optional list of reference images with inspiration notes
            
        Returns:
            Success status
        """
        try:
            # Create memory entry
            memory_text = self._build_memory_text(
                prompt=prompt,
                enhanced_prompt=enhanced_prompt,
                model_used=model_used,
                task_analysis=task_analysis,
                quality_evaluation=quality_evaluation,
                user_feedback=user_feedback,
                reference_images=reference_images
            )
            
            # Generate embedding for semantic search
            embedding = await openai_client.generate_embedding(memory_text)
            
            # Save to memory_entries table
            memory_id = await db.execute(
                """
                INSERT INTO memory_entries (
                    user_id,
                    memory_text,
                    embedding,
                    memory_type,
                    metadata,
                    created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                user_id,
                memory_text,
                embedding,
                "image_generation",
                json.dumps({
                    "job_id": job_id,
                    "model_used": model_used,
                    "complexity": task_analysis.get("complexity"),
                    "style_preference": task_analysis.get("style_preference"),
                    "quality_score": quality_evaluation.get("overall_score"),
                    "user_approved": user_feedback.get("approved") if user_feedback else None
                }),
                datetime.utcnow()
            )
            
            logger.info(f"[IMAGE_MEMORY] Saved memory {memory_id} for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"[IMAGE_MEMORY] Failed to save memory for job {job_id}: {e}", exc_info=True)
            return False
    
    def _build_memory_text(
        self,
        prompt: str,
        enhanced_prompt: str,
        model_used: str,
        task_analysis: Dict[str, Any],
        quality_evaluation: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]],
        reference_images: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Build semantic memory text for embedding."""
        
        parts = [
            f"Image Generation Request: {prompt}",
            f"Model Used: {model_used}",
            f"Complexity: {task_analysis.get('complexity', 'unknown')}",
            f"Style: {task_analysis.get('style_preference', 'unknown')}",
            f"Quality Score: {quality_evaluation.get('overall_score', 0)}/10"
        ]
        
        if reference_images:
            ref_notes = [img.get("inspiration_notes", "") for img in reference_images if img.get("inspiration_notes")]
            if ref_notes:
                parts.append(f"Reference Image Notes: {' | '.join(ref_notes)}")
        
        if user_feedback:
            if user_feedback.get("approved"):
                parts.append("User Feedback: Approved")
            elif user_feedback.get("rejected"):
                parts.append(f"User Feedback: Rejected - {user_feedback.get('reason', 'no reason')}")
            elif user_feedback.get("edits_requested"):
                parts.append(f"User Feedback: Requested edits - {user_feedback.get('edit_notes', '')}")
        
        return " | ".join(parts)
    
    async def get_relevant_context(
        self,
        user_id: int,
        current_prompt: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant past generations for context.
        
        Args:
            user_id: User ID
            current_prompt: Current generation prompt (for semantic search)
            limit: Max number of relevant memories to return
            
        Returns:
            List of relevant memory entries
        """
        try:
            # Generate embedding for current prompt
            query_embedding = await openai_client.generate_embedding(current_prompt)
            
            # Semantic search for similar past generations
            results = await db.fetch(
                """
                SELECT 
                    id,
                    memory_text,
                    metadata,
                    created_at,
                    1 - (embedding <=> $1::vector) AS similarity
                FROM memory_entries
                WHERE user_id = $2
                    AND memory_type = 'image_generation'
                    AND embedding IS NOT NULL
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                query_embedding,
                user_id,
                limit
            )
            
            memories = []
            for row in results:
                metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                memories.append({
                    "id": row["id"],
                    "text": row["memory_text"],
                    "metadata": metadata,
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    "similarity": float(row["similarity"]) if row["similarity"] else 0.0
                })
            
            logger.info(f"[IMAGE_MEMORY] Retrieved {len(memories)} relevant memories for user {user_id}")
            return memories
            
        except Exception as e:
            logger.error(f"[IMAGE_MEMORY] Failed to retrieve context for user {user_id}: {e}", exc_info=True)
            return []
    
    async def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """
        Analyze user's past generations to extract preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with user preferences (favorite models, styles, quality standards)
        """
        try:
            # Get all user's image generation memories
            results = await db.fetch(
                """
                SELECT metadata
                FROM memory_entries
                WHERE user_id = $1
                    AND memory_type = 'image_generation'
                    AND metadata IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 50
                """,
                user_id
            )
            
            if not results:
                return {
                    "has_history": False,
                    "total_generations": 0
                }
            
            # Analyze patterns
            models_used = {}
            styles_preferred = {}
            complexities = {}
            approved_count = 0
            total_count = len(results)
            quality_scores = []
            
            for row in results:
                metadata = json.loads(row["metadata"])
                
                # Track model usage
                model = metadata.get("model_used")
                if model:
                    models_used[model] = models_used.get(model, 0) + 1
                
                # Track style preferences
                style = metadata.get("style_preference")
                if style:
                    styles_preferred[style] = styles_preferred.get(style, 0) + 1
                
                # Track complexities
                complexity = metadata.get("complexity")
                if complexity:
                    complexities[complexity] = complexities.get(complexity, 0) + 1
                
                # Track approvals
                if metadata.get("user_approved"):
                    approved_count += 1
                
                # Track quality scores
                quality = metadata.get("quality_score")
                if quality:
                    quality_scores.append(quality)
            
            # Calculate averages and favorites
            favorite_model = max(models_used, key=models_used.get) if models_used else None
            favorite_style = max(styles_preferred, key=styles_preferred.get) if styles_preferred else None
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
            approval_rate = (approved_count / total_count) if total_count > 0 else 0
            
            preferences = {
                "has_history": True,
                "total_generations": total_count,
                "favorite_model": favorite_model,
                "model_usage": models_used,
                "favorite_style": favorite_style,
                "style_preferences": styles_preferred,
                "complexity_distribution": complexities,
                "approval_rate": approval_rate,
                "average_quality_score": avg_quality
            }
            
            logger.info(f"[IMAGE_MEMORY] Analyzed preferences for user {user_id}: {approval_rate:.1%} approval rate")
            return preferences
            
        except Exception as e:
            logger.error(f"[IMAGE_MEMORY] Failed to analyze preferences for user {user_id}: {e}", exc_info=True)
            return {"has_history": False, "error": str(e)}
    
    async def save_user_feedback(
        self,
        user_id: int,
        job_id: int,
        feedback_type: str,  # "approved", "rejected", "edited"
        feedback_data: Dict[str, Any]
    ) -> bool:
        """
        Save explicit user feedback on a generation.
        
        Args:
            user_id: User ID
            job_id: Image job ID
            feedback_type: Type of feedback
            feedback_data: Feedback details (reason, edits, rating, etc.)
            
        Returns:
            Success status
        """
        try:
            # Update job metadata with feedback
            await db.execute(
                """
                UPDATE image_jobs
                SET metadata = jsonb_set(
                    COALESCE(metadata, '{}'::jsonb),
                    '{feedback}',
                    $1::jsonb
                )
                WHERE id = $2 AND user_id = $3
                """,
                json.dumps({
                    "type": feedback_type,
                    "data": feedback_data,
                    "timestamp": datetime.utcnow().isoformat()
                }),
                job_id,
                user_id
            )
            
            # Update corresponding memory entry
            await db.execute(
                """
                UPDATE memory_entries
                SET metadata = jsonb_set(
                    COALESCE(metadata, '{}'::jsonb),
                    '{user_feedback}',
                    $1::jsonb
                )
                WHERE user_id = $2
                    AND memory_type = 'image_generation'
                    AND (metadata->>'job_id')::int = $3
                """,
                json.dumps({"type": feedback_type, **feedback_data}),
                user_id,
                job_id
            )
            
            logger.info(f"[IMAGE_MEMORY] Saved {feedback_type} feedback for job {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"[IMAGE_MEMORY] Failed to save feedback for job {job_id}: {e}", exc_info=True)
            return False


# Global service instance
image_memory_service = ImageGenerationMemoryService()

