"""Authentication routes — sync NextAuth users to DB."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from agentworthy.auth import create_access_token
from agentworthy.database import get_db
from agentworthy.models import User
from agentworthy.schemas import AuthSyncRequest, AuthSyncResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/sync", response_model=AuthSyncResponse)
def sync_user(body: AuthSyncRequest, db: Session = Depends(get_db)) -> AuthSyncResponse:
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user:
        user = User(email=body.email.lower(), name=body.name)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif body.name and user.name != body.name:
        user.name = body.name
        db.commit()
        db.refresh(user)

    token = create_access_token(user.id, user.email)
    return AuthSyncResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        access_token=token,
    )
