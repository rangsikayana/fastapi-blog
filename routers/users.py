from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schemas import PostResponse, UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.post(
    "",
    response_model=UserResponse,  # Validates payload & shows schema in /docs
    status_code=status.HTTP_201_CREATED,  # Replaces the default 200 OK
)
async def create_user(
    user: UserCreate,  # UserCreate acts as type hint, returns 422 error details
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(  # Checks if username exists in DB
        select(models.User).where(models.User.username == user.username),
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
        select(models.User).where(models.User.email == user.email),
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
        email=user.email,
    )

    db.add(new_user)  # Staging new data is necessary for insert
    # Uses await for DB ops that do I/O
    await db.commit()  # Executes to DB
    await db.refresh(
        new_user
    )  # Reloads obj from DB, makes Python aware of DB generated values (e.g. id)

    return new_user  # Pydantic auto serializes SQLAlchemy model into UserResponse via model_config


@router.get(
    "/{user_id}",
    response_model=UserResponse,  # Validates payload & shows schema in /docs
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
        select(models.User).where(models.User.id == user_id),
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
        .where(models.Post.user_id == user_id),
    )  # Returns SELECT * wrapped in tuple
    posts = result.scalars().all()
    # scalars() unwraps result's tuple
    # all() returns either all objs (True) or None (False)

    return posts  # None (empty list) if user has no posts


@router.patch(
    "/{user_id}",  # Locates user using user_id
    response_model=UserResponse,  # Response body schema validation
)
async def update_user(
    user_id: int,
    user_update: UserUpdate,  # Req body schema validation
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()  # Unwraps result's tuple
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Checks if new username is requested
    if user_update.username is not None and user_update.username != user.username:
        result = await db.execute(
            select(models.User).where(models.User.username == user_update.username)
        )  # Checks if username is taken
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    # Checks if new email is requested
    if user_update.email is not None and user_update.email != user.email:
        result = await db.execute(
            select(models.User).where(models.User.email == user_update.email)
        )  # Checks if email is taken
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email
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
    db: Annotated[AsyncSession, Depends(get_db)],
):
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
