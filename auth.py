from datetime import UTC, datetime, timedelta

import jwt
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from config import settings

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
