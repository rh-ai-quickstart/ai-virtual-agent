"""Shields API endpoints for LlamaStack."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

from .client import get_client_from_request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[Dict[str, Any]])
async def get_shields(request: Request):
    """
    Retrieve all available safety shields from LlamaStack.
    """
    client = get_client_from_request(request)
    try:
        shields = await client.shields.list()
        shields_list = []
        for shield in shields:
            shield = {
                "id": str(shield.identifier),
                "name": shield.provider_resource_id,
                "model_type": shield.type,
            }
            shields_list.append(shield)
        return shields_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
