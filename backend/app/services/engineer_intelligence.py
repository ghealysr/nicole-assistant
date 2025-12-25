"""
Engineer Intelligence Service
==============================
Advanced verification, state tracking, and error pattern recognition
to prevent systematic deployment failures.

Implements:
- VerificationLoop: Verify file changes actually applied
- StateTracker: Track intended vs actual deployment state
- ErrorPatternRecognizer: Detect recurring errors
- CircuitBreaker: Stop deployment loops
- StatusCommunicator: Accurate, verified status messages

Based on lessons from Nuclear Marmalade deployment failure analysis.

Author: Nicole V7 Engineer Intelligence
Quality: Anthropic Engineering Standards
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from app.database import db

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONSTANTS
# ============================================================================

class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking deployments
    HALF_OPEN = "half_open"  # Testing recovery


class VerificationStatus(str, Enum):
    """Status of a file verification."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    MISMATCH = "mismatch"


# Maximum consecutive failures before circuit opens
MAX_CONSECUTIVE_FAILURES = 3

# Cooldown period when circuit is open
CIRCUIT_COOLDOWN_MINUTES = 15

# Minimum occurrences to consider an error "recurring"
RECURRING_ERROR_THRESHOLD = 2


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class FileState:
    """State of a single file."""
    filepath: str
    content_hash: str
    description: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass 
class VerificationResult:
    """Result of file verification."""
    filepath: str
    success: bool
    status: VerificationStatus
    message: str
    expected_hash: Optional[str] = None
    actual_hash: Optional[str] = None
    requires_retry: bool = False


@dataclass
class ErrorOccurrence:
    """A single error occurrence."""
    error_type: str
    detail: str
    file: Optional[str] = None
    line: Optional[int] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RecurringError:
    """An error that has occurred multiple times."""
    error: ErrorOccurrence
    occurrence_count: int
    first_seen: datetime
    last_seen: datetime
    diagnosis: str


@dataclass
class DeploymentAttempt:
    """Record of a deployment attempt."""
    deployment_id: str
    timestamp: datetime
    success: bool
    error_count: int
    claimed_fixes: List[str]
    log_hash: str


@dataclass
class CircuitBreakerState:
    """Current circuit breaker state."""
    is_open: bool
    state: CircuitState
    failure_count: int
    message: Optional[str] = None
    resume_at: Optional[datetime] = None
    can_proceed: bool = True


@dataclass
class PreflightResult:
    """Result of preflight audit."""
    passed: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    blocked: bool = False


@dataclass
class ParsedError:
    """Parsed error from build logs."""
    error_type: str
    error_detail: str
    file: Optional[str] = None
    line: Optional[int] = None
    suggested_fix: Optional[str] = None


# ============================================================================
# ERROR PATTERNS
# ============================================================================

# Known error patterns with regex for extraction
ERROR_PATTERNS = {
    "module_not_found": re.compile(
        r"Module not found: Can't resolve '([^']+)'", re.IGNORECASE
    ),
    "no_default_export": re.compile(
        r"([\w./]+) does not contain a default export", re.IGNORECASE
    ),
    "no_named_export": re.compile(
        r"'(\w+)' is not exported from '([^']+)'", re.IGNORECASE
    ),
    "type_error": re.compile(
        r"Type error: (.+?) at (.+?):(\d+):(\d+)", re.IGNORECASE
    ),
    "eslint_error": re.compile(
        r"ESLint: (.+?) \((.+?)\)", re.IGNORECASE
    ),
    "peer_dependency": re.compile(
        r"peer (.+?) from (.+?) requires (.+?),", re.IGNORECASE
    ),
    "react_server_component": re.compile(
        r"You're importing a component that needs (.+?) in a Server Component", re.IGNORECASE
    ),
    "use_client_missing": re.compile(
        r"'use client' directive", re.IGNORECASE
    ),
    "next_config_invalid": re.compile(
        r"Invalid next\.config\.(js|mjs|ts) options", re.IGNORECASE
    ),
    "build_failed": re.compile(
        r"Build failed|Build error|Exit code (\d+)", re.IGNORECASE
    ),
    "typescript_error": re.compile(
        r"error TS(\d+): (.+)", re.IGNORECASE
    ),
}


