"""
Chat Sessions API endpoints for managing LlamaStack conversation sessions.

This module provides endpoints for creating, retrieving, and managing chat
sessions that are stored and managed by LlamaStack. Sessions track conversation state,
message history, and agent context for continuous conversations.

Key Features:
- Create new chat sessions with specific agents
- Retrieve session lists filtered by agent
- Get detailed session information including message history
- Delete chat sessions
- Automatic session metadata extraction from LlamaStack

All session data is managed by LlamaStack's session API, providing persistent
conversation state across multiple interactions.
"""

import logging
import random
import string
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...crud.chat_sessions import chat_sessions
from ...crud.virtual_agents import virtual_agents
from ...database import get_db
from ...schemas.chat_sessions import (
    ChatSessionDetail,
    ChatSessionSummary,
    CreateSessionRequest,
    DeleteSessionResponse,
)
from . import attachments
from .llama_stack.client import get_client_from_request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat_sessions", tags=["chat_sessions"])


def convert_internal_urls_to_relative(message_data: dict) -> None:
    """
    Convert internal service URLs back to relative URLs for frontend consumption.

    Args:
        message_data: Message data dict (modified in-place)
    """
    from urllib.parse import urlparse

    for content_item in message_data.get("content", []):
        if content_item.get("type") == "input_image":
            if image_url := content_item.get("image_url", ""):
                parsed = urlparse(image_url)
                # Keep only the path part of the URL
                content_item["image_url"] = parsed.path


