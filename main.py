from email.policy import HTTP

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic.json_schema import JsonRef
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

posts: list[dict] = [ # This runs in memory
	{
		"id": 1,
		"author": "Rangsi Kayana",
		"title": "Learning FastAPI",
		"content": "FastAPI is a modern, blazing fast Python framework.",
		"date_posted": "24 July 2026"
	},
	{
		"id": 2,
		"author": "Jimmy Sparks",
		"title": "Leader of the Landslide",
		"content": "This is a song from The Lumineers' III album.",
		"date_posted": "24 July 2026"
	},
]


@app.get("/", include_in_schema=False, name="home") # False hides endpoint from /docs
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request): # Rquest is required by Jinja2
    return templates.TemplateResponse( # Returns HTML response instead of JSON
        request,
        "home.html",
        {"posts": posts, "title": "Home"}, # Uses posts since home.html loops over all posts
    ) # Injects JSON data into HTML via Jinja2


@app.get("/posts/{post_id}", include_in_schema=False) # Hides endpoint from /docs since it contains HTML
def post_page(request: Request, post_id: int): # Rquest is required by Jinja2
    for post in posts:
        if post.get("id") == post_id:
            title = post["title"][:50] # Gets title value for browser tab's title
            return templates.TemplateResponse( # Returns HTML response instead of JSON
                request,
                "post.html",
                {"post": post, "title": title}, # Uses post since post.html shows one post
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.get("/api/posts")
def get_post():
    return posts


@app.get("/api/posts/{post_id}")
def get_post(post_id: int): # Int type hint, otherwise returns 422 status (e.g. api/posts/one)
    for post in posts:
        if post.get("id") == post_id:
            return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")


@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = ( # Sets up a message
        exception.detail
        if exception.detail # Shows detail if has detail
        else "An error occurred. Please check your request and try again."
    )

    if request.url.path.startswith("/api"):
        return JSONResponse( # Returns JSON for /api route
            status_code=exception.status_code,
            content={"detail": message},
        )

    return templates.TemplateResponse( # Returns error.html for non /api routes
        request,
        "error.html",
        {   # Passes contexts to error.html via Jinja2
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )   # Passes status_code to TemplateResponse for browser


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("api/"):
        return JSONResponse( # Returns JSON for /api route
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, # RequestValidationError doesn't have status_code like Starlette
            content={"detail": exception.errors()}, # Type validation error details
        )

    return templates.TemplateResponse( # Returns error.html for non /api routes
        request,
        "error.html",
        {   # Passes contexts to error.html via Jinja2
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )   # Passes status_code to TemplateResponse for browser
