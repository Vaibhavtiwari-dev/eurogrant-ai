from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import auth, database, models, schemas
from ..config import settings
from ..limiter import get_real_ip, limiter
from ..services.lockout import lockout_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/invitations", response_model=schemas.UserInvitationOut, status_code=status.HTTP_201_CREATED)
def create_invitation(
    invite_in: schemas.UserInvitationCreate,
    current_user: models.User = Depends(auth.require_role([models.RoleEnum.ADMIN])),
    db: Session = Depends(database.get_db),
):
    import secrets
    from datetime import UTC, datetime, timedelta
    
    if invite_in.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Cannot invite to other organizations")
        
    invite_code = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(days=7)
    
    invitation = models.UserInvitation(
        email=invite_in.email,
        organization_id=invite_in.organization_id,
        invited_by_id=current_user.id,
        invite_code=invite_code,
        expires_at=expires_at,
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(
    request: Request,
    user_in: schemas.UserCreate,
    db: Session = Depends(database.get_db),
) -> models.User:
    from datetime import UTC, datetime
    
    invitation = db.query(models.UserInvitation).filter(
        models.UserInvitation.invite_code == user_in.invite_code,
        models.UserInvitation.is_used == False,
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=403, detail="Invalid or used invite code")
        
    if invitation.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=403, detail="Invite code expired")
        
    if invitation.email.lower() != user_in.email.lower():
        raise HTTPException(status_code=400, detail="Email does not match invitation")

    org = db.query(models.Organization).filter(models.Organization.id == invitation.organization_id).first()
    if not org:
        raise HTTPException(status_code=400, detail="Invalid organization")

    # Check if user already exists
    user = db.query(models.User).filter(models.User.email == user_in.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Determine role based on existing users
    existing_user_count = (
        db.query(models.User).filter(models.User.organization_id == org.id).count()
    )
    user_role = models.RoleEnum.ADMIN if existing_user_count == 0 else models.RoleEnum.VIEWER

    # Create user
    hashed_password = auth.get_password_hash(user_in.password)
    new_user = models.User(
        email=user_in.email,
        hashed_password=hashed_password,
        full_name=user_in.full_name,
        organization_id=org.id,
        role=user_role,
    )
    db.add(new_user)
    
    # Mark invitation as used
    invitation.is_used = True
    
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
    client_identifier = get_real_ip(request)

    # Check account lockout before proceeding
    if lockout_service.check_locked(user_credentials.username, client_identifier):
        raise HTTPException(status_code=403, detail="Account temporarily locked. Try again later.")

    # LOW-01: constant-time bcrypt check even when user doesn't exist — prevents timing-oracle enumeration
    if not user:
        auth.verify_password(
            user_credentials.password,
            "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4fSRF6fK.2P8IqGK",
        )
        lockout_service.record_failure(user_credentials.username, client_identifier)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    if not auth.verify_password(user_credentials.password, user.hashed_password):
        lockout_service.record_failure(user_credentials.username, client_identifier)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    lockout_service.reset(user_credentials.username, client_identifier)

    access_token = auth.create_access_token(data={"sub": user.email})
    refresh_token = auth.create_refresh_token(data={"sub": user.email})

    # Set httpOnly cookie with strict SameSite + Secure flags for CSRF protection
    is_localhost = settings.ENVIRONMENT == "development"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not is_localhost,  # True in production (requires HTTPS)
        samesite="strict",  # Strict CSRF protection
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not is_localhost,
        samesite="strict",
        max_age=auth.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1/auth/refresh",
    )

    return {
        "message": "Authentication successful",
        "token_type": "bearer",  # nosec B105 - OAuth token type, not a password
    }  # SECURITY: JWT delivered exclusively via httpOnly cookie


@router.post("/change-password")
def change_password(
    password_change: schemas.PasswordChange,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(database.get_db),
) -> dict:
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    if not user or not auth.verify_password(password_change.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Current password is incorrect"
        )
    user.hashed_password = auth.get_password_hash(password_change.new_password)
    db.commit()
    return {"message": "Password updated successfully"}


@router.post("/logout")
def logout(response: Response) -> dict:
    is_localhost = settings.ENVIRONMENT == "development"
    response.delete_cookie(
        key="access_token", httponly=True, samesite="strict", path="/", secure=not is_localhost
    )
    response.delete_cookie(
        key="refresh_token", httponly=True, samesite="strict", path="/api/v1/auth/refresh", secure=not is_localhost
    )
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=schemas.Token, response_model_exclude_none=True)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(database.get_db),
) -> dict:
    import jwt
    from jwt.exceptions import PyJWTError as JWTError
    from typing import Any
    
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    
    try:
        payload = jwt.decode(refresh_token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM], options={"verify_exp": True})
        email: Any = payload.get("sub")
        token_type = payload.get("type")
        if email is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User inactive or deleted")
        
    access_token = auth.create_access_token(data={"sub": user.email})
    is_localhost = settings.ENVIRONMENT == "development"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not is_localhost,
        samesite="strict",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    return {
        "message": "Token refreshed",
        "token_type": "bearer",
    }