@router.get("/", response_model=List[ChatSessionSummary])
async def get_chat_sessions(
    agent_id: str,
    request: Request,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> List[ChatSessionSummary]:
    """
    Get a list of chat sessions for a specific agent from LlamaStack.

    Retrieves session metadata including session IDs, titles, agent
    information, and timestamps. Sessions are sorted by creation date
    (newest first) and limited to the specified number of results.

    Args:
        agent_id: The unique identifier of the agent to retrieve sessions for
        limit: Maximum number of sessions to return (default: 50)

    Returns:
        List of session summary dictionaries containing:
        - id: Session identifier
        - title: Session display title
        - agent_name: Display name of the associated agent
        - created_at: Session creation timestamp
        - updated_at: Session last update timestamp

    Raises:
        HTTPException: If session retrieval fails or agent is not found
    """
    try:
        logger.info(f"Attempting to list sessions for agent {agent_id}")

        # Get sessions from database
        local_sessions = await chat_sessions.get_by_agent(
            db, agent_id=agent_id, limit=limit
        )

        logger.info(
            f"Successfully retrieved {len(local_sessions)} sessions from local database"
        )

        # Get agent name from our VirtualAgent
        agent_name = "Unknown Agent"
        try:
            agent_config = await virtual_agents.get(db, id=agent_id)
            if agent_config:
                agent_name = agent_config.name
        except Exception as e:
            logger.warning(f"Could not get agent info: {e}")

        # Convert local ChatSession objects to response format
        sessions_response = [
            ChatSessionSummary(
                id=session.id,
                title=session.title or f"Chat {session.id[:8]}...",
                agent_name=agent_name,
                created_at=(
                    session.created_at.isoformat() if session.created_at else None
                ),
                updated_at=(
                    session.updated_at.isoformat() if session.updated_at else None
                ),
                last_response_id=(
                    session.session_state.get("last_response_id")
                    if session.session_state
                    else None
                ),
            )
            for session in local_sessions
        ]

        # Sort by created_at descending (newest first) to ensure
        # consistent ordering
        sessions_response.sort(key=lambda x: x.created_at or "", reverse=True)

        return sessions_response

    except Exception as e:
        logger.error(f"Error fetching chat sessions: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch chat sessions: {str(e)}"
        )


@router.get("/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(
    session_id: str,
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 50,
    load_messages: bool = True,
) -> ChatSessionDetail:
    """
    Get detailed information for a specific chat session including message
    history.

    Retrieves the complete session data from LlamaStack including all
    conversation turns (user messages and assistant responses). If session
    retrieval fails, returns a basic session structure with empty message history.

    Args:
        session_id: The unique identifier of the session to retrieve
        agent_id: The unique identifier of the agent that owns the session

    Returns:
        Dictionary containing complete session details:
        - id: Session identifier
        - title: Session display title
        - agent_name: Display name of the associated agent
        - agent_id: Agent identifier
        - messages: List of conversation messages with role and content
        - created_at: Session creation timestamp
        - updated_at: Session last update timestamp

    Raises:
        HTTPException: If agent is not found (404) or retrieval fails (500)
    """
    try:
        logger.info(f"Fetching session {session_id} for agent {agent_id}")

        # Verify agent exists in our VirtualAgent table
        agent_config = await virtual_agents.get(db, id=agent_id)
        if not agent_config:
            logger.error(f"Agent {agent_id} not found in VirtualAgent")
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        # Get agent name from our VirtualAgent
        agent_name = agent_config.name if agent_config.name else "Unknown Agent"

        logger.info(
            f"Returning session structure for {session_id} "
            f"(Responses API doesn't store session history)"
        )

        # Try to get session from database to retrieve state
        session = await chat_sessions.get_with_agent(db, session_id=session_id)

        # Get last_response_id from session state if available
        last_response_id = None
        if session and session.session_state:
            last_response_id = session.session_state.get("last_response_id")

        # Get messages from database
        messages = []
        total_messages = 0
        has_more = False

        if session and load_messages:
            # Load from ChatMessage table
            messages, total_messages, has_more = (
                await chat_sessions.load_messages_paginated(
                    db, session_id=session_id, page=page, page_size=page_size
                )
            )

        return ChatSessionDetail(
            id=session_id,
            title=session.title if session else f"Chat {session_id[:8]}...",
            agent_name=(
                session.agent.name if session and session.agent else agent_name
            ),
            agent_id=agent_id,
            messages=messages,
            created_at=(
                session.created_at.isoformat()
                if session
                else datetime.now().isoformat()
            ),
            updated_at=(
                session.updated_at.isoformat()
                if session
                else datetime.now().isoformat()
            ),
            last_response_id=last_response_id,
            pagination={
                "page": page,
                "page_size": page_size,
                "total_messages": total_messages,
                "has_more": has_more,
                "messages_loaded": len(messages),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch chat session: {str(e)}"
        )


@router.delete("/{session_id}", response_model=DeleteSessionResponse)
async def delete_chat_session(
    session_id: str,
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DeleteSessionResponse:
    """
    Delete a chat session from LlamaStack.

    Permanently removes the specified chat session and all associated
    conversation history from LlamaStack. This operation cannot be undone.

    Args:
        session_id: The unique identifier of the session to delete
        agent_id: The unique identifier of the agent that owns the session

    Returns:
        Dictionary containing the result of the delete operation from
        LlamaStack

    Raises:
        HTTPException: If agent is not found (404) or deletion fails (500)
    """
    try:
        # Verify agent exists in our VirtualAgent table
        agent_config = await virtual_agents.get(db, id=agent_id)
        if not agent_config:
            logger.error(f"Agent {agent_id} not found in VirtualAgent")
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        # Delete session and related data
        deleted = await chat_sessions.delete_session(db, session_id=session_id)

        if not deleted:
            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )

        # Clean up attachments (non-critical, don't fail if this fails)
        try:
            attachments.delete_attachments_for_session(session_id)
            logger.info(f"Successfully deleted session {session_id} and attachments")
        except Exception as attachment_error:
            logger.warning(
                f"Failed to delete attachments for session {session_id}: "
                f"{attachment_error}"
            )
            logger.info(
                f"Successfully deleted session {session_id} "
                f"(attachments cleanup failed)"
            )

        return DeleteSessionResponse(
            message=f"Session {session_id} deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete chat session: {str(e)}"
        )


@router.post("/", response_model=ChatSessionDetail)
async def create_chat_session(
    sessionRequest: CreateSessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionDetail:
    """
    Create a new chat session for an agent using LlamaStack.

    Creates a new conversation session associated with a specific agent. If no
    session name is provided, generates a unique name with timestamp and random
    component. The session is immediately available for chat interactions.

    Args:
        request: CreateSessionRequest containing:
            - agent_id: The unique identifier of the agent
            - session_name: Optional custom name for the session

    Returns:
        Dictionary containing the created session details:
        - id: Generated session identifier
        - title: Session name/title
        - agent_name: Display name of the associated agent
        - agent_id: Agent identifier
        - messages: Empty list (new session)
        - created_at: Session creation timestamp
        - updated_at: Session creation timestamp

    Raises:
        HTTPException: If agent is not found (404) or session creation
                       fails (500)
    """
    try:
        # Verify agent exists in our VirtualAgent table
        agent_config = await virtual_agents.get(db, id=sessionRequest.agent_id)
        if not agent_config:
            logger.error(f"Agent {sessionRequest.agent_id} not found in VirtualAgent")
            raise HTTPException(
                status_code=404,
                detail=f"Agent {sessionRequest.agent_id} not found",
            )
        logger.info(f"Found agent config: {agent_config.id}")

        # Generate unique session name
        if sessionRequest.session_name:
            session_name = sessionRequest.session_name
        else:
            # Generate unique name with timestamp and random component
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            random_suffix = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=4)
            )
            session_name = f"Chat-{timestamp}-{random_suffix}"

        # Create session locally without LlamaStack
        session_id = uuid.uuid4()
        logger.info(f"Generated local session ID: {session_id}")

        # Get agent name for display from our VirtualAgent
        agent_name = agent_config.name if agent_config else "Unknown Agent"

        # Create ChatSession record in database
        session_data = {
            "id": session_id,
            "title": session_name,
            "agent_id": sessionRequest.agent_id,
            "session_state": {
                "last_response_id": None,  # No responses yet
            },
        }

        new_session = await chat_sessions.create_session(db, session_data=session_data)

        logger.info(f"Created ChatSession record for {session_id}")

        return ChatSessionDetail(
            id=session_id,
            title=session_name,
            agent_name=agent_name,
            agent_id=sessionRequest.agent_id,
            messages=[],
            created_at=new_session.created_at.isoformat(),
            updated_at=new_session.updated_at.isoformat(),
            last_response_id=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create chat session: {str(e)}"
        )


@router.get("/debug/{agent_id}")
async def debug_session_listing(agent_id: str, request: Request):
    """
    Debug endpoint for troubleshooting session listing functionality.

    This development/debugging endpoint provides detailed information about
    session listing operations, including agent verification, session resource
    inspection, and method execution results. Used for diagnosing issues
    with LlamaStack session API interactions.

    Args:
        agent_id: The unique identifier of the agent to debug

    Returns:
        Dictionary containing debug information:
        - agent_id: The agent being debugged
        - response_type: Type of response from LlamaStack
        - response_value: Raw response value
        - sessions_count: Number of sessions found
        - sessions: List of session data
        - error: Error message if operation fails

    Note:
        This endpoint should only be used for development and debugging
        purposes.
    """
    try:
        logger.info(f"=== DEBUG SESSION LISTING FOR AGENT {agent_id} ===")

        # Test 1: Check if agent exists
        client = get_client_from_request(request)
        try:
            agent = await client.agents.retrieve(agent_id=agent_id)
            logger.info(f"✅ Agent exists: {agent.agent_id}")
        except Exception as e:
            logger.error(f"❌ Agent not found: {e}")
            return {"error": f"Agent not found: {e}"}

        # Test 2: Check session resource type
        session_resource = client.agents.session
        logger.info(f"Session resource type: {type(session_resource)}")
        logger.info(
            "Session resource methods: "
            f"{[m for m in dir(session_resource) if not m.startswith('_')]}"
        )

        # Test 3: Try to call list method
        try:
            sessions_response = await client.agents.session.list(agent_id=agent_id)
            logger.info("✅ List method called successfully")
            logger.info(f"Response type: {type(sessions_response)}")
            logger.info(f"Response value: {sessions_response}")
            logger.info(f"Response dir: {dir(sessions_response)}")

            # Try to extract sessions
            if hasattr(sessions_response, "sessions"):
                sessions = sessions_response.sessions
                logger.info(f"Found sessions attr: {sessions}")
            elif isinstance(sessions_response, list):
                sessions = sessions_response
                logger.info(f"Response is direct list: {sessions}")
            else:
                sessions = []
                logger.info("No sessions found in response")

            return {
                "agent_id": agent_id,
                "response_type": str(type(sessions_response)),
                "response_value": str(sessions_response),
                "sessions_count": len(sessions) if sessions else 0,
                "sessions": sessions if sessions else [],
            }

        except Exception as e:
            logger.error(f"❌ List method failed: {e}")
            logger.error(f"Exception type: {type(e)}")
            return {"error": f"List method failed: {e}"}

    except Exception as e:
        logger.error(f"❌ Debug failed: {e}")
        return {"error": f"Debug failed: {e}"}
