"""JWT authentication and user resolution."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from agentworthy.config import get_settings
from agentworthy.database import get_db
from agentworthy.models import User

security = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30


def create_access_token(user_id: uuid.UUID, email: str) -> str:
    settings = get_settings()
    secret = settings.nextauth_secret or settings.api_secret_key
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(UTC) + timedelta(days=TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, str]:
    settings = get_settings()
    secret = settings.nextauth_secret or settings.api_secret_key
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        email = payload.get("email")
        if not sub or not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return {"sub": str(sub), "email": str(email)}
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    data = decode_token(credentials.credentials)
    try:
        user_id = uuid.UUID(data["sub"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def get_site_for_user(db: Session, site_id: uuid.UUID, user: User):
    from agentworthy.models import Site

    site = db.get(Site, site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    if site.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return site
