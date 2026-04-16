import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import jwk
from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from src.config import settings
from src.database.main import get_session
from src.database.models.users import UserRole, Users
from src.services.users import get_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


def decode_token(token: str) -> dict:
    try:
        logger.debug(f"Decoding token: {token[:30]}...")
        logger.debug(f"Using secret key: {settings.JWT_SECRET_KEY!r}")
        logger.debug(f"Using algorithm: {settings.JWT_ALGORITHM!r}")
        secret_key = jwk.OctetJWK(settings.JWT_SECRET_KEY.encode())
        payload = jwt.JWT().decode(token, secret_key)
        logger.debug(f"Decoded payload type: {type(payload)}, value: {payload}")
        return payload
    except Exception as e:
        logger.error(f"Token decode failed — type={type(e).__name__}, error={e!s}")
        logger.error(f"Token was: {token}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: AsyncSession = Depends(get_session),
) -> Users:
    payload = decode_token(token)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await get_user(session, uuid.UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


CurrentUser = Annotated[Users, Depends(get_current_user)]


def require_teacher(current_user: Annotated[Users, Depends(get_current_user)]) -> Users:
    if current_user.role != UserRole.teacher:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can perform this action",
        )
    return current_user


TeacherUser = Annotated[Users, Depends(require_teacher)]
