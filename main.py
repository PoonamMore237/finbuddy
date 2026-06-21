"""
main.py
FinBuddy — FastAPI entry point.

Run locally:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.db import setup_database
from routers.auth import router as auth_router
from routers.api import router as api_router

app = FastAPI(
    title="FinBuddy",
    description="AI-powered personal finance assistant",
    version="2.0.0",
)

# Serve CSS, JS, images from /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register routers
app.include_router(auth_router)
app.include_router(api_router)


@app.on_event("startup")
def startup():
    """Initialize DB tables on first run."""
    setup_database()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
