"""Tools API endpoints for LlamaStack."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

from .client import get_client_from_request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[Dict[str, Any]])
async def get_tools(request: Request):
    """
    Retrieve all available MCP (Model Context Protocol) servers from LlamaStack.
    """
    client = get_client_from_request(request)
    try:
        servers = await client.toolgroups.list()
        return [
            {
                "id": str(server.identifier),
                "name": server.provider_resource_id,
                "title": server.provider_id,
                "toolgroup_id": str(server.identifier),
            }
            for server in servers
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
