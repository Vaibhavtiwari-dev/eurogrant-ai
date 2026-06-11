from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import PyJWTError as JWTError
from sqlalchemy.orm import Session

from . import database, models, schemas
from .config import settings

load_dotenv()

# JWT Configuration
_SECRET_KEY = settings.JWT_SECRET
if not _SECRET_KEY:
    raise ValueError("JWT_SECRET environment variable is not set")
# _SECRET_KEY is confirmed non-None here; assign to a const to appease type checkers
SECRET_KEY: str = _SECRET_KEY

ALGORITHM = "HS256"  # Hardcoded — do not allow env override to prevent algorithm confusion attacks
ACCESS_TOKEN_EXPIRE_MINUTES = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Cookie-first, then fall back to Authorization header
    jwt_token = request.cookies.get("access_token") or token
    if not jwt_token:
        raise credentials_exception

    try:
        payload = jwt.decode(
            jwt_token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": True}
        )
        email: Any = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError as exc:
        raise credentials_exception from exc
    user = db.query(models.User).filter(models.User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    return user


def require_role(allowed_roles: list[models.RoleEnum]):
    async def role_checker(current_user: models.User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have enough permissions to perform this action",
            )
        return current_user

    return role_checker


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    try:
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