# ============================================================================
# BANNED PHRASES
# ============================================================================

# Phrases that should NOT be used until verification is complete
BANNED_UNTIL_VERIFIED = [
    "✅ COMPLETE",
    "🎉 SUCCESS",
    "100% CONFIDENCE",
    "DEPLOYMENT READY",
    "BUILD WILL SUCCEED",
    "ALL ISSUES RESOLVED",
    "SHOULD NOW WORK",
    "FIXED",
    "DONE",
    "GUARANTEED",
]

# Required qualifiers for unverified states
UNVERIFIED_QUALIFIERS = [
    "PENDING VERIFICATION",
    "AWAITING BUILD RESULT",
    "CHANGES APPLIED - VERIFICATION NEEDED",
    "FIX ATTEMPTED - CONFIRM IN NEXT BUILD",
]


# ============================================================================
# ENGINEER INTELLIGENCE SERVICE
# ============================================================================

class EngineerIntelligenceService:
    """
    Core intelligence service for defensive engineering.
    
    Prevents the systematic failures observed in production:
    1. False verification (claiming complete without checking)
    2. No state tracking (losing track of deployed vs planned)
    3. Reactive vs systematic (fixing one-by-one vs comprehensive)
    4. Invalid packages (adding non-existent npm packages)
    5. Premature success signaling (claiming success before verified)
    """
    
    def __init__(self):
        self._deployment_id: Optional[str] = None
        self._intended_state: Dict[str, FileState] = {}
        self._verified_state: Dict[str, FileState] = {}
        self._deployment_attempts: List[DeploymentAttempt] = []
        self._error_history: List[ErrorOccurrence] = []
    
    # ========================================================================
    # VERIFICATION LOOP
    # ========================================================================
    
    def compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    async def record_intended_change(
        self,
        project_id: int,
        filepath: str,
        content: str,
        description: str,
        deployment_id: Optional[str] = None
    ) -> str:
        """
        Record an intended file change.
        
        MUST be called BEFORE applying any file update.
        Returns the content hash for later verification.
        """
        content_hash = self.compute_hash(content)
        
        self._intended_state[filepath] = FileState(
            filepath=filepath,
            content_hash=content_hash,
            description=description,
        )
        
        # Persist to database
        try:
            await db.execute(
                """
                INSERT INTO enjineer_deployment_state 
                (project_id, deployment_id, filepath, intended_hash, intended_content_preview, 
                 change_description, verified, verification_attempts, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, FALSE, 0, NOW())
                ON CONFLICT (project_id, deployment_id, filepath)
                DO UPDATE SET 
                    intended_hash = EXCLUDED.intended_hash,
                    intended_content_preview = EXCLUDED.intended_content_preview,
                    change_description = EXCLUDED.change_description,
                    verified = FALSE,
                    verification_attempts = enjineer_deployment_state.verification_attempts + 1
                """,
                project_id,
                deployment_id or "pending",
                filepath,
                content_hash,
                content[:500],  # Preview for debugging
                description,
            )
        except Exception as e:
            logger.warning(f"[INTEL] Failed to record intended change: {e}")
        
        logger.info(f"[INTEL] Recorded intended: {filepath} ({content_hash[:8]}...)")
        return content_hash
    
    async def verify_change_applied(
        self,
        project_id: int,
        filepath: str,
        actual_content: str,
        deployment_id: Optional[str] = None
    ) -> VerificationResult:
        """
        Verify that an intended change was actually applied.
        
        MUST be called AFTER applying any file update.
        Compares actual content hash against intended hash.
        """
        actual_hash = self.compute_hash(actual_content)
        intended = self._intended_state.get(filepath)
        
        if not intended:
            # No intended state recorded - this is a warning
            logger.warning(f"[INTEL] No intended state for {filepath} - update not tracked")
            return VerificationResult(
                filepath=filepath,
                success=True,  # Can't verify, assume success
                status=VerificationStatus.PENDING,
                message="Change applied but was not tracked",
                actual_hash=actual_hash,
            )
        
        if actual_hash == intended.content_hash:
            # SUCCESS: Content matches
            self._verified_state[filepath] = FileState(
                filepath=filepath,
                content_hash=actual_hash,
                description=intended.description,
            )
            
            # Update database
            try:
                await db.execute(
                    """
                    UPDATE enjineer_deployment_state 
                    SET verified = TRUE, verified_hash = $1, verified_at = NOW()
                    WHERE project_id = $2 AND filepath = $3 
                      AND (deployment_id = $4 OR deployment_id = 'pending')
                    """,
                    actual_hash,
                    project_id,
                    filepath,
                    deployment_id or "pending",
                )
            except Exception as e:
                logger.warning(f"[INTEL] Failed to update verification: {e}")
            
            logger.info(f"[INTEL] ✅ Verified: {filepath}")
            return VerificationResult(
                filepath=filepath,
                success=True,
                status=VerificationStatus.VERIFIED,
                message=f"Change verified: {intended.description}",
                expected_hash=intended.content_hash,
                actual_hash=actual_hash,
            )
        else:
            # FAILURE: Content mismatch
            logger.error(
                f"[INTEL] ❌ MISMATCH: {filepath} - "
                f"expected {intended.content_hash[:8]}, got {actual_hash[:8]}"
            )
            return VerificationResult(
                filepath=filepath,
                success=False,
                status=VerificationStatus.MISMATCH,
                message=f"UPDATE FAILED TO APPLY: Content hash mismatch for {filepath}",
                expected_hash=intended.content_hash,
                actual_hash=actual_hash,
                requires_retry=True,
            )
    
    async def get_unverified_changes(
        self,
        project_id: int
    ) -> List[Dict[str, Any]]:
        """Get all changes that were intended but not verified."""
        unverified = []
        
        for filepath, intended in self._intended_state.items():
            if filepath not in self._verified_state:
                unverified.append({
                    "filepath": filepath,
                    "description": intended.description,
                    "hash": intended.content_hash,
                    "status": "unverified",
                })
            elif self._verified_state[filepath].content_hash != intended.content_hash:
                unverified.append({
                    "filepath": filepath,
                    "description": intended.description,
                    "expected_hash": intended.content_hash,
                    "actual_hash": self._verified_state[filepath].content_hash,
                    "status": "mismatch",
                })
        
        return unverified
    
    # ========================================================================
    # ERROR PATTERN RECOGNITION
    # ========================================================================
    
    def parse_deployment_log(self, log: str) -> List[ErrorOccurrence]:
        """
        Parse deployment log for error patterns.
        
        Extracts structured error information for tracking and analysis.
        """
        errors = []
        
        for error_type, pattern in ERROR_PATTERNS.items():
            for match in pattern.finditer(log):
                error = ErrorOccurrence(
                    error_type=error_type,
                    detail=match.group(0),
                    file=match.group(2) if match.lastindex >= 2 and error_type == "type_error" else None,
                    line=int(match.group(3)) if match.lastindex >= 3 and error_type == "type_error" else None,
                )
                errors.append(error)
        
        return errors
    
    async def record_errors(
        self,
        project_id: int,
        deployment_id: str,
        errors: List[ErrorOccurrence]
    ):
        """Record errors in database for pattern detection."""
        for error in errors:
            try:
                # Check if this error already exists
                existing = await db.fetchrow(
                    """
                    SELECT id, occurrence_count 
                    FROM enjineer_error_patterns
                    WHERE project_id = $1 
                      AND error_type = $2 
                      AND error_detail = $3
                      AND resolved = FALSE
                    """,
                    project_id,
                    error.error_type,
                    error.detail,
                )
                
                if existing:
                    # Increment occurrence count
                    await db.execute(
                        """
                        UPDATE enjineer_error_patterns 
                        SET occurrence_count = occurrence_count + 1,
                            last_seen = NOW(),
                            deployment_id = $1
                        WHERE id = $2
                        """,
                        deployment_id,
                        existing["id"],
                    )
                else:
                    # Insert new error
                    await db.execute(
                        """
                        INSERT INTO enjineer_error_patterns
                        (project_id, deployment_id, error_type, error_detail, 
                         error_file, error_line, occurrence_count, first_seen, last_seen)
                        VALUES ($1, $2, $3, $4, $5, $6, 1, NOW(), NOW())
                        """,
                        project_id,
                        deployment_id,
                        error.error_type,
                        error.detail,
                        error.file,
                        error.line,
                    )
            except Exception as e:
                logger.warning(f"[INTEL] Failed to record error: {e}")
    
    async def get_recurring_errors(
        self,
        project_id: int,
        min_occurrences: int = RECURRING_ERROR_THRESHOLD
    ) -> List[RecurringError]:
        """Get errors that have occurred multiple times."""
        try:
            rows = await db.fetch(
                """
                SELECT error_type, error_detail, occurrence_count, first_seen, last_seen
                FROM enjineer_error_patterns
                WHERE project_id = $1 
                  AND resolved = FALSE 
                  AND occurrence_count >= $2
                ORDER BY occurrence_count DESC, last_seen DESC
                """,
                project_id,
                min_occurrences,
            )
            
            recurring = []
            for row in rows:
                error = ErrorOccurrence(
                    error_type=row["error_type"],
                    detail=row["error_detail"],
                )
                recurring.append(RecurringError(
                    error=error,
                    occurrence_count=row["occurrence_count"],
                    first_seen=row["first_seen"],
                    last_seen=row["last_seen"],
                    diagnosis=self._diagnose_recurring_error(row["error_type"], row["error_detail"]),
                ))
            
            return recurring
        except Exception as e:
            logger.warning(f"[INTEL] Failed to get recurring errors: {e}")
            return []
    
    def _diagnose_recurring_error(self, error_type: str, detail: str) -> str:
        """Provide diagnosis for recurring error."""
        diagnoses = {
            "module_not_found": (
                f"Module keeps being reported as missing. Likely causes:\n"
                f"1. package.json updates not being deployed\n"
                f"2. Package name incorrect or doesn't exist in npm\n"
                f"3. Version specified is invalid\n"
                f"ACTION: Verify package exists in npm and is in package.json"
            ),
            "no_default_export": (
                f"Import/export mismatch recurring. The component uses named exports "
                f"but is being imported as default.\n"
                f"ACTION: Audit ALL import statements and use consistent export convention"
            ),
            "type_error": (
                f"TypeScript error keeps recurring. The fix is not being applied or "
                f"is incorrect.\n"
                f"ACTION: Read back the file after update to verify fix applied"
            ),
            "peer_dependency": (
                f"Peer dependency conflict recurring.\n"
                f"ACTION: Check package versions are compatible, especially for React"
            ),
        }
        return diagnoses.get(error_type, f"Error type '{error_type}' recurring. Previous fixes not effective.")
    
    # ========================================================================
    # SINGLE ERROR PARSING AND RECORDING
    # ========================================================================
    
    def parse_build_error(self, error_message: str) -> 'ParsedError':
        """
        Parse a single build error message into structured form.
        
        Returns:
            ParsedError with error_type, error_detail, file, line, and suggested_fix
        """
        error_message = error_message or ""
        
        for error_type, pattern in ERROR_PATTERNS.items():
            match = pattern.search(error_message)
            if match:
                # Extract file and line if available
                file_path = None
                line_number = None
                suggested_fix = None
                
                if error_type == "type_error" and match.lastindex >= 3:
                    file_path = match.group(2)
                    line_number = int(match.group(3)) if match.group(3).isdigit() else None
                    suggested_fix = f"Fix TypeScript error at {file_path}:{line_number}"
                elif error_type == "module_not_found":
                    module_name = match.group(1) if match.lastindex >= 1 else None
                    suggested_fix = f"Install missing module: npm install {module_name}" if module_name else None
                elif error_type == "no_default_export":
                    suggested_fix = "Use named import syntax: import {{ Component }} from 'path'"
                elif error_type == "eslint_error":
                    rule = match.group(2) if match.lastindex >= 2 else None
                    suggested_fix = f"Fix ESLint rule: {rule}" if rule else "Fix ESLint violation"
                elif error_type == "use_client_missing":
                    suggested_fix = "Add 'use client' directive at top of component file"
                elif error_type == "react_server_component":
                    suggested_fix = "Add 'use client' directive or move hook/effect to client component"
                
                return ParsedError(
                    error_type=error_type,
                    error_detail=match.group(0)[:200],
                    file=file_path,
                    line=line_number,
                    suggested_fix=suggested_fix,
                )
        
        # No pattern matched - return generic
        return ParsedError(
            error_type="unknown",
            error_detail=error_message[:200],
            file=None,
            line=None,
            suggested_fix=None,
        )
    
    async def record_error_pattern(
        self,
        project_id: int,
        deployment_id: str,
        error_type: str,
        error_detail: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ):
        """
        Record a single error pattern occurrence.
        
        Increments occurrence count if error already exists, otherwise creates new.
        """
        try:
            # Check if this error already exists
            existing = await db.fetchrow(
                """
                SELECT id, occurrence_count 
                FROM enjineer_error_patterns
                WHERE project_id = $1 
                  AND error_type = $2 
                  AND error_detail = $3
                  AND resolved = FALSE
                """,
                project_id,
                error_type,
                error_detail[:500],  # Truncate for storage
            )
            
            if existing:
                # Increment occurrence count
                await db.execute(
                    """
                    UPDATE enjineer_error_patterns 
                    SET occurrence_count = occurrence_count + 1,
                        last_seen = NOW(),
                        deployment_id = $1
                    WHERE id = $2
                    """,
                    deployment_id,
                    existing["id"],
                )
                logger.info(f"[INTEL] Incremented error count: {error_type} (now {existing['occurrence_count'] + 1})")
            else:
                # Insert new error
                await db.execute(
                    """
                    INSERT INTO enjineer_error_patterns
                    (project_id, deployment_id, error_type, error_detail, 
                     error_file, error_line, occurrence_count, first_seen, last_seen)
                    VALUES ($1, $2, $3, $4, $5, $6, 1, NOW(), NOW())
                    """,
                    project_id,
                    deployment_id,
                    error_type,
                    error_detail[:500],
                    file_path,
                    line_number,
                )
                logger.info(f"[INTEL] Recorded new error: {error_type}")
        except Exception as e:
            logger.warning(f"[INTEL] Failed to record error pattern: {e}")
    
    async def update_circuit_breaker(
        self,
        project_id: int,
        success: bool,
        error_count: int = 0,
    ):
        """
        Update circuit breaker based on deployment result.
        
        - Success: Reset failure count, close circuit
        - Failure: Increment failure count, potentially open circuit
        """
        try:
            if success:
                # Reset on success
                await self._update_circuit_state(
                    project_id,
                    CircuitState.CLOSED,
                    0,
                    None,
                    None
                )
                # Also mark errors resolved
                await self.mark_errors_resolved(project_id, resolution="Successful deployment")
                logger.info(f"[INTEL] ✅ Circuit breaker reset - successful deployment")
            else:
                # Increment failure count
                current = await self.check_circuit_breaker(project_id)
                new_count = current.failure_count + 1
                
                if new_count >= MAX_CONSECUTIVE_FAILURES:
                    reason = (
                        f"⚠️ DEPLOYMENT PAUSED: {new_count} consecutive failures.\n"
                        f"Errors in last deployment: {error_count}\n"
                        f"Review errors before retrying.\n"
                        f"Cooldown: {CIRCUIT_COOLDOWN_MINUTES} minutes."
                    )
                    resume_at = datetime.now(timezone.utc) + timedelta(minutes=CIRCUIT_COOLDOWN_MINUTES)
                    
                    await self._update_circuit_state(
                        project_id,
                        CircuitState.OPEN,
                        new_count,
                        reason,
                        resume_at
                    )
                    logger.warning(f"[INTEL] 🔴 Circuit breaker OPENED - {new_count} failures")
                else:
                    await self._update_circuit_state(
                        project_id,
                        CircuitState.CLOSED,
                        new_count,
                        f"{new_count} consecutive failures (opens at {MAX_CONSECUTIVE_FAILURES})",
                        None
                    )
                    logger.info(f"[INTEL] 🟡 Failure recorded: {new_count}/{MAX_CONSECUTIVE_FAILURES}")
        except Exception as e:
            logger.warning(f"[INTEL] Failed to update circuit breaker: {e}")
    
    async def mark_errors_resolved(
        self,
        project_id: int,
        error_type: Optional[str] = None,
        resolution: str = "Fixed in deployment"
    ):
        """Mark errors as resolved."""
        try:
            if error_type:
                await db.execute(
                    """
                    UPDATE enjineer_error_patterns 
                    SET resolved = TRUE, resolution_description = $1, resolved_at = NOW()
                    WHERE project_id = $2 AND error_type = $3 AND resolved = FALSE
                    """,
                    resolution,
                    project_id,
                    error_type,
                )
            else:
                await db.execute(
                    """
                    UPDATE enjineer_error_patterns 
                    SET resolved = TRUE, resolution_description = $1, resolved_at = NOW()
                    WHERE project_id = $2 AND resolved = FALSE
                    """,
                    resolution,
                    project_id,
                )
        except Exception as e:
            logger.warning(f"[INTEL] Failed to mark errors resolved: {e}")
    
    # ========================================================================
    # CIRCUIT BREAKER
    # ========================================================================
    
    async def check_circuit_breaker(
        self,
        project_id: int
    ) -> CircuitBreakerState:
        """
        Check if circuit breaker is open (blocking deployments).
        
        Opens after MAX_CONSECUTIVE_FAILURES failures.
        """
        try:
            # Get recent failures
            failure_count = await db.fetchval(
                """
                SELECT COUNT(*) FROM enjineer_deployment_attempts
                WHERE project_id = $1 
                  AND status = 'failed'
                  AND created_at > NOW() - INTERVAL '30 minutes'
                """,
                project_id,
            ) or 0
            
            # Check existing circuit state
            circuit = await db.fetchrow(
                """
                SELECT state, failure_count, reason, resume_at
                FROM enjineer_circuit_breaker
                WHERE project_id = $1
                """,
                project_id,
            )
            
            if circuit and circuit["state"] == "open":
                resume_at = circuit["resume_at"]
                if resume_at and resume_at > datetime.now(timezone.utc):
                    return CircuitBreakerState(
                        is_open=True,
                        state=CircuitState.OPEN,
                        failure_count=circuit["failure_count"],
                        message=circuit["reason"],
                        resume_at=resume_at,
                        can_proceed=False,
                    )
            
            if failure_count >= MAX_CONSECUTIVE_FAILURES:
                # Open circuit
                reason = (
                    f"⚠️ DEPLOYMENT PAUSED: {failure_count} consecutive failures.\n"
                    f"Review errors before retrying.\n"
                    f"Cooldown: {CIRCUIT_COOLDOWN_MINUTES} minutes or manual override."
                )
                resume_at = datetime.now(timezone.utc) + timedelta(minutes=CIRCUIT_COOLDOWN_MINUTES)
                
                await self._update_circuit_state(
                    project_id, 
                    CircuitState.OPEN, 
                    failure_count, 
                    reason,
                    resume_at
                )
                
                return CircuitBreakerState(
                    is_open=True,
                    state=CircuitState.OPEN,
                    failure_count=failure_count,
                    message=reason,
                    resume_at=resume_at,
                    can_proceed=False,
                )
            
            return CircuitBreakerState(
                is_open=False,
                state=CircuitState.CLOSED,
                failure_count=failure_count,
                can_proceed=True,
            )
            
        except Exception as e:
            logger.warning(f"[INTEL] Circuit breaker check failed: {e}")
            return CircuitBreakerState(
                is_open=False,
                state=CircuitState.CLOSED,
                failure_count=0,
                can_proceed=True,
            )
    
    async def _update_circuit_state(
        self,
        project_id: int,
        state: CircuitState,
        failure_count: int,
        reason: Optional[str],
        resume_at: Optional[datetime]
    ):
        """Update circuit breaker state in database."""
        try:
            await db.execute(
                """
                INSERT INTO enjineer_circuit_breaker 
                (project_id, state, failure_count, reason, resume_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (project_id) 
                DO UPDATE SET 
                    state = EXCLUDED.state,
                    failure_count = EXCLUDED.failure_count,
                    reason = EXCLUDED.reason,
                    resume_at = EXCLUDED.resume_at,
                    opened_at = CASE WHEN EXCLUDED.state = 'open' THEN NOW() ELSE enjineer_circuit_breaker.opened_at END,
                    updated_at = NOW()
                """,
                project_id,
                state.value,
                failure_count,
                reason,
                resume_at,
            )
        except Exception as e:
            logger.warning(f"[INTEL] Failed to update circuit state: {e}")
    
    async def reset_circuit_breaker(self, project_id: int):
        """Manually reset circuit breaker."""
        await self._update_circuit_state(
            project_id,
            CircuitState.CLOSED,
            0,
            None,
            None
        )
        logger.info(f"[INTEL] Circuit breaker reset for project {project_id}")
    
    # ========================================================================
    # DEPLOYMENT TRACKING
    # ========================================================================
    
    async def record_deployment_attempt(
        self,
        project_id: int,
        deployment_id: str,
        vercel_deployment_id: Optional[str],
        success: bool,
        error_count: int,
        claimed_fixes: List[str],
        log: Optional[str] = None
    ):
        """Record a deployment attempt."""
        try:
            status = "success" if success else "failed"
            log_hash = hashlib.sha256(log.encode()).hexdigest()[:16] if log else None
            
            await db.execute(
                """
                INSERT INTO enjineer_deployment_attempts
                (project_id, deployment_id, vercel_deployment_id, status, 
                 error_count, claimed_fixes, log_hash, created_at, completed_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                """,
                project_id,
                deployment_id,
                vercel_deployment_id,
                status,
                error_count,
                json.dumps(claimed_fixes),
                log_hash,
            )
            
            # If successful, mark errors resolved
            if success:
                await self.mark_errors_resolved(project_id, resolution="Successful deployment")
                await self.reset_circuit_breaker(project_id)
            
        except Exception as e:
            logger.warning(f"[INTEL] Failed to record deployment: {e}")
    
    # ========================================================================
    # STATUS COMMUNICATION
    # ========================================================================
    
    def format_status(
        self,
        action: str,
        verified: bool,
        unverified_changes: Optional[List[Dict]] = None
    ) -> str:
        """
        Format status message with appropriate confidence level.
        
        NEVER claims success for unverified changes.
        """
        unverified = unverified_changes or []
        
        if not verified or unverified:
            return (
                f"## Status: PENDING VERIFICATION\n\n"
                f"**Action Taken:** {action}\n\n"
                f"**Unverified Changes ({len(unverified)}):**\n"
                + "\n".join(f"- {c.get('filepath', 'unknown')}: {c.get('description', '')}" for c in unverified) +
                f"\n\n**Next Step:** Deploy and check build logs to verify fixes applied.\n"
                f"**DO NOT claim success until build log confirms resolution.**"
            )
        
        return (
            f"## Status: VERIFIED ✓\n\n"
            f"**Action:** {action}\n"
            f"**Verification:** All changes confirmed in build output.\n"
        )
    
    def check_banned_phrases(self, message: str) -> List[str]:
        """
        Check if message contains banned phrases.
        
        Returns list of violations found.
        """
        violations = []
        message_upper = message.upper()
        
        for phrase in BANNED_UNTIL_VERIFIED:
            if phrase.upper() in message_upper:
                violations.append(phrase)
        
        return violations
    
    # ========================================================================
    # PREFLIGHT AUDIT
    # ========================================================================
    
    async def run_preflight_audit(
        self,
        project_id: int,
        files: Dict[str, str],
        package_json: Optional[Dict] = None
    ) -> PreflightResult:
        """
        Run comprehensive preflight audit before deployment.
        
        Checks:
        1. Import/export consistency
        2. Package.json validity
        3. TypeScript compatibility
        4. Known anti-patterns
        """
        from app.services.npm_validator import npm_validator
        
        errors = []
        warnings = []
        recommendations = []
        
        # 1. Audit package.json if provided
        if package_json:
            audit = await npm_validator.audit_package_json(package_json)
            
            for invalid in audit.invalid_packages:
                errors.append(f"Invalid package: {invalid.package}@{invalid.version} - {invalid.error}")
            
            for conflict in audit.peer_conflicts:
                warnings.append(conflict)
            
            for react_warn in audit.react_19_warnings:
                warnings.append(f"React 19 compatibility: {react_warn}")
            
            recommendations.extend(audit.recommendations)
        
        # 2. Check import/export patterns
        import_errors = self._audit_imports(files)
        errors.extend(import_errors)
        
        # 3. Check for anti-patterns
        anti_pattern_warnings = self._check_anti_patterns(files)
        warnings.extend(anti_pattern_warnings)
        
        # 4. Store audit result
        passed = len(errors) == 0
        try:
            await db.execute(
                """
                INSERT INTO enjineer_preflight_audits
                (project_id, audit_type, passed, error_count, warning_count,
                 errors, warnings, recommendations, created_at)
                VALUES ($1, 'full', $2, $3, $4, $5, $6, $7, NOW())
                """,
                project_id,
                passed,
                len(errors),
                len(warnings),
                json.dumps(errors),
                json.dumps(warnings),
                json.dumps(recommendations),
            )
        except Exception as e:
            logger.warning(f"[INTEL] Failed to store preflight audit: {e}")
        
        return PreflightResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            recommendations=recommendations,
            blocked=len(errors) > 0,
        )
    
    def _audit_imports(self, files: Dict[str, str]) -> List[str]:
        """Audit import statements for common issues."""
        errors = []
        
        # Patterns to detect
        default_import = re.compile(r"import\s+(\w+)\s+from\s+['\"]([^'\"]+)['\"]")
        named_import = re.compile(r"import\s+\{\s*([^}]+)\s*\}\s+from\s+['\"]([^'\"]+)['\"]")
        
        for filepath, content in files.items():
            if not filepath.endswith(('.ts', '.tsx', '.js', '.jsx')):
                continue
            
            # Check for common import errors
            for match in default_import.finditer(content):
                imported_name, source = match.groups()
                
                # Check if importing default from a named-export-only file
                if source.startswith('.') or source.startswith('@/'):
                    # Local import - would need to check target file
                    pass
                elif source in ['react', 'next/link', 'next/image']:
                    # These have default exports, OK
                    pass
                elif source.startswith('@radix-ui/') or source.startswith('lucide-react'):
                    # These use named exports
                    errors.append(
                        f"{filepath}: Importing '{imported_name}' as default from '{source}' "
                        f"which uses named exports"
                    )
        
        return errors
    
    def _check_anti_patterns(self, files: Dict[str, str]) -> List[str]:
        """Check for known anti-patterns."""
        warnings = []
        
        anti_patterns = [
            (r"height:\s*100vh", "Avoid 100vh on mobile - use 100dvh or min-height"),
            (r"onClick.*href", "Avoid onClick with href - use Link component"),
            (r"style=\{\{", "Inline styles detected - prefer Tailwind classes"),
            (r"dangerouslySetInnerHTML", "dangerouslySetInnerHTML used - ensure sanitized"),
            (r"useEffect\(\s*\(\)\s*=>\s*\{[^}]*fetch", "Fetching in useEffect - consider useSWR or RSC"),
        ]
        
        for filepath, content in files.items():
            for pattern, message in anti_patterns:
                if re.search(pattern, content):
                    warnings.append(f"{filepath}: {message}")
        
        return warnings


# Global service instance
engineer_intelligence = EngineerIntelligenceService()

