"""
Chat API endpoints for streaming conversations with LlamaStack agents.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.virtual_agents import virtual_agents
from ...database import get_db
from ...schemas import ChatRequest
from ...services.chat import ChatService
from .users import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat")
async def chat(
    chat_request: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Main chat endpoint for streaming conversations with LlamaStack agents.

    Handles real-time chat interactions by streaming responses from LlamaStack
    agents while maintaining session state.
    """
    try:
        logger.info(f"Received chatRequest: {chat_request.model_dump()}")

        # Validate agent exists early to return proper 404 error for invalid agents
        agent = await virtual_agents.get_with_template(
            db, id=chat_request.virtualAgentId
        )
        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Virtual agent {chat_request.virtualAgentId} not found",
            )

        # Create chat service with the database session
        chat_service = ChatService(request, db, user_id=current_user.id)

        async def chat_stream():
            try:
                async for chunk in chat_service.stream(
                    chat_request.virtualAgentId,
                    chat_request.sessionId or "default",
                    chat_request.message.content,
                ):
                    yield f"data: {chunk}\n\n"

                yield "data: [DONE]\n\n"

            except Exception as e:
                logger.error(f"Error in stream: {str(e)}")
                yield f'data: {{"type":"error","content":"Error: {str(e)}"}}\n\n'

        return StreamingResponse(chat_stream(), media_type="text/event-stream")

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise
