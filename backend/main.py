"""
FastAPI main application module for AI Virtual Agent Quickstart.

This module initializes and configures the FastAPI application, including
middleware, routes, database connections, and API documentation. It serves as
the entry point for the backend API.

The app provides a complete REST API for managing virtual agents,
knowledge bases, chat sessions, and integration with LlamaStack for AI
capabilities.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .app.api.v1.router import api_router
from .app.api.v1.validate import router as validate_router
from .app.core.auth import is_local_dev_mode
from .app.core.logging_config import setup_logging

load_dotenv()

# Configure centralized logging
setup_logging(level="DEBUG")
logger = logging.getLogger(__name__)


async def ensure_templates_available():
    """Ensure templates are populated - runs in all environments."""
    from .app.core.template_startup import ensure_templates_populated

    try:
        await ensure_templates_populated()
        logger.info("Template population completed")
    except Exception as e:
        logger.error(f"Failed to populate templates: {str(e)}")


async def startup_tasks():
    """Run all startup tasks after the server is ready."""
    logger.info("Starting post-startup tasks...")

    # Always ensure templates are available (no external dependencies)
    await ensure_templates_available()

    logger.info("All startup tasks completed successfully!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI app is starting up...")

    # Schedule startup tasks to run after server is ready
    async def run_startup_tasks():
        # Wait a bit for the server to finish starting up
        await asyncio.sleep(3)
        logger.info("Running post-startup tasks...")
        try:
            await startup_tasks()
        except Exception as e:
            logger.error(f"Error running post-startup tasks: {e}")

    # Create background task for startup
    task = asyncio.create_task(run_startup_tasks())
    logger.info("Startup event completed, server will start accepting connections")

    yield

    # Shutdown
    logger.info("FastAPI app is shutting down...")
    # Cancel the background task if it's still running
    if not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)

origins = ["*"]  # Update this with the frontend domain in production

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the main API router with all endpoints
app.include_router(api_router, prefix="/api/v1")

# Include debug router only in local development mode
if is_local_dev_mode():
    from .app.api.v1.debug import router as debug_router

    app.include_router(debug_router, prefix="/api")

# Include validate router at root for compatibility
app.include_router(validate_router)


@app.get("/admin/coverage", include_in_schema=False)
async def get_coverage():
    """Save and download coverage data file (dev/test only)."""
    # First, save the coverage data
    if os.getenv("ENABLE_COVERAGE") == "true":
        try:
            import coverage

            cov = coverage.Coverage.current()
            if cov:
                cov.save()
        except Exception:
            pass  # Continue anyway, file might still exist

    # Then return the file
    coverage_file = Path("/app/.coverage.integration")
    if coverage_file.exists():
        return FileResponse(
            path=str(coverage_file),
            filename=".coverage.integration",
            media_type="application/octet-stream",
        )
    raise HTTPException(status_code=404, detail="Coverage file not found")


class SPAStaticFiles(StaticFiles):
    """
    Custom static file handler for Single Page Application routing.

    Handles dev mode proxying to React dev server and production fallback
    to index.html for client-side routing.
    """

    async def get_response(self, path: str, scope):
        if len(sys.argv) > 1 and sys.argv[1] == "dev":
            # We are in Dev mode, proxy to the React dev server
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(f"http://localhost:8000/{path}")
            return Response(response.text, status_code=response.status_code)
        else:
            try:
                return await super().get_response(path, scope)
            except (HTTPException, StarletteHTTPException) as ex:
                if ex.status_code == 404:
                    return await super().get_response("index.html", scope)
                else:
                    raise ex


app.mount(
    "/",
    SPAStaticFiles(directory="backend/public", html=True),
    name="spa-static-files",
)
