from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

app = FastAPI()


posts: list[dict] = [
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


templates = Jinja2Templates(directory="templates")

@app.get("/", include_in_schema=False) # False hides endpoint from /docs
@app.get("/posts", include_in_schema=False)
def home(request: Request): # Rquest is required by Jinja2
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": posts, "title": "Home"},
    ) # Injects the JSON snippets for Jinja2

# @app.get("/api/posts")
# def get_post():
#     return posts
