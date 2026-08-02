from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

import models
from database import Base, engine, get_db
from schemas import PostCreate, PostResponse, UserCreate, UserResponse

Base.metadata.create_all(bind=engine)  # Creates models' tables if not exist

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")


@app.get(
    "/",
    include_in_schema=False,  # False hides route from /docs since it contains HTML
    name="home",
)
@app.get("/posts", include_in_schema=False, name="posts")
def home(
    request: Request,  # Rquest is required by Jinja2
    db: Annotated[Session, Depends(get_db)],
):
    result = db.execute(select(models.Post))  # Gets posts with no filters
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
def post_page(
    request: Request,  # Rquest is required by Jinja2
    post_id: int,  # Type hint, otherwise returns 422 unprocessable
    db: Annotated[Session, Depends(get_db)],
):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
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
def user_posts_page(
    request: Request,  # Rquest is required by Jinja2
    user_id: int,  # Type hint, otherwise returns 422 unprocessable
    db: Annotated[Session, Depends(get_db)],
):
    result = db.execute(  # Checks if user_id exists in DB
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

    result = db.execute(  # Gets posts belong to the user_Id
        select(models.Post).where(models.Post.user_id == user_id)
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
def create_user(
    user: UserCreate,  # UserCreate acts as type hint, returns 422 error details
    db: Annotated[Session, Depends(get_db)],
):
    result = db.execute(  # Checks if username exists in DB
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

    result = db.execute(  # Checks if email exists in DB
        select(models.User).where(models.User.email == user.email),
    )  # Returns SELECT * wrapped in tuple
    existing_email = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )

    new_user = models.User(
        username=user.username,
        email=user.email,
    )

    db.add(new_user)  # Stages insert
    db.commit()  # Executes to DB
    db.refresh(
        new_user
    )  # Reloads obj from DB, makes Python aware of DB generated values (e.g. id)

    return new_user  # Pydantic auto converts this into UserResponse


@app.get(
    "/api/users/{user_id}",
    response_model=UserResponse,  # Validates payload & shows schema in /docs
)  # Validates a single obj & shows schema in /docs
def get_user(
    user_id: int,  # Type hint, otherwise returns 422 unprocessable
    db: Annotated[Session, Depends(get_db)],
):
    result = db.execute(  # Checks if user_id exists in DB
        select(models.User).where(models.User.id == user_id),
    )  # Returns SELECT * wrapped in tuple
    user = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if user:
        return user

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@app.get(
    "/api/users/{user_id}/posts", response_model=list[UserResponse]
)  # Wraps payload in a list & shows schema in /docs
def get_user_posts(
    user_id: int,  # Type hint, otherwise returns 422 unprocessable
    db: Annotated[Session, Depends(get_db)],
):
    result = db.execute(  # Checks if user_id exists in DB
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

    result = db.execute(  # Gets posts belong to the user_id
        select(models.Post).where(models.Post.user_id == user_id),
    )  # Returns SELECT * wrapped in tuple
    posts = result.scalars().all()
    # scalars() unwraps result's tuple
    # all() returns either all objs (True) or None (False)

    return posts  # None (empty list) if user has no posts


@app.get(
    "/api/posts", response_model=list[PostResponse]
)  # Wraps payload in a list & shows schema in /docs
def get_posts(db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    # scalars() unwraps result's tuple
    # all() returns either all objs (True) or None (False)

    return posts  # None (empty list) if post is empty


@app.post(
    "/api/posts",
    response_model=PostResponse,  # Validates payload & shows schema in /docs
    status_code=status.HTTP_201_CREATED,  # Replaces the default 200 OK
)
def create_post(
    post: PostCreate,  # PostCreate acts as type hint, returns 422 error details
    db: Annotated[Session, Depends(get_db)],
):
    result = db.execute(
        select(models.User).where(models.User.id == post.user_id)
    )  # Checks if user is registered
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
    db.add(new_post)  # Stages insert
    db.commit()  # Executes to DB
    db.refresh(
        new_post
    )  # Reloads obj from DB, makes Python aware of DB generated values (e.g. id)

    return new_post  # Pydantic auto converts this into PostResponse


@app.get(
    "/api/posts/{post_id}", response_model=PostResponse
)  # Validates a single obj & shows schema in /docs
def get_post(
    post_id: int,  # Type hint, otherwise returns 422 unprocessable
    db: Annotated[Session, Depends(get_db)],
):
    result = db.execute(
        select(models.Post).where(models.Post.id == post_id)
    )  # Checks if post_id exists in DB
    post = result.scalars().first()
    # scalars() unwraps result's tuple
    # first() returns either the first obj (True) or None (False)

    if post:
        return post
    raise HTTPException(  # Raises error if None
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Post not found",
    )


@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (  # Sets up a message
        exception.detail
        if exception.detail  # Shows detail if has detail
        else "An error occurred. Please check your request and try again."
    )

    if request.url.path.startswith("/api"):
        return JSONResponse(  # Returns JSON for /api route
            status_code=exception.status_code,
            content={"detail": message},
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
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(  # Returns JSON for /api route
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,  # RequestValidationError doesn't have status_code like Starlette
            content={"detail": exception.errors()},  # Type validation error details
        )

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
