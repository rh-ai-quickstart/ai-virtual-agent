"""LlamaStack Integration API submodules."""

from fastapi import APIRouter

from .mcp_servers import router as mcp_servers_router
from .models import router as models_router
from .providers import router as providers_router
from .shields import router as shields_router
from .tools import router as tools_router

router = APIRouter()

# Include submodule routers
router.include_router(models_router, prefix="/models", tags=["models"])
router.include_router(tools_router, prefix="/tools", tags=["tools"])
router.include_router(shields_router, prefix="/shields", tags=["shields"])
router.include_router(providers_router, prefix="/providers", tags=["providers"])
router.include_router(mcp_servers_router, prefix="/mcp_servers", tags=["mcp_servers"])
