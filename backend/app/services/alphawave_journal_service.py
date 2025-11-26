"""
Journal Service for Nicole V7.
Handles daily journal entries, Nicole's responses, and pattern detection.

QA NOTES:
- Daily journals are user-specific (RLS enforced in Supabase)
- Nicole responds to journals at 11:59 PM via background worker
- Integrates with Spotify and HealthKit data when available
- Patterns are detected and stored for long-term memory
"""

import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.config import settings
from app.database import get_supabase
from app.integrations.alphawave_claude import claude_client

logger = logging.getLogger(__name__)


class AlphawaveJournalService:
    """
    Service for managing daily journal entries and Nicole's responses.
    
    Features:
    - Create/update daily journal entries
    - Generate Nicole's thoughtful responses
    - Integrate Spotify listening data
    - Integrate Apple HealthKit data
    - Detect patterns across entries
    """
    
    def __init__(self):
        """Initialize the journal service."""
        self.supabase = get_supabase()
    
    async def get_journal_entry(
        self,
        user_id: UUID,
        entry_date: date
    ) -> Optional[Dict[str, Any]]:
        """
        Get a journal entry for a specific date.
        
        Args:
            user_id: The user's UUID
            entry_date: The date of the entry
            
        Returns:
            Journal entry dict or None if not found
        """
        if not self.supabase:
            logger.error("Supabase not available")
            return None
        
        try:
            response = self.supabase.table("daily_journals").select("*").eq(
                "user_id", str(user_id)
            ).eq(
                "date", entry_date.isoformat()
            ).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error fetching journal entry: {e}", exc_info=True)
            return None
    
    async def get_recent_entries(
        self,
        user_id: UUID,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get recent journal entries for pattern analysis.
        
        Args:
            user_id: The user's UUID
            days: Number of days to look back (default 7)
            
        Returns:
            List of journal entries
        """
        if not self.supabase:
            logger.error("Supabase not available")
            return []
        
        try:
            start_date = (date.today() - timedelta(days=days)).isoformat()
            
            response = self.supabase.table("daily_journals").select("*").eq(
                "user_id", str(user_id)
            ).gte(
                "date", start_date
            ).order(
                "date", desc=True
            ).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error fetching recent entries: {e}", exc_info=True)
            return []
    
    async def create_or_update_entry(
        self,
        user_id: UUID,
        entry_date: date,
        user_entry: str,
        spotify_data: Optional[Dict[str, Any]] = None,
        health_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create or update a journal entry.
        
        Args:
            user_id: The user's UUID
            entry_date: The date of the entry
            user_entry: The user's journal text
            spotify_data: Optional Spotify listening data
            health_data: Optional HealthKit data
            
        Returns:
            The created/updated entry or None on error
            
        QA NOTE: Uses upsert to handle both create and update
        """
        if not self.supabase:
            logger.error("Supabase not available")
            return None
        
        try:
            entry_data = {
                "user_id": str(user_id),
                "date": entry_date.isoformat(),
                "user_entry": user_entry,
                "submitted_at": datetime.utcnow().isoformat()
            }
            
            # Add Spotify data if available
            if spotify_data:
                entry_data["spotify_top_artists"] = spotify_data.get("top_artists")
                entry_data["spotify_top_tracks"] = spotify_data.get("top_tracks")
                entry_data["spotify_listening_duration"] = spotify_data.get("duration_minutes")
            
            # Add health data if available
            if health_data:
                entry_data["health_steps"] = health_data.get("steps")
                entry_data["health_sleep_hours"] = health_data.get("sleep_hours")
                entry_data["health_heart_rate_avg"] = health_data.get("heart_rate_avg")
                entry_data["health_active_energy"] = health_data.get("active_energy")
            
            # Upsert the entry
            response = self.supabase.table("daily_journals").upsert(
                entry_data,
                on_conflict="user_id,date"
            ).execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Journal entry saved for user {user_id} on {entry_date}")
                return response.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error saving journal entry: {e}", exc_info=True)
            return None
    
    async def generate_nicole_response(
        self,
        user_id: UUID,
        entry_date: date,
        user_name: str = "friend"
    ) -> Optional[str]:
        """
        Generate Nicole's thoughtful response to a journal entry.
        
        Args:
            user_id: The user's UUID
            entry_date: The date of the entry
            user_name: The user's name for personalization
            
        Returns:
            Nicole's response text or None on error
            
        QA NOTE: Response is generated at 11:59 PM by background worker
        """
        # Get the journal entry
        entry = await self.get_journal_entry(user_id, entry_date)
        if not entry or not entry.get("user_entry"):
            logger.warning(f"No journal entry found for {user_id} on {entry_date}")
            return None
        
        # Get recent entries for context
        recent_entries = await self.get_recent_entries(user_id, days=7)
        
        # Build context from recent entries
        context_entries = []
        for past_entry in recent_entries[:5]:  # Last 5 entries
            if past_entry["date"] != entry_date.isoformat():
                context_entries.append({
                    "date": past_entry["date"],
                    "summary": past_entry.get("user_entry", "")[:200]
                })
        
        # Build the prompt
        system_prompt = f"""You are Nicole, a warm and caring AI companion responding to {user_name}'s daily journal entry.

Your response should:
1. Acknowledge their feelings and experiences with genuine empathy
2. Notice patterns or connections to previous days if relevant
3. Offer gentle encouragement or thoughtful reflections
4. Ask a meaningful follow-up question if appropriate
5. Keep your response conversational and warm (150-300 words)

Remember: You're their trusted friend, not a therapist. Be supportive but natural."""

        # Build user message with context
        user_message = f"Today's journal entry from {user_name}:\n\n{entry['user_entry']}"
        
        # Add Spotify context if available
        if entry.get("spotify_top_tracks"):
            user_message += f"\n\n[They listened to: {', '.join(entry['spotify_top_tracks'][:3])}]"
        
        # Add health context if available
        if entry.get("health_steps"):
            user_message += f"\n\n[Activity: {entry['health_steps']} steps"
            if entry.get("health_sleep_hours"):
                user_message += f", {entry['health_sleep_hours']} hours sleep"
            user_message += "]"
        
        # Add recent context
        if context_entries:
            user_message += "\n\n[Recent journal context:"
            for ctx in context_entries[:3]:
                user_message += f"\n- {ctx['date']}: {ctx['summary'][:100]}..."
            user_message += "]"
        
        try:
            # Generate response with Claude
            response = await claude_client.generate_response(
                messages=[{"role": "user", "content": user_message}],
                system_prompt=system_prompt,
                max_tokens=500,
                temperature=0.8
            )
            
            if response:
                # Save the response
                await self._save_nicole_response(user_id, entry_date, response)
                logger.info(f"Generated Nicole response for {user_id} on {entry_date}")
                return response
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating Nicole response: {e}", exc_info=True)
            return None
    
    async def _save_nicole_response(
        self,
        user_id: UUID,
        entry_date: date,
        response: str
    ) -> bool:
        """Save Nicole's response to the journal entry."""
        if not self.supabase:
            return False
        
        try:
            self.supabase.table("daily_journals").update({
                "nicole_response": response,
                "responded_at": datetime.utcnow().isoformat()
            }).eq(
                "user_id", str(user_id)
            ).eq(
                "date", entry_date.isoformat()
            ).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving Nicole response: {e}", exc_info=True)
            return False
    
    async def detect_patterns(
        self,
        user_id: UUID,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Detect patterns in journal entries over time.
        
        Args:
            user_id: The user's UUID
            days: Number of days to analyze (default 30)
            
        Returns:
            List of detected patterns
            
        QA NOTE: Patterns are stored in life_story_entries table
        """
        entries = await self.get_recent_entries(user_id, days)
        
        if len(entries) < 5:
            logger.info(f"Not enough entries for pattern detection ({len(entries)} entries)")
            return []
        
        patterns = []
        
        # Analyze mood patterns (simple keyword analysis)
        mood_keywords = {
            "positive": ["happy", "great", "wonderful", "excited", "grateful", "love"],
            "negative": ["sad", "tired", "stressed", "anxious", "worried", "frustrated"],
            "neutral": ["okay", "fine", "normal", "usual", "regular"]
        }
        
        mood_counts = {"positive": 0, "negative": 0, "neutral": 0}
        
        for entry in entries:
            text = (entry.get("user_entry") or "").lower()
            for mood, keywords in mood_keywords.items():
                if any(kw in text for kw in keywords):
                    mood_counts[mood] += 1
        
        # Identify dominant mood
        total = sum(mood_counts.values())
        if total > 0:
            for mood, count in mood_counts.items():
                percentage = (count / total) * 100
                if percentage > 40:
                    patterns.append({
                        "type": "mood_pattern",
                        "pattern": mood,
                        "confidence": percentage / 100,
                        "description": f"Your entries have been predominantly {mood} ({percentage:.0f}% of entries)"
                    })
        
        # Analyze activity patterns (from health data)
        steps_data = [e.get("health_steps") for e in entries if e.get("health_steps")]
        if steps_data:
            avg_steps = sum(steps_data) / len(steps_data)
            if avg_steps > 10000:
                patterns.append({
                    "type": "activity_pattern",
                    "pattern": "high_activity",
                    "confidence": 0.8,
                    "description": f"You've been very active! Average of {avg_steps:.0f} steps per day"
                })
            elif avg_steps < 5000:
                patterns.append({
                    "type": "activity_pattern",
                    "pattern": "low_activity",
                    "confidence": 0.7,
                    "description": f"Activity has been lower lately. Average of {avg_steps:.0f} steps per day"
                })
        
        # Analyze sleep patterns
        sleep_data = [e.get("health_sleep_hours") for e in entries if e.get("health_sleep_hours")]
        if sleep_data:
            avg_sleep = sum(sleep_data) / len(sleep_data)
            if avg_sleep < 6:
                patterns.append({
                    "type": "sleep_pattern",
                    "pattern": "sleep_deficit",
                    "confidence": 0.85,
                    "description": f"You might need more rest. Averaging {avg_sleep:.1f} hours of sleep"
                })
        
        logger.info(f"Detected {len(patterns)} patterns for user {user_id}")
        return patterns
    
    async def get_all_entries(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all journal entries for a user with pagination.
        
        Args:
            user_id: The user's UUID
            limit: Maximum entries to return
            offset: Number of entries to skip
            
        Returns:
            List of journal entries
        """
        if not self.supabase:
            return []
        
        try:
            response = self.supabase.table("daily_journals").select("*").eq(
                "user_id", str(user_id)
            ).order(
                "date", desc=True
            ).range(
                offset, offset + limit - 1
            ).execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"Error fetching all entries: {e}", exc_info=True)
            return []


# Global service instance
journal_service = AlphawaveJournalService()

