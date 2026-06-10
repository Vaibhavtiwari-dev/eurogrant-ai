import logging
import secrets

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded as RateLimitExceededExc
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import models, schemas
from .auth import get_current_user
from .config import settings
from .limiter import limiter
from .routers import auth as auth_router
from .routers import grants as grants_router
from .routers import organizations as organizations_router
from .routers import proposals as proposals_router
from .routers import uploads as uploads_router

logger = logging.getLogger(__name__)

app = FastAPI(title="EuroGrant AI API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceededExc, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Determine allowed hosts for TrustedHostMiddleware.
# Always include localhost variants and known production domains.
# Add "testserver" only when not in production (test clients send Host: testserver).
_allowed_hosts = ["eurogrant.ai", "www.eurogrant.ai", "localhost", "127.0.0.1"]
if settings.ENVIRONMENT != "production":
    _allowed_hosts.append("testserver")

# Security: TrustedHostMiddleware — block requests with unrecognized Host headers
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=_allowed_hosts,
)


# Security: Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Note: 'unsafe-inline' in style-src is acceptable and required for Tailwind CSS / Next.js.
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
    )
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=()"
    response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return response


# CSRF Token Middleware — sets csrf_token cookie on GET requests if not already present
@app.middleware("http")
async def csrf_token_middleware(request: Request, call_next):
    response = await call_next(request)
    if request.method == "GET" and not request.cookies.get("csrf_token"):
        token = secrets.token_hex(32)
        response.set_cookie(
            key="csrf_token",
            value=token,
            httponly=False,
            samesite="strict",
            secure=settings.ENVIRONMENT != "development",
            path="/",
        )
    return response


# CSRF Protection Middleware — validates Origin on state-changing requests
@app.middleware("http")
async def csrf_protection_middleware(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        allowed_origins = {"http://localhost:3000", "http://127.0.0.1:3000", "https://eurogrant.ai"}
        if settings.ENVIRONMENT != "production":
            allowed_origins.add("http://testserver")
        # If Origin header is present, validate it matches an allowed origin
        if origin:
            # Strip trailing slash for comparison
            if origin.rstrip("/") not in {o.rstrip("/") for o in allowed_origins}:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed: unauthorized origin"},
                )
        # If no Origin but Referer is present, validate it too (defence-in-depth)
        elif referer:
            # Extract scheme+host from referer and compare
            from urllib.parse import urlparse

            ref_parsed = urlparse(referer)
            ref_origin = f"{ref_parsed.scheme}://{ref_parsed.netloc}"
            if ref_origin.rstrip("/") not in {o.rstrip("/") for o in allowed_origins}:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed: unauthorized referer"},
                )
        else:
            if settings.ENVIRONMENT == "testing":
                pass
            else:
                csrf_cookie = request.cookies.get("csrf_token")
                csrf_header = request.headers.get("X-CSRF-Token")
                if not (
                    csrf_cookie and csrf_header and secrets.compare_digest(csrf_cookie, csrf_header)
                ):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF validation failed: missing or invalid token"},
                    )
    response = await call_next(request)
    return response


# Configure CORS
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://eurogrant.ai",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "Accept"],
)

# API Versioning: v1 Router
api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router.router)
api_v1_router.include_router(uploads_router.router)
api_v1_router.include_router(organizations_router.router)
api_v1_router.include_router(grants_router.router)
api_v1_router.include_router(proposals_router.router)

# Include versioned router in app
app.include_router(api_v1_router)


# Health Check Endpoint
@app.get("/health")
async def health_check():
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "lockout_degraded": False,
    }
    try:
        from .database import SessionLocal

        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["database"] = "ok"
    except Exception as e:
        health_status["database"] = "error: " + str(e)
        health_status["status"] = "degraded"
    try:
        from redis import Redis as RedisClient

        r = RedisClient.from_url(settings.CELERY_BROKER_URL)
        r.ping()
        r.close()
        health_status["redis"] = "ok"
    except Exception as e:
        health_status["redis"] = "error: " + str(e)
        health_status["status"] = "degraded"
    # Surface lockout degradation separately: an attacker DoSing Redis must
    # not silently disable account-lockout visibility on the /health endpoint.
    try:
        from .services.lockout import lockout_service

        if lockout_service.is_degraded():
            health_status["lockout_degraded"] = True
            health_status["status"] = "degraded"
    except Exception:
        logger.warning("Health check: lockout service check failed", exc_info=True)
    status_code = 200 if health_status["status"] == "healthy" else 503
    from fastapi.responses import JSONResponse

    return JSONResponse(content=health_status, status_code=status_code)


# Global/Unversioned Routes
@app.get("/")
@limiter.limit("5/minute")
async def root(request: Request):
    return {"message": "Welcome to EuroGrant AI API"}


@app.get("/api/v1/users/me", response_model=schemas.UserOut)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user
