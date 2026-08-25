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
from routers import posts, users


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

# Connects routers to app, adds prefix to routes, creates collapsible sections
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])


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
        select(models.Post)
        .options(
            selectinload(models.Post.author)
        )  # selectinload eager loads models' relationship
        .order_by(models.Post.date_posted.desc())
    )
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
        .order_by(models.Post.date_posted.desc())
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
