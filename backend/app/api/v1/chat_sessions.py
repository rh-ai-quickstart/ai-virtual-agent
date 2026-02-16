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
from datetime import datetime, timezone
from typing import List
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.llamastack import (
    get_client_from_request,
)
from ...crud.chat_sessions import chat_sessions
from ...crud.virtual_agents import virtual_agents
from ...database import get_db
from ...schemas.chat_sessions import (
    ChatSession,
    ConversationMessagesResponse,
    CreateSessionRequest,
    DeleteSessionResponse,
)
from . import attachments
from .users import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat_sessions", tags=["chat_sessions"])


def _process_content_item(content_item: dict | str, role: str) -> dict | None:
    """Process a single content item from a message."""
    # Handle string content (simple text format)
    if isinstance(content_item, str):
        return {
            "type": "input_text" if role == "user" else "output_text",
            "text": content_item,
        }

    # Handle dict content (structured format)
    content_type = content_item.get("type")

    if content_type in ("input_text", "output_text"):
        return {
            "type": "input_text" if role == "user" else "output_text",
            "text": content_item.get("text", ""),
        }
    elif content_type == "input_image":
        image_url = content_item.get("image_url", "")
        # Convert internal URLs to relative paths for frontend
        if image_url:
            parsed = urlparse(image_url)
            image_url = parsed.path
        return {
            "type": "input_image",
            "image_url": image_url,
        }
    return None


def _process_tool_call_item(item_dict: dict) -> dict:
    """Process a tool call item (mcp_call, file_search_call, web_search_call)."""
    item_type = item_dict.get("type")

    # Tool call field mappings: (name_field, server_label_field, args_field, output_field)
    tool_map = {
        "mcp_call": ("name", "server_label", "arguments", "output"),
        "file_search_call": ("knowledge_search", "llamastack", "queries", "results"),
        "web_search_call": ("web_search", "llamastack", "query", None),
    }

    name_field, server_field, args_field, output_field = tool_map[item_type]

    # For mcp_call, name/server_label are fields; for others, they're literal values
    name = item_dict.get(name_field) if item_type == "mcp_call" else name_field
    server_label = (
        item_dict.get(server_field) if item_type == "mcp_call" else server_field
    )

    args_val = item_dict.get(args_field)
    output_val = item_dict.get(output_field) if output_field else None

    # Format output
    output = (
        f"Tool execution {item_dict.get('status', 'completed')}"
        if output_field is None
        else (str(output_val) if output_val else "No results found")
    )

    return {
        "type": "tool_call",
        "id": item_dict.get("id"),
        "name": name,
        "server_label": server_label,
        "arguments": str(args_val) if args_val else None,
        "output": output,
        "error": item_dict.get("error"),
        "status": "failed" if item_dict.get("error") else "completed",
    }


