"""
Nicole V7 - Google OAuth Authentication Middleware

Verifies Google OAuth ID tokens and attaches user context to request state.
Replaces Supabase JWT verification with Google's secure token verification.

ACCESS CONTROL:
- Only allows emails from configured domains (e.g., @alphawavetech.com)
- Or specific emails in the allowlist (e.g., personal Gmail)
- All other Google accounts are rejected

Author: Nicole V7 Architecture
Date: December 2025
"""

import uuid
import logging
import time
import re
from typing import Callable, Optional, Dict, Any, Set

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.config import settings
from app.services.tiger_user_service import tiger_user_service

logger = logging.getLogger(__name__)

# CORS origins for error responses
CORS_ORIGINS = [
    "https://nicole.alphawavetech.com",
    "https://nicole.alphawavelabs.io",
    "https://nicole-v7.vercel.app",
    "https://nicole-assistant-yyr5.vercel.app",
    "https://ghealysr-nicole-assistant-yyr5.vercel.app",
    "http://localhost:3000",
]

# Regex pattern for Vercel preview deployments (matches both naming patterns)
CORS_ORIGIN_REGEX = re.compile(r"https://(nicole-assistant|ghealysr-nicole-assistant).*\.vercel\.app")


def add_cors_headers(response: JSONResponse, request: Request) -> JSONResponse:
    """Add CORS headers to error responses."""
    origin = request.headers.get("origin", "")
    if origin in CORS_ORIGINS or CORS_ORIGIN_REGEX.match(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


# Public paths that don't require authentication
PUBLIC_PATHS = {
    "/healthz",
    "/health/check",
    "/health/ping",
    "/health/system",
    "/health/mcp",
    "/auth/login",
    "/images/models",
    "/images/presets",
    "/claude-skills",
    "/claude-skills/categories",
    "/claude-skills/search",
    "/claude-skills/summary",
    "/auth/callback",
    "/auth/logout",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# Paths that require admin role
ADMIN_PATHS = {
    "/admin",
    "/users",
    "/system",
}


def _get_allowed_domains() -> Set[str]:
    """Get set of allowed email domains from config."""
    domains = settings.GOOGLE_ALLOWED_DOMAINS or ""
    return {d.strip().lower() for d in domains.split(",") if d.strip()}


def _get_allowed_emails() -> Set[str]:
    """Get set of specifically allowed email addresses from config."""
    emails = settings.GOOGLE_ALLOWED_EMAILS or ""
    return {e.strip().lower() for e in emails.split(",") if e.strip()}


def _is_email_allowed(email: str) -> bool:
    """
    Check if email is allowed to access Nicole.
    
    Allowed if:
    - Email domain is in GOOGLE_ALLOWED_DOMAINS
    - Email is specifically in GOOGLE_ALLOWED_EMAILS
    """
    if not email:
        return False
    
    email_lower = email.lower()
    
    # Check specific emails first
    allowed_emails = _get_allowed_emails()
    if email_lower in allowed_emails:
        return True
    
    # Check domain
    allowed_domains = _get_allowed_domains()
    if allowed_domains:
        domain = email_lower.split("@")[-1] if "@" in email_lower else ""
        if domain in allowed_domains:
            return True
    
    return False


def get_current_user_id(request: Request) -> Optional[str]:
    """Helper to get current user id from request state if available."""
    return getattr(request.state, "user_id", None)


def get_current_user_role(request: Request) -> Optional[str]:
    """Helper to get current user role from request state if available."""
    return getattr(request.state, "user_role", None)


def get_current_tiger_user_id(request: Request) -> Optional[int]:
    """Helper to get Tiger Postgres user_id from request state."""
    return getattr(request.state, "tiger_user_id", None)


async def get_current_user(request: Request):
    """
    FastAPI dependency to get the current authenticated user.
    
    Returns a user object with user_id and other attributes from request state.
    Raises HTTPException if user is not authenticated.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(user = Depends(get_current_user)):
            print(user.user_id, user.email)
    """
    tiger_user_id = getattr(request.state, "tiger_user_id", None)
    
    if not tiger_user_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    
    # Return a simple namespace object with user attributes
    class UserContext:
        def __init__(self):
            self.user_id = tiger_user_id
            self.google_id = getattr(request.state, "user_id", None)
            self.email = getattr(request.state, "user_email", None)
            self.name = getattr(request.state, "user_name", None)
            self.role = getattr(request.state, "user_role", "standard")
            self.picture = getattr(request.state, "user_picture", None)
    
    return UserContext()


def get_correlation_id(request: Request) -> str:
    """Helper to get correlation ID from request state."""
    return getattr(request.state, "correlation_id", "unknown")


async def verify_jwt(request: Request, call_next: Callable):
    """
    Google OAuth ID token verification middleware.
    
    Validates Google ID tokens and attaches user context to request state.
    Only allows users from configured domains or specific email allowlist.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response from next middleware/endpoint
    """
    start_time = time.time()
    correlation_id = str(uuid.uuid4())
    request.state.correlation_id = correlation_id

    try:
        # Allow CORS preflight requests
        if request.method == "OPTIONS":
            response = await call_next(request)
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response

        # Skip authentication for public paths
        if request.url.path in PUBLIC_PATHS:
            logger.debug(f"[{correlation_id}] Public path accessed: {request.method} {request.url.path}")
            return await call_next(request)

        # Extract and validate authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(f"[{correlation_id}] Missing authorization header for: {request.method} {request.url.path}")
            return add_cors_headers(JSONResponse(
                status_code=401,
                content={
                    "error": "Authorization header required",
                    "correlation_id": correlation_id
                }
            ), request)

        if not auth_header.startswith("Bearer "):
            logger.warning(f"[{correlation_id}] Invalid auth header format for: {request.method} {request.url.path}")
            return add_cors_headers(JSONResponse(
                status_code=401,
                content={
                    "error": "Invalid authorization header format",
                    "correlation_id": correlation_id
                }
            ), request)

        token = auth_header.split(" ")[1]

        # Verify Google ID token
        try:
            # Verify the token with Google
            google_client_id = settings.GOOGLE_CLIENT_ID
            if not google_client_id:
                logger.error(f"[{correlation_id}] GOOGLE_CLIENT_ID not configured")
                return add_cors_headers(JSONResponse(
                    status_code=500,
                    content={
                        "error": "Authentication not configured",
                        "correlation_id": correlation_id
                    }
                ), request)

            # Verify ID token
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                google_client_id
            )

            # Verify issuer
            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                logger.warning(f"[{correlation_id}] Invalid token issuer: {idinfo.get('iss')}")
                return add_cors_headers(JSONResponse(
                    status_code=401,
                    content={
                        "error": "Invalid token issuer",
                        "correlation_id": correlation_id
                    }
                ), request)

            # Extract user info from token
            user_id = idinfo.get("sub")  # Google's unique user ID
            user_email = idinfo.get("email")
            email_verified = idinfo.get("email_verified", False)

            if not user_id:
                logger.error(f"[{correlation_id}] Token missing subject claim")
                return add_cors_headers(JSONResponse(
                    status_code=401,
                    content={
                        "error": "Invalid token payload",
                        "correlation_id": correlation_id
                    }
                ), request)

            # Require verified email
            if not email_verified:
                logger.warning(f"[{correlation_id}] Email not verified: {user_email}")
                return add_cors_headers(JSONResponse(
                    status_code=403,
                    content={
                        "error": "Email address not verified with Google",
                        "correlation_id": correlation_id
                    }
                ), request)

            # Check email allowlist
            if not _is_email_allowed(user_email):
                logger.warning(f"[{correlation_id}] Access denied for email: {user_email}")
                return add_cors_headers(JSONResponse(
                    status_code=403,
                    content={
                        "error": "Access denied. Your email is not authorized to use Nicole.",
                        "correlation_id": correlation_id
                    }
                ), request)

            # Extract additional user info
            user_name = idinfo.get("name", "")
            user_picture = idinfo.get("picture", "")

            # Determine role (admin for specific emails, standard otherwise)
            user_role = "admin" if user_email and user_email.lower() in _get_allowed_emails() else "standard"

            # Attach user context to request state
            request.state.user_id = user_id
            request.state.user_role = user_role
            request.state.user_email = user_email
            request.state.user_name = user_name
            request.state.user_picture = user_picture
            request.state.token_issued_at = idinfo.get("iat")
            request.state.token_expires_at = idinfo.get("exp")

            # Ensure Tiger user exists (for database operations)
            tiger_user = None
            if user_email:
                tiger_user = await tiger_user_service.get_or_create_user(
                    user_email,
                    full_name=user_name,
                    role=user_role,
                    relationship="owner" if user_role == "admin" else "user",
                )
                request.state.tiger_user_id = tiger_user["user_id"]
                request.state.tiger_user = tiger_user
                await tiger_user_service.touch_user_activity(tiger_user["user_id"])

            masked_email = f"{user_email.split('@')[0][:3]}...@{user_email.split('@')[-1]}" if user_email else "unknown"
            logger.info(
                f"[{correlation_id}] Auth successful - Email: {masked_email}, Role: {user_role}, "
                f"Path: {request.method} {request.url.path}"
            )

        except ValueError as ve:
            # Token verification failed
            logger.warning(f"[{correlation_id}] Token verification failed: {ve}")
            return add_cors_headers(JSONResponse(
                status_code=401,
                content={
                    "error": "Invalid or expired token",
                    "correlation_id": correlation_id
                }
            ), request)
        except Exception as e:
            logger.error(f"[{correlation_id}] Auth error: {str(e)}")
            return add_cors_headers(JSONResponse(
                status_code=401,
                content={
                    "error": "Authentication failed",
                    "correlation_id": correlation_id
                }
            ), request)

        # Execute the request
        response = await call_next(request)

        # Log successful request completion
        duration = time.time() - start_time
        logger.info(
            f"[{correlation_id}] Request completed - Status: {response.status_code}, "
            f"Duration: {duration:.3f}s, User: {request.state.user_email}"
        )

        return response

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"[{correlation_id}] Middleware error: {str(e)} - Duration: {duration:.3f}s",
            exc_info=True
        )
        return add_cors_headers(JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "correlation_id": correlation_id
            }
        ), request)


async def require_admin(request: Request) -> None:
    """
    Helper function to enforce admin-only access.
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If user is not admin
    """
    user_role = get_current_user_role(request)
    if user_role != "admin":
        correlation_id = get_correlation_id(request)
        logger.warning(
            f"[{correlation_id}] Admin access denied - User: {get_current_user_id(request)}, "
            f"Role: {user_role}, Path: {request.method} {request.url.path}"
        )
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )


def log_security_event(event_type: str, request: Request, details: Dict[str, Any] = None):
    """
    Log security-related events for monitoring.
    
    Args:
        event_type: Type of security event
        request: FastAPI request object
        details: Additional event details
    """
    correlation_id = get_correlation_id(request)
    user_id = get_current_user_id(request)

    logger.warning(
        f"[{correlation_id}] Security Event: {event_type} - "
        f"User: {user_id}, Path: {request.method} {request.url.path}, "
        f"Details: {details or {}}"
    )
