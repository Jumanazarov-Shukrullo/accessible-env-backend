import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger

logger = get_logger("middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only log important requests (not OPTIONS, health checks, etc.)
        if request.method in ["POST", "PUT", "DELETE"] or request.url.path.startswith("/api/v1/"):
            if not request.url.path.endswith("/me") and "_optimize=true" not in str(request.url.query):
                logger.info(f"Request: {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        # Only log error responses and important successful operations
        if response.status_code >= 400 or (response.status_code < 400 and request.method in ["POST", "PUT", "DELETE"]):
            if not request.url.path.endswith("/me") and "_optimize=true" not in str(request.url.query):
                logger.info(f"Response status: {response.status_code} for {request.method} {request.url.path}")
                
        return response
