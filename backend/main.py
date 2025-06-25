"""
FastAPI main application module for AI Virtual Assistant.

This module initializes the FastAPI application, configures middleware,
registers API routes, and handles static file serving for the frontend.
The app provides a complete REST API for managing virtual assistants,
knowledge bases, tools, and chat interactions.
"""

import asyncio
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

from .database import AsyncSessionLocal
from .routes import (
    chat_sessions,
    guardrails,
    knowledge_bases,
    llama_stack,
    mcp_servers,
    model_servers,
    tools,
    users,
    validate,
    virtual_assistants,
)
from .utils.logging_config import get_logger, setup_logging

load_dotenv()

# Configure centralized logging
setup_logging(level="INFO")
logger = get_logger(__name__)


def get_incluster_namespace() -> str:
    """Get the current Kubernetes namespace."""
    try:
        with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace") as file:
            return file.read().strip()
    except Exception:
        return "default"


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
                            f"Service '{service_name}' in namespace \
                                '{namespace}' is ready."
                        )
                        return True

        except client.ApiException as e:
            if e.status != 404:  # Ignore 404 if service not yet created
                logger.error(f"Error checking endpoints: {e}")

        logger.info(
            f"Waiting for service '{service_name}' in namespace \
                '{namespace}' to be ready..."
        )
        time.sleep(interval_seconds)

    logger.warning(
        f"Timeout waiting for service '{service_name}' in namespace '{namespace}'."
    )
    return False


async def sync_all_services():
    """Sync all external services (MCP servers, model servers, knowledge bases)."""
    sync_operations = [
        ("MCP servers", mcp_servers.sync_mcp_servers),
        ("Model servers", model_servers.sync_model_servers),
        ("Knowledge bases", knowledge_bases.sync_knowledge_bases),
    ]

    for service_name, sync_func in sync_operations:
        try:
            async with AsyncSessionLocal() as session:
                await sync_func(session)
            logger.info(f"Successfully synced {service_name}")
        except Exception as e:
            logger.error(f"Failed to sync {service_name}: {str(e)}")


async def startup_tasks():
    """Run all startup tasks after the server is ready."""
    logger.info("Starting post-startup tasks...")

    service_name = "ai-virtual-assistant"
    namespace = get_incluster_namespace()

    if wait_for_service_ready(service_name, namespace):
        logger.info("Service is ready, proceeding with sync operations.")
        await sync_all_services()
        logger.info("All startup tasks completed successfully!")
    else:
        logger.error("Service did not become ready within the timeout.")


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

app.include_router(validate.router)
app.include_router(users.router, prefix="/api")
app.include_router(mcp_servers.router, prefix="/api")
app.include_router(tools.router, prefix="/api")
app.include_router(knowledge_bases.router, prefix="/api")
app.include_router(virtual_assistants.router, prefix="/api")
app.include_router(guardrails.router, prefix="/api")
app.include_router(model_servers.router, prefix="/api")
app.include_router(llama_stack.router, prefix="/api")
app.include_router(chat_sessions.router, prefix="/api")


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
    "/", SPAStaticFiles(directory="backend/public", html=True), name="spa-static-files"
)
