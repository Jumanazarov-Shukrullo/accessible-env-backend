from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.routers.assessment_detail_router import (
    assessment_detail_router,
)
from app.api.v1.routers.assessment_router import assessment_router
from app.api.v1.routers.assessment_set_router import assessment_set_router
from app.api.v1.routers.category_router import category_router
from app.api.v1.routers.criteria_router import criteria_router
from app.api.v1.routers.geo_router import geo_router
from app.api.v1.routers.image_router import image_router
from app.api.v1.routers.location_router import location_router
from app.api.v1.routers.metrics_router import metrics_router
from app.api.v1.routers.notification_router import notification_router
from app.api.v1.routers.permission_router import permission_router
from app.api.v1.routers.rating_router import rating_router
from app.api.v1.routers.review_router import review_router
from app.api.v1.routers.role_router import role_router
from app.api.v1.routers.social_router import social_router
from app.api.v1.routers.statistic_router import statistic_router
from app.api.v1.routers.statistics_router import statistics_router
from app.api.v1.routers.user_router import user_router_instance
from app.core.config import settings

from app.middlewares.logging_middleware import LoggingMiddleware
from app.middlewares.rate_limit import limiter
from app.utils.logger import configure_logging


# Configure logging to prevent duplicates
configure_logging()

app = FastAPI(title="Enterprise FastAPI Application")

# Configure CORS using settings from .env file
allowed_origins = []

# Fix: allowed_hosts_list is a property, not an attribute
try:
    hosts_list = settings.allowed_hosts_list
    for host in hosts_list:
        # Ensure proper URL format
        if host.startswith(("http://", "https://")):
            # Remove trailing slash if present
            host = host.rstrip("/")
            allowed_origins.append(host)
        else:
            # Skip invalid entries that don't start with protocol
            print(f"Skipping invalid origin (missing protocol): {host}")
except Exception as e:
    print(f"Error processing allowed_hosts from settings: {e}")

# Fallback to localhost if no valid origins from settings
print(f"Loaded origins from settings: {allowed_origins}")
if not allowed_origins:
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000", 
        "http://127.0.0.1:8000"
    ]
    print("Using fallback CORS origins (no valid origins from settings)")

print("CORS allowed origins:", allowed_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    same_site="none",  # Required for OAuth cross-site redirects
    https_only=False,  # Set to False for local development, True for production
    session_cookie="sid",
    max_age=3600,
)

# app.add_middleware(
#     SessionMiddleware,
#     secret_key=settings.session_secret_key,  # Use a secure, random string
#     max_age=3600,         # Optional: session lifetime in seconds
#     same_site="none",      # Optional
#     session_cookie="sid",  # Optional: cookie name
#     https_only=False,
# )

# 1) SlowAPI Rate limiting
app.add_middleware(SlowAPIMiddleware)
app.state.limiter = limiter

# 2) Logging middleware
app.add_middleware(LoggingMiddleware)

# 3) Session middleware (needed by Authlib for request.session)

# Prometheus instrumentation
Instrumentator().instrument(app).expose(app)

# Include your routers
app.include_router(
    user_router_instance.router, prefix="/api/v1/users", tags=["Users"]
)
app.include_router(location_router, prefix="/api/v1")
app.include_router(assessment_router, prefix="/api/v1")
app.include_router(geo_router, prefix="/api/v1")
app.include_router(category_router, prefix="/api/v1")
app.include_router(review_router, prefix="/api/v1")
app.include_router(statistic_router, prefix="/api/v1")
app.include_router(notification_router, prefix="/api/v1")
app.include_router(assessment_detail_router, prefix="/api/v1")
app.include_router(image_router, prefix="/api/v1")
app.include_router(social_router, prefix="/api/v1")
app.include_router(role_router, prefix="/api/v1")
app.include_router(permission_router, prefix="/api/v1")
app.include_router(assessment_set_router, prefix="/api/v1")
app.include_router(criteria_router, prefix="/api/v1")
app.include_router(statistics_router, prefix="/api/v1")
app.include_router(rating_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")


# Health check endpoint for Railway
@app.get("/health")
async def health():
    return {"status": "healthy", "message": "Backend is running"}


@app.get("/")
async def root():
    return {"message": "Enterprise FastAPI Application"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
