from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schemas import PostCreate, PostResponse, PostUpdate

router = APIRouter()


@router.get(
    "", response_model=list[PostResponse]
)  # Wraps payload in a list & shows schema in /docs
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post)
        .options(
            selectinload(models.Post.author)  # Eager loads models' relationship
        )
        .order_by(models.Post.date_posted.desc())
    )
    posts = result.scalars().all()
    # scalars() unwraps result's tuple
    # all() returns either all objs (True) or None (False)

    return posts  # None (empty list) if post is empty


@router.post(
    "",
    response_model=PostResponse,  # Validates payload & shows schema in /docs
    status_code=status.HTTP_201_CREATED,  # Replaces the default 200 OK
)
async def create_post(
    post: PostCreate,  # PostCreate acts as type hint, returns 422 error details
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.User).where(
            models.User.id == post.user_id
        )  # Checks if user is registered
    )  # Returns SELECT * wrapped in tuple
    user = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if not user:  # Raises error if None
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )
    db.add(new_post)  # Staging new data is necessary for insert
    # Uses await for DB ops that do I/O
    await db.commit()  # Executes to DB
    # Refreshes post & loads model's relationship
    await db.refresh(
        new_post,
        attribute_names=[
            "author"
        ],  # Substitutes the need for seperate selectinload query
    )  # Reloads obj from DB, makes Python aware of DB generated values (e.g. id)

    return new_post  # Pydantic auto serializes SQLAlchemy model into PostResponse via model_config


@router.get(
    "/{post_id}", response_model=PostResponse
)  # Validates a single obj & shows schema in /docs
async def get_post(
    post_id: int,  # Type hint, otherwise returns 422 unprocessable
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))  # Eager loads models' relationship
        .where(models.Post.id == post_id)  # Checks if post_id exists in DB
    )  # Returns SELECT * wrapped in tuple
    post = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if post:
        return post
    raise HTTPException(  # Raises error if None
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found",
    )


@router.put(
    "/{post_id}", response_model=PostResponse
)  # Validates a single obj & shows schema in /docs
async def update_post_full(
    post_id: int,  # Type hint, otherwise returns 422 unprocessable
    post_data: PostCreate,  # Uses PostCreate since it contains all fields for full update
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.Post).where(
            models.Post.id == post_id
        )  # Checks if post_id exists in DB
    )  # Returns SELECT * wrapped in tuple
    post = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if not post:  # If post_id doesn't exist (None)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    if (
        post_data.user_id != post.user_id
    ):  # Checks if the mismatched user_id refers to other author
        result = await db.execute(
            select(models.User).where(
                models.User.id == post_data.user_id
            ),  # Returns the author of that user_id, allowing post ownership transfer
        )  # Returns SELECT * wrapped in tuple
        user = result.scalars().first()
        # scalars() unwraps result's tuple
        # first() returns either the first obj (True) or None (False)

        if not user:  # If the changed user_id doesn't exist (None)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    # No need to stage modified data from DB for update
    # Uses await for DB ops that do I/O
    await db.commit()  # Executes to DB
    # Refreshes post & loads model's relationship
    await db.refresh(
        post,
        attribute_names=[
            "author"
        ],  # Substitutes the need for seperate selectinload query
    )  # Reloads obj from DB, makes Python aware of DB generated values (e.g. id)

    return post  # Pydantic auto serializes SQLAlchemy model into PostResponse via model_config


@router.patch(
    "/{post_id}/", response_model=PostResponse
)  # Validates a single obj & shows schema in /docs
async def update_post_partial(
    post_id: int,  # Type hint, otherwise returns 422 unprocessable
    post_data: PostUpdate,  # Uses PostUpdate to update only title & content
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.Post).where(
            models.Post.id == post_id
        )  # Checks if post_id exists in DB
    )  # Returns SELECT * wrapped in tuple
    post = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if not post:  # If post_id doesn't exist (None)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    update_data = post_data.model_dump(  # Converts post_data into dict
        exclude_unset=True  # True prevents cols not being updated to replace existing values with their default (None)
    )
    for field, value in update_data.items():  # Loops through the dict keys & values
        setattr(post, field, value)  # Assigns post with the new values

    # No need to stage modified data from DB for update
    # Uses await for DB ops that do I/O
    await db.commit()  # Executes to DB
    # Refreshes post & loads model's relationship
    await db.refresh(
        post,
        attribute_names=[
            "author"
        ],  # Substitutes the need for seperate selectinload query
    )  # Reloads obj from DB, makes Python aware of DB generated values (e.g. id)

    return post  # Pydantic auto serializes SQLAlchemy model into PostResponse via model_config


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,  # 204 means req succeeded with no response body to return
)
async def delete_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.Post).where(
            models.Post.id == post_id
        )  # Checks if post_id exists in DB
    )  # Returns SELECT * wrapped in tuple
    post = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if not post:  # If post_id doesn't exist (None)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    # Post ownership check will be added later when integrating auth

    # Uses await for DB ops that do I/O
    await db.delete(post)  # Interacts with DB sess to stage delete
    await db.commit()  # Executes to DB
