from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.exceptions import HTTPException as StarletteHTTPException

import models
from database import Base, engine, get_db
from schemas import (
    PostCreate,
    PostResponse,
    PostUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Runs at startup
    async with engine.begin() as conn:  # Get async conn
        await conn.run_sync(  # Runs sync create tables inside async DB conn driver
            Base.metadata.create_all
        )
    yield  # Transfer controls to app to handle req

    # Runs at shutdown to dispose engine
    await engine.dispose()


app = FastAPI(
    lifespan=lifespan,
    swagger_ui_parameters={
        "tryItOutEnabled": True  # Hides "Try it out" button in /docs
    },
)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")


@app.get(
    "/",
    include_in_schema=False,  # False hides route from /docs since it contains HTML
    name="home",
)
@app.get("/posts", include_in_schema=False, name="posts")
async def home(
    request: Request,  # Rquest is required by Jinja2
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.Post).options(selectinload(models.Post.author)),
    )  # selectinload eager loads models' relationship
    posts = result.scalars().all()
    # scalars() unwraps result's tuple
    # all() returns either all objs (True) or None (False)

    return templates.TemplateResponse(  # Renders Jinja2 that injects JSON response into HTML
        request,
        "home.html",
        {
            "posts": posts,  # Uses posts since home.html loops over posts
            "title": "Home",
        },
    )


@app.get(
    "/posts/{post_id}",
    include_in_schema=False,  # False hides route from /docs since it contains HTML
)
async def post_page(
    request: Request,  # Rquest is required by Jinja2
    post_id: int,  # Type hint, otherwise returns 422 unprocessable
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))  # Eager loads models' relationship
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if post:
        title = post.title[:50]  # Gets title value for browser tab's title
        return templates.TemplateResponse(  # Renders Jinja2 that injects JSON response into HTML
            request,
            "post.html",
            {
                "post": post,  # Uses post since post.html shows a single post
                "title": title,
            },
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(
    request: Request,  # Rquest is required by Jinja2
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

    result = await db.execute(  # Gets posts belong to the user_Id
        select(models.Post)
        .options(selectinload(models.Post.author))  # Eager loads models' relationship
        .where(models.Post.user_id == user_id)
    )  # Returns SELECT * wrapped in tuple
    posts = result.scalars().all()
    # scalars() unwraps result's tuple
    # all() returns either all objs (True) or None (False)

    return templates.TemplateResponse(  # Renders template if post exists
        request,
        "user_posts.html",
        {
            "posts": posts,  # Uses posts since user_posts.html loops over user's posts
            "user": user,
            "title": f"{user.username}'s Posts",
        },
    )


@app.post(
    "/api/users",
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


@app.get(
    "/api/users/{user_id}",
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


@app.get(
    "/api/users/{user_id}/posts", response_model=list[PostResponse]
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


@app.patch(
    "/api/users/{user_id}",  # Locates user using user_id
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


@app.delete(
    "/api/users/{user_id}",
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


@app.get(
    "/api/posts", response_model=list[PostResponse]
)  # Wraps payload in a list & shows schema in /docs
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post).options(
            selectinload(models.Post.author)  # Eager loads models' relationship
        )
    )
    posts = result.scalars().all()
    # scalars() unwraps result's tuple
    # all() returns either all objs (True) or None (False)

    return posts  # None (empty list) if post is empty


@app.post(
    "/api/posts",
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


@app.get(
    "/api/posts/{post_id}", response_model=PostResponse
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


@app.put(
    "/api/posts/{post_id}", response_model=PostResponse
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


@app.patch(
    "/api/posts/{post_id}/", response_model=PostResponse
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


@app.delete(
    "/api/posts/{post_id}",
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


@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(
    request: Request, exception: StarletteHTTPException
):

    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)

    message = (  # Sets up a message for template routes (TemplateResponse)
        exception.detail
        if exception.detail  # Shows detail if has detail
        else "An error occurred. Please check your request and try again."
    )

    return templates.TemplateResponse(  # Returns error.html for non /api routes
        request,
        "error.html",
        {  # Passes contexts to error.html via Jinja2
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )  # Passes status_code to TemplateResponse for browser


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exception: RequestValidationError
):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)

    return templates.TemplateResponse(  # Returns error.html for non /api routes
        request,
        "error.html",
        {  # Passes contexts to error.html via Jinja2
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )  # Passes status_code to TemplateResponse for browser
