"""
main.py
FinBuddy — Advanced Generative AI Personal Finance Copilot.

Run locally:
    uvicorn main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.db import setup_database
from routers.auth import router as auth_router
from routers.api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB tables and persistent indexes on startup."""
    setup_database()
    yield


app = FastAPI(
    title="FinBuddy",
    description="Advanced Gen AI Autonomous Personal Finance Copilot",
    version="3.0.0",
    lifespan=lifespan,
)

# Static asset serving
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register modular routers
app.include_router(auth_router)
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
