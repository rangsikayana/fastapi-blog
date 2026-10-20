from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import models
from config import settings
from database import get_db

# Creates pass hasher using argon2
password_hash = PasswordHash.recommended()  # recommended() auto gives secure defaults

# Extracts token from auth header
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/users/token"  # Has to match login endpoint path
)  # Enables 'Authorize' button in /docs


def hash_password(password: str) -> str:  # Takes & returns str
    return password_hash.hash(password)  # Hashes pass that was passed in
    # Chose hashing over encryption since it's irreversible


def verify_password(plain_password: str, hash_password: str) -> bool:
    return password_hash.verify(  # Compares plain & hashed pass
        plain_password, hash_password
    )  # Returns true if matched


def create_access_token(
    data: dict,  # Takes dict
    expires_delta: timedelta | None = None,  # Optional exp delta
) -> str:
    to_encode = data.copy()
    if expires_delta:  # Adds exp
        expire = datetime.now(UTC) + expires_delta
    else:  # Creates exp
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(  # Encodes to JWT
        to_encode,
        settings.secret_key.get_secret_value(),  # Gets the actual secret str
        algorithm=settings.algorithm,
    )
    return encoded_jwt


def verify_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError:  # If invalid signature, expired, missing claims
        return None
    else:  # If valid
        return payload.get("sub")  # Returns sub (user_id)


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> models.User:
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authentication": "Bearer"},
        )

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authentication": "Bearer"},
        )

    result = await db.execute(
        select(models.User).where(models.User.id == user_id_int),
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authentication": "Bearer"},
        )
    return user


CurrentUser = Annotated[models.User, Depends(get_current_user)]
