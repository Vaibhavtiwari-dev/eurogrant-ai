import os
from fastapi import FastAPI, Depends, APIRouter, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded as RateLimitExceededExc
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import models, schemas
from .routers import auth as auth_router, uploads as uploads_router, organizations as organizations_router, grants as grants_router
from .auth import get_current_user
from .limiter import limiter

app = FastAPI(title="EuroGrant AI API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceededExc, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# Determine allowed hosts for TrustedHostMiddleware.
# Always include localhost variants and known production domains.
# Add "testserver" only when not in production (test clients send Host: testserver).
_allowed_hosts = ["eurogrant.ai", "www.eurogrant.ai", "localhost", "127.0.0.1"]
if os.getenv("ENVIRONMENT", "production") != "production":
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
    return response

# CSRF Protection Middleware — validates Origin on state-changing requests
@app.middleware("http")
async def csrf_protection_middleware(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")
        allowed_origins = {"http://localhost:3000", "http://127.0.0.1:3000", "https://eurogrant.ai"}
        # If Origin header is present, validate it matches an allowed origin
        if origin:
            # Strip trailing slash for comparison
            if origin.rstrip("/") not in {o.rstrip("/") for o in allowed_origins}:
                raise HTTPException(status_code=403, detail="CSRF validation failed: unauthorized origin")
        # If no Origin but Referer is present, validate it too (defence-in-depth)
        elif referer:
            # Extract scheme+host from referer and compare
            from urllib.parse import urlparse
            ref_parsed = urlparse(referer)
            ref_origin = f"{ref_parsed.scheme}://{ref_parsed.netloc}"
            if ref_origin.rstrip("/") not in {o.rstrip("/") for o in allowed_origins}:
                raise HTTPException(status_code=403, detail="CSRF validation failed: unauthorized referer")
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
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Versioning: v1 Router
api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router.router)
api_v1_router.include_router(uploads_router.router)
api_v1_router.include_router(organizations_router.router)
api_v1_router.include_router(grants_router.router)

# Include versioned router in app
app.include_router(api_v1_router)

# Global/Unversioned Routes
@app.get("/")
@limiter.limit("5/minute")
async def root(request: Request):
    return {"message": "Welcome to EuroGrant AI API"}

@app.get("/api/v1/users/me", response_model=schemas.UserOut)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user
