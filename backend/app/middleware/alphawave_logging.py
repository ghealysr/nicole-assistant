"""
Logging middleware for structured JSON logs with correlation IDs.
"""

from typing import Callable
from fastapi import Request
import logging
import time
import json

logger = logging.getLogger(__name__)


async def logging_middleware(request: Request, call_next: Callable):
    """
    Logging middleware that adds structured logging with correlation IDs.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/endpoint in chain
        
    Returns:
        Response from next middleware/endpoint
    """
    
    start_time = time.time()
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    # Log request
    logger.info(
        json.dumps({
            "type": "request",
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": str(request.query_params),
            "client_host": request.client.host if request.client else "unknown"
        })
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    logger.info(
        json.dumps({
            "type": "response",
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2)
        })
    )
    
    return response
