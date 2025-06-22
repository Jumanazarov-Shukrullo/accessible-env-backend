from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger


logger = get_logger("middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log all API requests for debugging
        if request.url.path.startswith("/api/v1/"):
            logger.info(f"📥 {request.method} {request.url.path}")

        response = await call_next(request)

        # Log response status for API requests
        if request.url.path.startswith("/api/v1/"):
            status_emoji = "✅" if response.status_code < 400 else "❌"
            logger.info(f"{status_emoji} {request.method} {request.url.path} → {response.status_code}")

        return response
