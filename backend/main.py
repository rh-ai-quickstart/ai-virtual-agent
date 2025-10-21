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
import sys
import time
from contextlib import asynccontextmanager

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from kubernetes import client, config
from starlette.exceptions import HTTPException as StarletteHTTPException

from .app.api.v1.router import api_router
from .app.api.v1.validate import router as validate_router
from .app.core.logging_config import setup_logging

load_dotenv()

# Configure centralized logging
setup_logging(level="DEBUG")
logger = logging.getLogger(__name__)


def wait_for_service_ready(
    service_name: str,
    namespace: str,
    timeout_seconds: int = 300,
    interval_seconds: int = 5,
) -> bool:
    """Wait for a Kubernetes service to be ready."""
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        try:
            config.load_incluster_config()
            core_v1 = client.CoreV1Api()
            endpoints = core_v1.read_namespaced_endpoints(
                name=service_name, namespace=namespace
            )

            if endpoints.subsets:
                for subset in endpoints.subsets:
                    if subset.addresses:
                        logger.info(
                            f"Service '{service_name}' in namespace "
                            f"'{namespace}' is ready."
                        )
                        return True

        except client.ApiException as e:
            if e.status != 404:  # Ignore 404 if service not yet created
                logger.error(f"Error checking endpoints: {e}")

        logger.info(
            f"Waiting for service '{service_name}' in namespace "
            f"'{namespace}' to be ready..."
        )
        time.sleep(interval_seconds)

    logger.warning(
        f"Timeout waiting for service '{service_name}' in namespace '{namespace}'."
    )
    return False


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

# For backward compatibility, also include some routes at the old paths
# app.include_router(api_router, prefix="/api")

# Debug router has been removed

# Include validate router at root for compatibility
app.include_router(validate_router)

# Agent templates route is now included in the main API router


class SPAStaticFiles(StaticFiles):
    """
    Custom static file handler for Single Page Application routing.

    Handles dev mode proxying to React dev server and production fallback
    to index.html for client-side routing.
    """

    async def get_response(self, path: str, scope):
        if len(sys.argv) > 1 and sys.argv[1] == "dev":
            # We are in Dev mode, proxy to the React dev server
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:8000/{path}")
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
