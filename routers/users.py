from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from auth import (
    CurrentUser,
    create_access_token,
    hash_password,
    verify_password,
)
from config import settings
from database import get_db
from schemas import PostResponse, Token, UserCreate, UserPrivate, UserPublic, UserUpdate

router = APIRouter()


@router.post(
    "",
    response_model=UserPrivate,  # User will get all of their info back after the account is created
    status_code=status.HTTP_201_CREATED,  # Replaces the default 200 OK
)
async def create_user(
    user: UserCreate,  # UserCreate acts as type hint, returns 422 error details
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(  # Checks if username exists in DB
        select(models.User).where(
            func.lower(models.User.username) == user.username.lower()
        ),
    )  # Returns SELECT * wrapped in tuple
    existing_user = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    result = await db.execute(  # Checks if email exists in DB
        select(models.User).where(func.lower(models.User.email) == user.email.lower()),
    )  # Returns SELECT * wrapped in tuple
    existing_email = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(user.password),
    )

    db.add(new_user)  # Staging new data is necessary for insert
    # Uses await for DB ops that do I/O
    await db.commit()  # Executes to DB
    await db.refresh(
        new_user
    )  # Reloads obj from DB, makes Python aware of DB generated values (e.g. id)

    return new_user  # Pydantic auto serializes SQLAlchemy model into UserPrivate via model_config


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[
        OAuth2PasswordRequestForm, Depends()
    ],  # Parses login form data
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.User).where(
            func.lower(models.User.email) == form_data.username.lower()
        )  # OAuth2PasswordRequestForm expects 'username' field, but used for email
    )
    user = result.scalars().first()

    if not user or not verify_password(  # If user not found or wrong pass
        form_data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",  # Doesn't reveal which one failed (security best practice)
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Creates access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},  # User ID as sub
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserPrivate)  # Gets user full info
async def get_current_user(current_user: CurrentUser):
    return current_user


@router.get(
    "/{user_id}",
    response_model=UserPublic,  # Public can see user info
)  # Validates a single obj & shows schema in /docs
async def get_user(
    user_id: int,  # Type hint, otherwise returns 422 unprocessable
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(  # Checks if user_id exists in DB
        select(models.User).where(models.User.id == user_id),
    )  # Returns SELECT * wrapped in tuple
    user = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if user:
        return user

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.get(
    "/{user_id}/posts", response_model=list[PostResponse]
)  # Wraps payload in a list & shows schema in /docs
async def get_user_posts(
    user_id: int,  # Type hint, otherwise returns 422 unprocessable
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(  # Checks if user_id exists in DB
        select(models.User).where(models.User.id == user_id)
    )  # Returns SELECT * wrapped in tuple
    user = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if not user:  # Raises error if None
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = await db.execute(  # Gets posts belong to the user_id
        select(models.Post)
        .options(selectinload(models.Post.author))  # Eager loads models' relationship
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc())
    )  # Returns SELECT * wrapped in tuple
    posts = result.scalars().all()
    # scalars() unwraps result's tuple
    # all() returns either all objs (True) or None (False)

    return posts  # None (empty list) if user has no posts


@router.patch(
    "/{user_id}",  # Locates user using user_id
    response_model=UserPrivate,  # Response body schema validation
)
async def update_user(
    user_id: int,
    user_update: UserUpdate,  # Req body schema validation
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()  # Unwraps result's tuple
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Checks if new username is requested
    if (
        user_update.username is not None
        and user_update.username.lower() != user.username.lower()
    ):
        result = await db.execute(
            select(models.User).where(
                func.lower(models.User.username) == user_update.username.lower()
            )
        )  # Checks if username is taken
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    # Checks if new email is requested
    if (
        user_update.email is not None
        and user_update.email.lower() != user.email.lower()
    ):
        result = await db.execute(
            select(models.User).where(
                func.lower(models.User.email) == user_update.email.lower()
            )
        )  # Checks if email is taken
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    if user_update.username is not None:
        user.username = user_update.username  # Preserves casing
    if user_update.email is not None:
        user.email = user_update.email.lower()  # Stores lowercase
    if user_update.image_file is not None:
        user.image_file = user_update.image_file

    # Uses await for DB ops that do I/O
    await db.commit()
    await db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,  # 204 means req succeeded with no response body to return
)
async def delete_user(
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user",
        )

    result = await db.execute(
        select(models.User).where(
            models.User.id == user_id
        )  # Checks if user_id exists in DB
    )  # Returns SELECT * wrapped in tuple
    user = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if not user:  # If user_id doesn't exist (None)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Uses await for DB ops that do I/O
    await db.delete(user)  # Interacts with DB sess to stage delete
    await db.commit()  # Executes to DB
