import os
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from .. import models, schemas, auth, database
from ..limiter import limiter
from fastapi.security import OAuth2PasswordRequestForm
from ..services.lockout import lockout_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(
    request: Request,
    user_in: schemas.UserCreate,
    db: Session = Depends(database.get_db),
) -> models.User:
    # Validate invite code - Mandatory environment variable check
    master_invite_code = os.getenv("MASTER_INVITE_CODE")
    if not master_invite_code:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration system is misconfigured. MASTER_INVITE_CODE environment variable is missing."
        )

    if user_in.invite_code != master_invite_code:
        raise HTTPException(status_code=403, detail="Invalid invite code")

    # Check if user already exists
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check if organization exists or create new
    org = db.query(models.Organization).filter(models.Organization.name == user_in.organization_name).first()
    if not org:
        org = models.Organization(name=user_in.organization_name)
        db.add(org)
        db.commit()
        db.refresh(org)
    else:
        # Prevent org name squatting: if joining an existing org,
        # the email domain should loosely match the org name.
        email_domain = user_in.email.split("@")[-1].lower()
        org_name_normalized = user_in.organization_name.lower().replace(" ", "").replace("-", "")
        if org_name_normalized not in email_domain and email_domain not in org_name_normalized:
            raise HTTPException(
                status_code=400,
                detail="Your email domain does not match this organization. Contact the admin for an invite."
            )

    # Check if org already has users to determine role
    existing_user_count = db.query(models.User).filter(models.User.organization_id == org.id).count()
    user_role = models.RoleEnum.ADMIN if existing_user_count == 0 else models.RoleEnum.VIEWER

    # Create user
    hashed_password = auth.get_password_hash(user_in.password)
    new_user = models.User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        organization_id=org.id,
        role=user_role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", response_model=schemas.Token, response_model_exclude_none=True)
@limiter.limit("5/minute")
def login(
    request: Request,
    response: Response,
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
) -> dict:
    user = db.query(models.User).filter(models.User.email == user_credentials.username).first()

    # Check account lockout before proceeding
    if lockout_service.check_locked(user_credentials.username):
        raise HTTPException(status_code=403, detail="Account temporarily locked. Try again later.")

    # LOW-01: constant-time bcrypt check even when user doesn't exist — prevents timing-oracle enumeration
    if not user:
        auth.verify_password(user_credentials.password, "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4fSRF6fK.2P8IqGK")
        lockout_service.record_failure(user_credentials.username)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    if not auth.verify_password(user_credentials.password, user.hashed_password):
        lockout_service.record_failure(user_credentials.username)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    lockout_service.reset(user_credentials.username)

    access_token = auth.create_access_token(data={"sub": user.email})

    # Set httpOnly cookie with strict SameSite + Secure flags for CSRF protection
    is_localhost = os.getenv("ENVIRONMENT", "development") == "development"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not is_localhost,  # True in production (requires HTTPS)
        samesite="strict",       # Strict CSRF protection
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    return {"message": "Authentication successful", "token_type": "bearer"}  # SECURITY: JWT delivered exclusively via httpOnly cookie


@router.post("/logout")
def logout(response: Response) -> dict:
    is_localhost = os.getenv("ENVIRONMENT", "development") == "development"
    response.delete_cookie(key="access_token", httponly=True, samesite="strict", path="/", secure=not is_localhost)
    return {"message": "Successfully logged out"}