@router.get("/", response_model=List[ChatSession])
async def get_chat_sessions(
    agent_id: str,
    request: Request,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> List[ChatSession]:
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

        # Get sessions from database filtered by user
        local_sessions = await chat_sessions.get_by_agent(
            db, agent_id=agent_id, user_id=current_user.id, limit=limit
        )

        logger.info(
            f"Successfully retrieved {len(local_sessions)} sessions from local database"
        )

        # Convert local ChatSession objects to response format
        sessions_response = [
            ChatSession(
                id=session.id,
                title=session.title or f"Chat {str(session.id)[:8]}...",
                agent_id=session.agent_id,
                conversation_id=session.conversation_id,
                created_at=session.created_at.isoformat(),
                updated_at=session.updated_at.isoformat(),
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


@router.get("/{session_id}", response_model=ChatSession)
async def get_chat_session(
    session_id: str,
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChatSession:
    """
    Get session metadata (messages are managed by LlamaStack Conversations API).

    Args:
        session_id: The unique identifier of the session to retrieve
        agent_id: The unique identifier of the agent that owns the session

    Returns:
        Session metadata including ID, title, agent_id, conversation_id, and timestamps

    Raises:
        HTTPException: If session is not found (404) or retrieval fails (500)
    """
    try:
        logger.info(f"Fetching session {session_id} for agent {agent_id}")

        # Get session from database (filtered by user)
        session = await chat_sessions.get_with_agent(
            db, session_id=session_id, user_id=current_user.id
        )

        if not session:
            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )

        return ChatSession(
            id=session.id,
            title=session.title or f"Chat {str(session.id)[:8]}...",
            agent_id=session.agent_id,
            conversation_id=session.conversation_id,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch chat session: {str(e)}"
        )


@router.get("/{session_id}/messages", response_model=ConversationMessagesResponse)
async def get_conversation_messages(
    session_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ConversationMessagesResponse:
    """
    Get messages for a conversation from LlamaStack.

    Args:
        session_id: The unique identifier of the session

    Returns:
        List of messages from the LlamaStack conversation

    Raises:
        HTTPException: If session is not found (404) or retrieval fails (500)
    """
    try:
        logger.info(f"Fetching messages for session {session_id}")

        # Get session from database (filtered by user)
        session = await chat_sessions.get_with_agent(
            db, session_id=session_id, user_id=current_user.id
        )

        if not session:
            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )

        # If no conversation_id yet, return empty messages
        if not session.conversation_id:
            logger.info(
                f"No conversation_id for session {session_id}, returning empty messages"
            )
            return ConversationMessagesResponse(messages=[])

        # Fetch messages from LlamaStack
        client = get_client_from_request(request)
        try:
            # List items in the conversation
            # The include parameter is required (empty list to get default fields)
            # Available include values are for extra fields like:
            # "file_search_call.results", "reasoning.encrypted_content", etc.
            items_response = await client.conversations.items.list(
                conversation_id=session.conversation_id,
                limit=100,
                order="asc",
            )

            # Convert conversation items to messages, grouping tool calls with their responses
            messages = []
            pending_tool_calls = (
                []
            )  # Accumulate tool calls until we see the assistant message

            logger.info(f"Total items received: {len(items_response.data)}")

            for item in items_response.data:
                item_dict = jsonable_encoder(item)
                item_type = item_dict.get("type")

                logger.debug(
                    f"Processing item: type={item_type}, id={item_dict.get('id')}"
                )

                # Skip tool discovery items
                if item_type == "mcp_list_tools":
                    logger.debug("Skipping mcp_list_tools item")
                    continue

                if item_type == "message":
                    # Process user or assistant message
                    role = item_dict.get("role")
                    message_id = item_dict.get("id")

                    # Process content items
                    content_items = []
                    raw_content = item_dict.get("content", [])

                    # Handle both string and list content
                    # When using simple format (e.g., with guardrails), content is a string
                    if isinstance(raw_content, str):
                        raw_content = [raw_content]

                    for content_item in raw_content:
                        processed = _process_content_item(content_item, role)
                        if processed:
                            content_items.append(processed)

                    logger.debug(
                        f"Message: role={role}, id={message_id}, "
                        f"content_items={len(content_items)}, "
                        f"pending_tool_calls={len(pending_tool_calls)}"
                    )

                    # If this is a user message and we have pending tool calls,
                    # drop them (orphaned - assistant response not persisted)
                    if role == "user" and pending_tool_calls:
                        logger.warning(
                            f"Dropping {len(pending_tool_calls)} orphaned tool calls "
                            f"before user message {message_id}"
                        )
                        pending_tool_calls = []

                    if content_items:
                        msg = {
                            "type": "message",
                            "role": role,
                            "content": content_items,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }

                        # If assistant message, attach any pending tool calls
                        if role == "assistant" and pending_tool_calls:
                            msg["tool_calls"] = pending_tool_calls
                            logger.info(
                                f"Attached {len(pending_tool_calls)} tool calls to "
                                f"assistant message {message_id}"
                            )
                            logger.debug(
                                f"Tool calls: "
                                f"{[tc['name'] for tc in pending_tool_calls]}"
                            )
                            pending_tool_calls = []

                        logger.debug(
                            f"Appending message: role={role}, "
                            f"has_tool_calls={'tool_calls' in msg}"
                        )
                        messages.append(msg)

                elif item_type in ("mcp_call", "file_search_call", "web_search_call"):
                    # Process tool call
                    tool_entry = _process_tool_call_item(item_dict)
                    logger.debug(
                        f"Adding tool call: name={tool_entry['name']}, "
                        f"id={tool_entry['id']}, status={tool_entry['status']}"
                    )
                    pending_tool_calls.append(tool_entry)

            # Check for orphaned tool calls at the end
            if pending_tool_calls:
                logger.warning(
                    f"Dropping {len(pending_tool_calls)} orphaned tool calls at end "
                    f"of conversation {session.conversation_id}"
                )

            logger.info(
                f"Retrieved {len(messages)} messages for conversation "
                f"{session.conversation_id}"
            )
            logger.debug(
                f"Final messages being sent to frontend: {len(messages)} messages"
            )
            for idx, msg in enumerate(messages):
                logger.debug(
                    f"  Message {idx}: role={msg.get('role')}, "
                    f"has_tool_calls={'tool_calls' in msg}, "
                    f"content_items={len(msg.get('content', []))}"
                )

            return ConversationMessagesResponse(messages=messages)

        except Exception as llamastack_error:
            logger.error(
                f"LlamaStack error retrieving conversation: {llamastack_error}"
            )
            # If conversation doesn't exist in LlamaStack, return empty messages
            return ConversationMessagesResponse(messages=[])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching conversation messages: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch conversation messages: {str(e)}"
        )


@router.delete("/{session_id}", response_model=DeleteSessionResponse)
async def delete_chat_session(
    session_id: str,
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
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

        # Delete session and related data (only if user owns it)
        deleted = await chat_sessions.delete_session(
            db, session_id=session_id, user_id=current_user.id
        )

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


@router.post("/", response_model=ChatSession)
async def create_chat_session(
    sessionRequest: CreateSessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> ChatSession:
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

        # Create session locally (conversation will be created by LlamaStack on first message)
        session_id = uuid.uuid4()
        logger.info(f"Generated local session ID: {session_id}")

        # Create ChatSession record in database
        session_data = {
            "id": session_id,
            "title": session_name,
            "agent_id": sessionRequest.agent_id,
            "user_id": current_user.id,
            "conversation_id": None,  # Will be set when first message is sent
        }

        new_session = await chat_sessions.create_session(db, session_data=session_data)

        logger.info(f"Created ChatSession record for {session_id}")

        return ChatSession(
            id=session_id,
            title=session_name,
            agent_id=sessionRequest.agent_id,
            conversation_id=None,
            created_at=new_session.created_at.isoformat(),
            updated_at=new_session.updated_at.isoformat(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating chat session: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create chat session: {str(e)}"
        )
