"""
Chat History API endpoints for managing conversation records.

This module provides CRUD operations for chat history records, storing
conversation data between users and virtual agents. It maintains
persistent records of chat interactions for audit trails and conversation
continuity.

Key Features:
- Store and retrieve chat conversation history
- Associate chat records with specific agents and users
- Support for message and response storage
- Conversation audit and retrieval capabilities
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/chat_history", tags=["chat_history"])


@router.post(
    "/", response_model=schemas.ChatHistoryRead, status_code=status.HTTP_201_CREATED
)
async def create_chat_history(
    item: schemas.ChatHistoryCreate, db: AsyncSession = Depends(get_db)
):
    """
    Create a new chat history record.

    This endpoint stores a new chat interaction record including the user's
    message and the assistant's response for future reference and audit.

    Args:
        item: Chat history data including agent_id, user_id, message, and response
        db: Database session dependency

    Returns:
        schemas.ChatHistoryRead: The created chat history record

    Raises:
        HTTPException: If creation fails or validation errors occur
    """
    db_item = models.ChatHistory(**item.dict())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


@router.get("/", response_model=List[schemas.ChatHistoryRead])
async def read_chat_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.ChatHistory))
    return result.scalars().all()


@router.get("/{chat_id}", response_model=schemas.ChatHistoryRead)
async def read_chat_item(chat_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.ChatHistory).where(models.ChatHistory.id == chat_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Chat history not found")
    return item


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_item(chat_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(models.ChatHistory).where(models.ChatHistory.id == chat_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Chat history not found")
    await db.delete(item)
    await db.commit()
    return None
