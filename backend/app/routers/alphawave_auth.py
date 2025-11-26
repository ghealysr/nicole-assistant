"""
Authentication router for Supabase OAuth and email/password login.
"""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional
import logging

from app.database import get_supabase
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class AlphawaveLoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str


class AlphawaveRegisterRequest(BaseModel):
    """Registration request model."""
    email: EmailStr
    password: str
    full_name: str


class AlphawaveAuthResponse(BaseModel):
    """Authentication response model."""
    access_token: str
    refresh_token: str
    user_id: str
    email: str


@router.post("/login", response_model=AlphawaveAuthResponse)
async def login(request: Request, login_data: AlphawaveLoginRequest) -> AlphawaveAuthResponse:
    """
    Login with email and password using Supabase Auth.
    
    Args:
        request: FastAPI request object
        login_data: Login credentials
        
    Returns:
        Authentication tokens and user info
        
    Raises:
        HTTPException: If login fails
    """
    
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    try:
        supabase = get_supabase()
        if supabase is None:
            raise HTTPException(status_code=503, detail="Supabase unavailable")
        # Authenticate with Supabase
        response = supabase.auth.sign_in_with_password({
            "email": login_data.email,
            "password": login_data.password
        })
        
        if not response.user or not response.session:
            logger.warning(
                f"[{correlation_id}] Login failed for {login_data.email}"
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        logger.info(
            f"[{correlation_id}] Login successful for user: {response.user.id}"
        )
        
        return AlphawaveAuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user_id=str(response.user.id),
            email=response.user.email
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[{correlation_id}] Login error: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Authentication failed"
        )


@router.post("/register", response_model=AlphawaveAuthResponse)
async def register(request: Request, register_data: AlphawaveRegisterRequest) -> AlphawaveAuthResponse:
    """
    Register new user with email and password using Supabase Auth.
    
    Args:
        request: FastAPI request object
        register_data: Registration data
        
    Returns:
        Authentication tokens and user info
        
    Raises:
        HTTPException: If registration fails
    """
    
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    try:
        supabase = get_supabase()
        if supabase is None:
            raise HTTPException(status_code=503, detail="Supabase unavailable")
        # Register with Supabase
        response = supabase.auth.sign_up({
            "email": register_data.email,
            "password": register_data.password,
            "options": {
                "data": {
                    "full_name": register_data.full_name
                }
            }
        })
        
        if not response.user or not response.session:
            logger.warning(
                f"[{correlation_id}] Registration failed for {register_data.email}"
            )
            raise HTTPException(
                status_code=400,
                detail="Registration failed"
            )
        
        logger.info(
            f"[{correlation_id}] Registration successful for user: {response.user.id}"
        )
        
        return AlphawaveAuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user_id=str(response.user.id),
            email=response.user.email
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[{correlation_id}] Registration error: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Registration failed"
        )


@router.post("/refresh")
async def refresh_token(request: Request, refresh_token: str) -> AlphawaveAuthResponse:
    """
    Refresh access token using refresh token.
    
    Args:
        request: FastAPI request object
        refresh_token: Refresh token
        
    Returns:
        New authentication tokens
        
    Raises:
        HTTPException: If refresh fails
    """
    
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    try:
        supabase = get_supabase()
        if supabase is None:
            raise HTTPException(status_code=503, detail="Supabase unavailable")
        response = supabase.auth.refresh_session(refresh_token)
        
        if not response.user or not response.session:
            logger.warning(
                f"[{correlation_id}] Token refresh failed"
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token"
            )
        
        logger.info(
            f"[{correlation_id}] Token refreshed for user: {response.user.id}"
        )
        
        return AlphawaveAuthResponse(
            access_token=response.session.access_token,
            refresh_token=response.session.refresh_token,
            user_id=str(response.user.id),
            email=response.user.email
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"[{correlation_id}] Token refresh error: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(request: Request) -> dict:
    """
    Logout current user (invalidate session).
    
    Args:
        request: FastAPI request object
        
    Returns:
        Success message
    """
    
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    user_id = getattr(request.state, "user_id", None)
    
    try:
        supabase = get_supabase()
        if supabase is None:
            raise HTTPException(status_code=503, detail="Supabase unavailable")
        supabase.auth.sign_out()
        
        logger.info(
            f"[{correlation_id}] Logout successful for user: {user_id}"
        )
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(
            f"[{correlation_id}] Logout error: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Logout failed"
        )


@router.get("/callback")
async def auth_callback(code: Optional[str] = None, error: Optional[str] = None) -> dict:
    """
    OAuth callback endpoint for Google OAuth.
    
    Args:
        code: OAuth authorization code
        error: Optional error from OAuth provider
        
    Returns:
        Redirect information
    """
    
    if error:
        logger.error(f"OAuth error: {error}")
        return {
            "error": error,
            "redirect": f"{settings.FRONTEND_URL}/login?error={error}"
        }
    
    if not code:
        return {
            "error": "No authorization code",
            "redirect": f"{settings.FRONTEND_URL}/login?error=no_code"
        }
    
    try:
        supabase = get_supabase()
        if supabase is None:
            return {
                "error": "Supabase unavailable",
                "redirect": f"{getattr(settings, 'FRONTEND_URL', '')}/login?error=supabase_unavailable",
            }
        # Exchange code for session
        response = supabase.auth.exchange_code_for_session(code)
        
        if response.session:
            return {
                "success": True,
                "redirect": f"{settings.FRONTEND_URL}/chat",
                "access_token": response.session.access_token
            }
        
        return {
            "error": "Session creation failed",
            "redirect": f"{settings.FRONTEND_URL}/login?error=session_failed"
        }
        
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        return {
            "error": str(e),
            "redirect": f"{settings.FRONTEND_URL}/login?error=callback_failed"
        }

