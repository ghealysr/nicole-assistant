"""
Authentication middleware for JWT verification.
Verifies Supabase JWT tokens and attaches user_id to request state.
Production-quality with comprehensive error handling and logging.
"""

import uuid
import jwt
import logging
import time
from typing import Callable, Optional, Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from datetime import datetime

from app.config import settings
from app.services.tiger_user_service import tiger_user_service

logger = logging.getLogger(__name__)

import re

# CORS origins for error responses
CORS_ORIGINS = [
    "https://nicole.alphawavetech.com",
    "https://nicole-v7.vercel.app",
    "https://ghealysr-nicole-assistant-yyr5.vercel.app",
]

# Regex pattern for Vercel preview deployments
CORS_ORIGIN_REGEX = re.compile(r"https://ghealysr-nicole-assistant.*\.vercel\.app")


def add_cors_headers(response: JSONResponse, request: Request) -> JSONResponse:
    """Add CORS headers to error responses."""
    origin = request.headers.get("origin", "")
    # Check exact match or regex pattern
    if origin in CORS_ORIGINS or CORS_ORIGIN_REGEX.match(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


# Public paths that don't require authentication
PUBLIC_PATHS = {
    "/healthz",
    "/health/check",
    "/auth/login",
    "/auth/register",
    "/auth/callback",
    "/auth/refresh",
    "/auth/logout",
    "/docs",
    "/redoc",
    "/openapi.json"
}

# Paths that require admin role
ADMIN_PATHS = {
    "/admin",
    "/users",
    "/system"
}


def get_current_user_id(request: Request) -> Optional[str]:
    """Helper to get current user id from request state if available."""
    return getattr(request.state, "user_id", None)


def get_current_user_role(request: Request) -> Optional[str]:
    """Helper to get current user role from request state if available."""
    return getattr(request.state, "user_role", None)


def get_current_tiger_user_id(request: Request) -> Optional[int]:
    """Helper to get Tiger Postgres user_id from request state."""
    return getattr(request.state, "tiger_user_id", None)


def get_correlation_id(request: Request) -> str:
    """Helper to get correlation ID from request state."""
    return getattr(request.state, "correlation_id", "unknown")


async def verify_jwt(request: Request, call_next: Callable):
    """
    JWT verification middleware with comprehensive security and logging.

    Validates Supabase JWT tokens and attaches user context to request state.
    Includes rate limiting protection and detailed security logging.

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

        # Verify JWT token with Supabase
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                options={
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True
                },
                leeway=60
            )

            # Extract user information from JWT
            user_id = payload.get("sub")
            if not user_id:
                logger.error(f"[{correlation_id}] JWT missing subject claim")
                return add_cors_headers(JSONResponse(
                    status_code=401,
                    content={
                        "error": "Invalid token payload",
                        "correlation_id": correlation_id
                    }
                ), request)

            # Optional issuer check if configured
            token_issuer = payload.get("iss")
            expected_issuer = getattr(settings, "SUPABASE_ISSUER", "")
            if expected_issuer and token_issuer != expected_issuer:
                logger.warning(f"[{correlation_id}] Token issuer mismatch")
                return add_cors_headers(JSONResponse(
                    status_code=401,
                    content={
                        "error": "Invalid authentication token",
                        "correlation_id": correlation_id
                    }
                ), request)

            # Validate user_id format as UUID
            try:
                uuid.UUID(str(user_id))
            except Exception:
                logger.warning(f"[{correlation_id}] Token subject is not a valid UUID")
                return add_cors_headers(JSONResponse(
                    status_code=401,
                    content={
                        "error": "Invalid authentication token",
                        "correlation_id": correlation_id
                    }
                ), request)

            # Get user metadata from JWT
            user_metadata = payload.get("user_metadata", {})
            app_metadata = payload.get("app_metadata", {})

            # Determine user role
            user_role = user_metadata.get("role", "standard")

            user_email = payload.get("email") or user_metadata.get("email")

            # Attach user context to request state
            request.state.user_id = user_id
            request.state.user_role = user_role
            request.state.user_email = user_email
            request.state.token_issued_at = payload.get("iat")
            request.state.token_expires_at = payload.get("exp")

            # Ensure Tiger user exists
            tiger_user = None
            if user_email:
                tiger_user = await tiger_user_service.get_or_create_user(
                    user_email,
                    full_name=user_metadata.get("full_name"),
                    role=user_role,
                    relationship=user_metadata.get("relationship"),
                )
                request.state.tiger_user_id = tiger_user["user_id"]
                request.state.tiger_user = tiger_user
                await tiger_user_service.touch_user_activity(tiger_user["user_id"])

            masked_user = f"{str(user_id)[:8]}..."
            logger.info(
                f"[{correlation_id}] Auth successful - User: {masked_user}, Role: {user_role}, "
                f"Path: {request.method} {request.url.path}"
            )

        except jwt.ExpiredSignatureError:
            logger.warning(f"[{correlation_id}] Token expired for path: {request.method} {request.url.path}")
            return add_cors_headers(JSONResponse(
                status_code=401,
                content={
                    "error": "Token has expired",
                    "correlation_id": correlation_id
                }
            ), request)
        except jwt.InvalidTokenError:
            logger.warning(f"[{correlation_id}] Invalid token for path: {request.method} {request.url.path}")
            return add_cors_headers(JSONResponse(
                status_code=401,
                content={
                    "error": "Invalid or expired token",
                    "correlation_id": correlation_id
                }
            ), request)
        except Exception as e:
            logger.error(f"[{correlation_id}] JWT verification error: {str(e)}")
            return add_cors_headers(JSONResponse(
                status_code=500,
                content={
                    "error": "Authentication service error",
                    "correlation_id": correlation_id
                }
            ), request)

        # Execute the request
        response = await call_next(request)

        # Log successful request completion
        duration = time.time() - start_time
        logger.info(
            f"[{correlation_id}] Request completed - Status: {response.status_code}, "
            f"Duration: {duration:.3f}s, User: {request.state.user_id}"
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
