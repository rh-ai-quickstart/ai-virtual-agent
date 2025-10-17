"""
Knowledge Base API endpoints for managing vector databases and knowledge sources.
"""

import logging
import os
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.knowledge_bases import knowledge_bases
from ...database import get_db
from ...schemas import KnowledgeBaseCreate, KnowledgeBaseResponse
from .llama_stack.client import get_client_from_request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge_bases", tags=["knowledge_bases"])


async def create_knowledge_base_internal(
    kb: KnowledgeBaseCreate, db: AsyncSession
) -> KnowledgeBaseResponse:
    """
    Internal utility function to create a knowledge base.
    Can be used by API endpoints and other services without dependency injection issues.
    """
    await create_ingestion_pipeline(kb)
    db_kb = await knowledge_bases.create(db, obj_in=kb)
    db_kb.status = await get_pipeline_status(db_kb.vector_store_name)
    return db_kb


@router.post(
    "/", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED
)
async def create_knowledge_base(
    kb: KnowledgeBaseCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new knowledge base."""
    return await create_knowledge_base_internal(kb, db)


@router.get("/", response_model=List[KnowledgeBaseResponse])
async def read_knowledge_bases(request: Request, db: AsyncSession = Depends(get_db)):
    """Retrieve all knowledge bases from the database."""
    # Update vector_store_ids by matching with LlamaStack vector stores
    await update_vector_store_ids(request, db)

    # Get all knowledge bases
    kbs = await knowledge_bases.get_multi(db)

    # Get pipeline status for each knowledge base
    for kb in kbs:
        kb.status = await get_pipeline_status(kb.vector_store_name)

    return kbs


@router.get("/{vector_store_name}", response_model=KnowledgeBaseResponse)
async def read_knowledge_base(
    vector_store_name: str, db: AsyncSession = Depends(get_db)
):
    """Retrieve a specific knowledge base by its vector database name."""
    kb = await knowledge_bases.get_by_vector_store_name(
        db, vector_store_name=vector_store_name
    )
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    kb.status = await get_pipeline_status(kb.vector_store_name)
    return kb


@router.delete("/{vector_store_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    vector_store_name: str, request: Request, db: AsyncSession = Depends(get_db)
):
    """Delete a knowledge base from both the database and LlamaStack."""
    kb = await knowledge_bases.get_by_vector_store_name(
        db, vector_store_name=vector_store_name
    )
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    kb_name = kb.name  # Store name before deletion

    # First, try to delete from LlamaStack using vector_store_id if available
    if kb.vector_store_id:
        client = get_client_from_request(request)
        try:
            logger.info(
                f"Deleting knowledge base from LlamaStack using ID: {kb.vector_store_id}"
            )
            await client.vector_stores.delete(kb.vector_store_id)
            logger.info(f"Successfully deleted from LlamaStack: {kb.vector_store_id}")
        except Exception as e:
            logger.warning(f"Failed to delete from LlamaStack: {str(e)}")
    else:
        logger.info(
            f"No vector_store_id found for {vector_store_name}, skipping LlamaStack deletion"
        )

    try:
        await delete_ingestion_pipeline(vector_store_name)
    except Exception as e:
        logger.warning(f"failed to delete ingestion pipeline: {str(e)}")

    # Then delete from database - CRUD handles transaction
    await knowledge_bases.remove(db, id=kb.id)

    logger.info(f"Successfully deleted knowledge base from database: {kb_name}")
    return None


async def create_ingestion_pipeline(kb: KnowledgeBaseCreate):
    """Create ingestion pipeline via external API."""
    add_pipeline = os.environ["INGESTION_PIPELINE_URL"] + "/add"
    data = kb.pipeline_model_dict()
    logger.info(f"Creating pipeline at {add_pipeline} {data=}")
    async with httpx.AsyncClient() as client:
        response = await client.post(add_pipeline, json=data)
        response.raise_for_status()


async def delete_ingestion_pipeline(vector_store_name: str):
    """Delete ingestion pipeline via external API."""
    del_pipeline = os.environ["INGESTION_PIPELINE_URL"] + "/delete"
    data = {"pipeline_name": vector_store_name}
    logger.info(f"Deleting pipeline with {del_pipeline} {data=}")
    async with httpx.AsyncClient() as client:
        response = await client.delete(del_pipeline, params=data)
        response.raise_for_status()


async def update_vector_store_ids(request: Request, db: AsyncSession):
    """Update vector_store_id fields by matching with LlamaStack vector stores."""
    try:
        client = get_client_from_request(request)
        vector_stores = await client.vector_stores.list()

        # Create a mapping of vector store names to IDs
        vs_name_to_id = {vs.name: vs.id for vs in vector_stores.data}

        # Get knowledge bases that exist in LlamaStack vector stores
        kbs = await knowledge_bases.get_multi(db)

        # Update knowledge bases that need vector_store_id updates
        for kb in kbs:
            if kb.vector_store_name in vs_name_to_id:
                vs_id = vs_name_to_id[kb.vector_store_name]
                if kb.vector_store_id != vs_id:
                    await knowledge_bases.update(
                        db, db_obj=kb, obj_in={"vector_store_id": vs_id}
                    )
                    logger.info(
                        f"Updated vector_store_id for {kb.vector_store_name}: {vs_id}"
                    )

    except Exception as e:
        logger.warning(f"Failed to update vector_store_ids from LlamaStack: {str(e)}")


async def get_pipeline_status(pipeline_name: str) -> str:
    """Get ingestion pipeline status via external API."""
    status_endpoint = os.environ["INGESTION_PIPELINE_URL"] + "/status"
    data = {"pipeline_name": pipeline_name}
    logger.info(f"Fetching pipeline status from {status_endpoint} {data=}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(status_endpoint, params=data)
            response.raise_for_status()
            return response.json().get("state", "unknown")
        except Exception as e:
            logger.error(
                f"could not fetch pipeline status for {pipeline_name}: {str(e)}"
            )
            return "unknown"
