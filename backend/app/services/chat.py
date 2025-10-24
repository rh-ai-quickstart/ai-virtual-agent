"""
Chat service for handling LlamaStack conversations with virtual agent configurations.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.llamastack import get_client_from_request
from ..crud.virtual_agents import virtual_agents
from ..models import ChatMessage, ChatSession

logger = logging.getLogger(__name__)


def expand_image_url(content_item: Dict[str, Any]) -> None:
    """
    Expand relative image URL to full URL for LlamaStack inference service.

    Args:
        content_item: Content item that may contain a relative image URL
                     (modified in-place)
    """
    if content_item.get("type") == "input_image" and content_item.get("image_url"):
        image_url = content_item["image_url"]
        if image_url.startswith("/"):
            attachments_endpoint = os.getenv(
                "ATTACHMENTS_INTERNAL_API_ENDPOINT", "http://ai-virtual-agent:8000"
            )
            content_item["image_url"] = f"{attachments_endpoint}{image_url}"


async def build_responses_tools(
    tools: Optional[List[Any]],
    vector_store_ids: Optional[List[str]],
    request: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """
    Convert virtual agent tools to OpenAI Responses API compatible format.

    The Responses API uses OpenAI-compatible tool patterns:
    - file_search for RAG/knowledge base queries
    - web_search for web searches
    - code_interpreter for code execution

    Args:
        tools: List of virtual agent tools to convert
        vector_store_ids: List of LlamaStack vector store IDs for file_search tools

    Returns:
        List of tools in OpenAI Responses API format
    """
    responses_tools = []

    if not tools:
        return responses_tools

    for tool_info in tools:
        tool_id = tool_info["toolgroup_id"]

        # Convert to OpenAI Responses API tool format
        if tool_id == "builtin::rag":
            if vector_store_ids:
                responses_tools.append(
                    {"type": "file_search", "vector_store_ids": vector_store_ids}
                )
        elif "web_search" in tool_id or "search" in tool_id:
            responses_tools.append({"type": "web_search"})
        elif tool_id.startswith("mcp::"):
            # For MCP tools, we need to get server info from LlamaStack
            if request:
                try:
                    client = get_client_from_request(request)
                    # Get all toolgroups to find the one matching our tool
                    toolgroups = await client.toolgroups.list()
                    for toolgroup in toolgroups:
                        if str(toolgroup.identifier) == tool_id:
                            responses_tools.append(
                                {
                                    "type": "mcp",
                                    "server_label": toolgroup.args.get(
                                        "name", str(toolgroup.identifier)
                                    ),
                                    "server_url": toolgroup.mcp_endpoint.uri,
                                }
                            )
                            break
                except Exception as e:
                    logger.warning(f"Failed to get MCP server info for {tool_id}: {e}")
                    # Fallback: skip this tool if we can't get server info
            else:
                logger.warning(
                    f"Cannot get MCP server info for {tool_id} without request object"
                )
        else:
            # For other tools, try to use the toolgroup_id directly
            responses_tools.append({"type": tool_id})

    return responses_tools


async def get_conversation_history(
    db: AsyncSession, session_id: str
) -> List[Dict[str, Any]]:
    """
    Retrieve conversation history for a session in OpenAI message format.

    Args:
        db: Database session
        session_id: Chat session ID

    Returns:
        List of messages in OpenAI format for LlamaStack
    """
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()

    conversation = []
    for message in messages:
        # Expand image URLs in message content for LlamaStack
        content = message.content
        if isinstance(content, list):
            # Process each content item and expand image URLs
            for item in content:
                if isinstance(item, dict):
                    expand_image_url(item)

        conversation.append({"role": message.role, "content": content})

    return conversation


class ChatService:
    """
    A chat service using LlamaStack's Responses API with virtual agent configurations.

    This approach:
    - Uses virtual agent configs as templates for model/tools/prompt
    - Dynamically passes model and tools from config to each Responses API call
    - Sends full conversation history for proper context
    - No need to pre-create persistent agents

    Args:
        request: FastAPI request object for LlamaStack client access
        db: Database session for accessing virtual agent configurations
        user_id: ID of the authenticated user
    """

    def __init__(self, request: Request, db: AsyncSession, user_id):
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        self.request = request
        self.db = db
        self.user_id = user_id  # Can be UUID or string, SQLAlchemy handles conversion

    async def _prepare_conversation_input(self, session_id, user_input):
        """Prepare input with full conversation history."""
        if not session_id:
            raise Exception("session_id is required")

        # Get existing conversation history (don't store user message yet)
        conversation_history = await get_conversation_history(self.db, session_id)

        # Add current user input to conversation
        if isinstance(user_input, list):
            # Multimodal content - serialize and expand URLs
            content_items = []
            for item in user_input:
                content_item = item.model_dump()
                expand_image_url(content_item)
                content_items.append(content_item)
            conversation_history.append({"role": "user", "content": content_items})
        else:
            # Single content item
            content_item = user_input.model_dump()
            expand_image_url(content_item)
            conversation_history.append({"role": "user", "content": [content_item]})

        return conversation_history

    async def _store_conversation_turn(
        self,
        agent_id: str,
        session_id: str,
        user_input: Any,
        assistant_content_items: List[Any],
        response_id: str,
    ) -> None:
        """
        Store both user input and assistant response in a single transaction.
        Also ensures the chat session exists before storing messages.

        Args:
            agent_id: Virtual agent configuration ID
            session_id: Chat session ID
            user_input: User message content
            assistant_content_items: Assistant response content items from LlamaStack
            response_id: LlamaStack response ID
        """
        # Convert user input to JSON format - expecting Pydantic models
        if isinstance(user_input, list):
            user_json_content = [item.model_dump() for item in user_input]
        else:
            user_json_content = user_input.model_dump()

        # Convert assistant content items to JSON format
        assistant_json_content = [item.model_dump() for item in assistant_content_items]

        # Check if session exists, create if not
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == self.user_id)
        )
        session = result.scalar_one_or_none()

        # Generate title from user message (do this for both new and existing sessions)
        title = "New Chat"
        if isinstance(user_input, list) and user_input:
            # For multimodal content, look for text content
            for item in user_input:
                if hasattr(item, "text") and item.text:
                    txt = item.text
                    title = txt[:50] + "..." if len(txt) > 50 else txt[:50]
                    break
        elif hasattr(user_input, "text"):
            txt = user_input.text
            title = txt[:50] + "..." if len(txt) > 50 else txt[:50]

        if not session:
            # Create new session owned by the current user
            session = ChatSession(
                id=session_id,
                title=title,
                agent_id=agent_id,
                user_id=self.user_id,
                session_state={"last_response_id": response_id},
            )
            self.db.add(session)
        else:
            # Update existing session with latest response_id and title
            session.session_state = {"last_response_id": response_id}
            session.title = title

        # Create user message with explicit timestamp
        now = datetime.now()
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_json_content,
            created_at=now,
        )
        self.db.add(user_message)

        # Create assistant message with smallest possible later timestamp (1 microsecond)
        assistant_message = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=assistant_json_content,
            response_id=response_id,
            created_at=now + timedelta(microseconds=1),
        )
        self.db.add(assistant_message)

        try:
            # Commit the transaction
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error during commit: {e}")
            await self.db.rollback()
            raise

    async def create_response(
        self, agent_id: str, user_input, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new response using the Responses API with virtual agent config.

        Args:
            agent_id: Virtual agent configuration ID
            user_input: User's message/input
            session_id: Chat session ID for message storage

        Returns:
            Response data including response ID and content

        Raises:
            Exception: If virtual agent not found or response creation fails
        """
        # Get virtual agent from database
        agent = await virtual_agents.get_with_template(self.db, id=agent_id)
        if not agent:
            raise Exception(f"Virtual agent {agent_id} not found")

        # Build tools in Responses API format using agent config
        tools = await build_responses_tools(
            agent.tools, agent.vector_store_ids, self.request
        )

        # Prepare input with full conversation history
        openai_input = await self._prepare_conversation_input(session_id, user_input)

        # Prepare response creation parameters using agent config
        response_params = {
            "model": agent.model_name,  # Use model from agent
            "input": openai_input,
        }

        # Add optional parameters from agent
        param_mapping = {
            "temperature": "temperature",
        }

        for agent_attr, api_param in param_mapping.items():
            if hasattr(agent, agent_attr):
                value = getattr(agent, agent_attr)
                if value is not None and (
                    not isinstance(value, list) or len(value) > 0
                ):
                    response_params[api_param] = value

        # Add system prompt if available
        if agent.prompt:
            # Use the instructions parameter for system prompt in LlamaStack
            # Responses API
            response_params["instructions"] = agent.prompt

        # Add tools from agent if any
        if tools:
            response_params["tools"] = tools

        # Note: Input/output shields not yet supported in Responses API
        if agent.input_shields:
            logger.warning("Input shields not yet supported in Responses API")
        if agent.output_shields:
            logger.warning("Output shields not yet supported in Responses API")

        try:
            # Call LlamaStack Responses API
            client = get_client_from_request(self.request)

            # Log the exact call parameters and client info
            logger.info(f"LlamaStack send: {response_params}")
            response = await client.responses.create(**response_params)
            logger.info(f"LlamaStack recv: {response}")

            # Extract content from response.output array
            content = ""
            assistant_content_items = []
            if hasattr(response, "output") and response.output:
                for output_item in response.output:
                    if hasattr(output_item, "content") and output_item.content:
                        # Store the full content array from this output item
                        assistant_content_items.extend(output_item.content)
                        # Build concatenated string for return value
                        for content_item in output_item.content:
                            if hasattr(content_item, "text"):
                                content += content_item.text

            # Store conversation turn in database
            if session_id:
                await self._store_conversation_turn(
                    agent_id,
                    session_id,
                    user_input,
                    assistant_content_items,
                    response.id,
                )

            return {
                "response_id": response.id,
                "model": response.model,
                "usage": getattr(response, "usage", None),
                "content": content,
                "agent_id": agent_id,
            }

        except Exception as e:
            logger.error(f"Error creating response: {str(e)}")
            raise

    async def stream(
        self,
        agent_id: str,
        session_id: str,  # Session ID for updating session state
        prompt,  # Can be str or InterleavedContent
    ):
        """
        Stream a response using the Responses API with virtual agent configuration.

        This method maintains compatibility with the old interface while using
        the new Responses API under the hood.

        Args:
            agent_id: Virtual agent configuration ID
            session_id: Session ID for message storage
            prompt: User's message/input

        Yields:
            JSON strings containing response chunks
        """
        try:
            # Pass InterleavedContent directly to create_response to preserve images
            response_data = await self.create_response(agent_id, prompt, session_id)

            # Session state will be updated by the background task in llama_stack.py

            # Stream the response content
            # TODO: When LlamaStack Responses API supports streaming, update this
            yield json.dumps(
                jsonable_encoder(
                    {
                        "type": "content",
                        "content": response_data["content"],
                        "response_id": response_data["response_id"],
                        "model": response_data["model"],
                        "session_id": session_id,
                    }
                )
            )

            # End stream marker
            yield json.dumps(
                jsonable_encoder(
                    {
                        "type": "done",
                        "response_id": response_data["response_id"],
                        "session_id": session_id,  # Return for compatibility
                    }
                )
            )

        except Exception as e:
            logger.error(f"Error in stream for agent {agent_id}: {e}")
            yield json.dumps(
                jsonable_encoder(
                    {
                        "type": "error",
                        "content": f"Error occurred while processing your request: "
                        f"{str(e)}",
                    }
                )
            )
