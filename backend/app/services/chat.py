"""
Chat service for handling LlamaStack conversations with virtual agent configurations.
"""

import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.llamastack import get_client_from_request
from ..models import ChatSession

logger = logging.getLogger(__name__)


class ContentPart:
    """Represents a single content part (reasoning or output text) within a message"""

    def __init__(self, item_id: str, content_index: int, part_type: str):
        self.item_id = item_id
        self.content_index = content_index
        self.type = part_type  # 'reasoning_text' or 'output_text'
        self.text = ""
        self.complete = False

    def add_delta(self, delta: str):
        """Accumulate text delta"""
        self.text += delta

    def set_final_text(self, text: str):
        """Set the final complete text"""
        self.text = text
        self.complete = True

    def get_key(self):
        """Get unique key for this content part"""
        return f"{self.item_id}:{self.content_index}"


class ToolCall:
    """Represents a single tool call"""

    def __init__(self, item_id: str, name: str = None, server_label: str = None):
        self.item_id = item_id
        self.name = name
        self.server_label = server_label
        self.arguments = None
        self.output = None
        self.error = None
        self.complete = False

    def update_arguments(self, arguments: str):
        """Update tool call arguments"""
        self.arguments = arguments

    def set_result(self, arguments: str = None, output: str = None, error: str = None):
        """Set final result and mark complete"""
        if arguments:
            self.arguments = arguments
        self.output = output
        self.error = error
        self.complete = True

    def to_dict(self):
        """Serialize to dict for sending to frontend"""
        return {
            "id": self.item_id,
            "name": self.name,
            "server_label": self.server_label,
            "arguments": self.arguments,
            "output": self.output,
            "error": self.error,
            "status": "failed" if self.error else "completed",
        }


class StreamAggregator:
    """
    Aggregates raw LlamaStack streaming events into simplified, complete events.

    Works like a DOM builder - accumulates content parts and tool calls,
    then serializes and sends them when complete.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        # Content parts indexed by key (item_id:content_index)
        self.content_parts: Dict[str, ContentPart] = {}
        # Tool calls indexed by item_id
        self.tool_calls: Dict[str, ToolCall] = {}
        # Track what we've already sent to avoid duplicates
        self.sent_content = set()
        self.sent_tool_calls = set()
        # Track if we've seen any output text
        self.has_output_text = False

    async def process_chunk(
        self, chunk: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a raw LlamaStack chunk and yield simplified events.

        Args:
            chunk: Raw LlamaStack streaming chunk

        Yields:
            Simplified events ready for frontend consumption
        """
        chunk_type = chunk.get("type", "")

        # Handle content part creation
        if chunk_type == "response.content_part.added":
            for event in self._handle_content_part_added(chunk):
                yield event

        # Handle reasoning text streaming
        elif chunk_type == "response.reasoning_text.delta":
            for event in self._handle_reasoning_delta(chunk):
                yield event
        elif chunk_type == "response.reasoning_text.done":
            for event in self._handle_reasoning_done(chunk):
                yield event

        # Handle output text streaming
        elif chunk_type == "response.output_text.delta":
            for event in self._handle_output_text_delta(chunk):
                yield event

        # Handle tool calls
        elif chunk_type == "response.output_item.added":
            for event in self._handle_output_item_added(chunk):
                yield event
        elif chunk_type == "response.output_item.done":
            for event in self._handle_output_item_done(chunk):
                yield event
        elif chunk_type == "response.mcp_call.arguments.done":
            for event in self._handle_tool_arguments(chunk):
                yield event
        elif chunk_type == "response.function_call.arguments.done":
            for event in self._handle_tool_arguments(chunk):
                yield event

        # Handle response completion/failure
        elif chunk_type == "response.completed":
            for event in self._handle_response_completed(chunk):
                yield event
        elif chunk_type == "response.failed":
            for event in self._handle_response_failed(chunk):
                yield event

        # Handle errors
        elif chunk_type == "error":
            yield self._create_event(
                "error", {"message": chunk.get("content", "Unknown error")}
            )

    def _handle_content_part_added(self, chunk: Dict[str, Any]):
        """Handle content part creation - send in_progress event for reasoning"""
        item_id = chunk.get("item_id")
        content_index = chunk.get("content_index")
        part = chunk.get("part", {})
        part_type = part.get("type")

        # Only handle reasoning_text - send in_progress event immediately
        if part_type == "reasoning_text":
            key = f"{item_id}:{content_index}"

            # Create content part
            if key not in self.content_parts:
                self.content_parts[key] = ContentPart(
                    item_id, content_index, "reasoning_text"
                )

            # Send in_progress event to create the reasoning block in UI
            yield self._create_event(
                "reasoning",
                {"text": "", "status": "in_progress", "id": key},
            )

        # Don't handle output_text here - that streams via deltas
        return []

    def _handle_reasoning_delta(self, chunk: Dict[str, Any]):
        """Handle reasoning text delta - stream deltas to frontend"""
        item_id = chunk.get("item_id")
        content_index = chunk.get("content_index")
        delta = chunk.get("delta", "")

        key = f"{item_id}:{content_index}"

        # Get or create content part
        if key not in self.content_parts:
            self.content_parts[key] = ContentPart(
                item_id, content_index, "reasoning_text"
            )

        part = self.content_parts[key]
        part.add_delta(delta)

        # Stream the delta to frontend for real-time display
        if delta:
            yield self._create_event(
                "reasoning",
                {"text": part.text, "status": "in_progress", "id": key},
            )

    def _handle_reasoning_done(self, chunk: Dict[str, Any]):
        """Handle reasoning text completion - send complete reasoning block"""
        item_id = chunk.get("item_id")
        content_index = chunk.get("content_index")
        text = chunk.get("text", "")

        key = f"{item_id}:{content_index}"

        # Get or create content part
        if key not in self.content_parts:
            self.content_parts[key] = ContentPart(
                item_id, content_index, "reasoning_text"
            )

        part = self.content_parts[key]
        part.set_final_text(text)

        # Send only if not already sent
        if key not in self.sent_content:
            self.sent_content.add(key)
            yield self._create_event(
                "reasoning",
                {"text": part.text, "status": "completed", "id": key},
            )

    def _handle_output_text_delta(self, chunk: Dict[str, Any]):
        """Handle output text delta - stream deltas to frontend for client-side accumulation"""
        item_id = chunk.get("item_id")
        content_index = chunk.get("content_index")
        delta = chunk.get("delta", "")

        key = f"{item_id}:{content_index}"

        # Track that we've seen output text (for completion validation)
        if key not in self.content_parts:
            self.content_parts[key] = ContentPart(item_id, content_index, "output_text")

        self.has_output_text = True

        # Stream just the delta to frontend (frontend will accumulate)
        yield self._create_event(
            "response",
            {"delta": delta, "status": "in_progress", "id": key},
        )

    def _handle_output_item_added(self, chunk: Dict[str, Any]):
        """Handle output item added - only process tool executions"""
        item = chunk.get("item", {})
        item_type = item.get("type")
        item_id = item.get("id")

        # Only process tool execution types
        tool_execution_types = [
            "mcp_call",
            "function_call",
            "web_search_call",
            "file_search_call",
        ]
        if item_type not in tool_execution_types:
            return

        # Tool call field mappings: (name_field, server_label_field, args_field)
        tool_map = {
            "mcp_call": ("name", "server_label", "arguments"),
            "function_call": ("name", "server_label", "arguments"),
            "file_search_call": ("knowledge_search", "llamastack", "queries"),
            "web_search_call": ("web_search", "llamastack", "query"),
        }

        name_field, server_field, args_field = tool_map[item_type]

        # For mcp_call/function_call, name/server_label are fields; for others, they're literal values
        is_standard = item_type in ("mcp_call", "function_call")
        name = item.get(name_field) if is_standard else name_field
        server_label = item.get(server_field) if is_standard else server_field

        tool_call = ToolCall(item_id=item_id, name=name, server_label=server_label)

        args_val = item.get(args_field)
        if args_val:
            tool_call.update_arguments(str(args_val) if not is_standard else args_val)

        self.tool_calls[item_id] = tool_call

        # Yield in_progress tool call
        yield self._create_event(
            "tool_call",
            {
                **tool_call.to_dict(),
                "status": "in_progress",
            },
        )

    def _handle_tool_arguments(self, chunk: Dict[str, Any]):
        """Handle tool call arguments completion"""
        item_id = chunk.get("item_id")
        arguments = chunk.get("arguments")

        if item_id in self.tool_calls:
            self.tool_calls[item_id].update_arguments(arguments)

            # Yield updated in_progress event
            yield self._create_event(
                "tool_call",
                {
                    **self.tool_calls[item_id].to_dict(),
                    "status": "in_progress",
                },
            )

    def _handle_output_item_done(self, chunk: Dict[str, Any]):
        """Handle output item completion - finalize tool calls"""
        item = chunk.get("item", {})
        item_type = item.get("type")
        item_id = item.get("id")

        # Only process tool execution types
        tool_execution_types = [
            "mcp_call",
            "function_call",
            "web_search_call",
            "file_search_call",
        ]
        if item_type not in tool_execution_types:
            return

        # Tool call field mappings: (name_field, server_label_field, args_field, output_field)
        # Note: web_search_call uses None for output_field because results aren't exposed in API
        tool_map = {
            "mcp_call": ("name", "server_label", "arguments", "output"),
            "function_call": ("name", "server_label", "arguments", "output"),
            "file_search_call": (
                "knowledge_search",
                "llamastack",
                "queries",
                "results",
            ),
            "web_search_call": ("web_search", "llamastack", "query", None),
        }

        name_field, server_field, args_field, output_field = tool_map[item_type]

        # Get or create tool call
        if item_id not in self.tool_calls:
            is_standard = item_type in ("mcp_call", "function_call")
            name = item.get(name_field) if is_standard else name_field
            server_label = item.get(server_field) if is_standard else server_field
            tool_call = ToolCall(item_id=item_id, name=name, server_label=server_label)
            self.tool_calls[item_id] = tool_call
        else:
            tool_call = self.tool_calls[item_id]

        # Set final result
        is_standard = item_type in ("mcp_call", "function_call")
        args_val = item.get(args_field)

        # Get output value (None if output_field is None)
        output_val = item.get(output_field) if output_field else None

        # Format output based on tool type
        if output_field is None:
            # For tools like web_search that don't expose results
            status = item.get("status", "completed")
            output = f"Tool execution {status}"
        elif output_val is not None:
            # For tools that return results
            if item_type == "file_search_call" and isinstance(output_val, list):
                output = str(output_val) if output_val else "No results found"
            else:
                output = str(output_val)
        else:
            output = "No results found" if not is_standard else None

        tool_call.set_result(
            arguments=str(args_val) if args_val and not is_standard else args_val,
            output=output,
            error=item.get("error"),
        )

        # Send only if not already sent
        if item_id not in self.sent_tool_calls:
            self.sent_tool_calls.add(item_id)
            yield self._create_event("tool_call", tool_call.to_dict())

    def _handle_response_completed(self, chunk: Dict[str, Any]):
        """Handle response completion"""
        response = chunk.get("response", {})
        output = response.get("output", [])

        # Check for guardrail refusal
        for output_item in output:
            if output_item.get("type") == "message":
                content = output_item.get("content", [])
                for content_item in content:
                    if content_item.get("type") == "refusal":
                        refusal_msg = content_item.get(
                            "refusal", "Request blocked by safety guardrail"
                        )
                        yield self._create_event("error", {"message": refusal_msg})
                        return

        # If we have no output text, send error
        if not self.has_output_text:
            error_msg = (
                "The assistant couldn't generate a text response. "
                "Please try again or rephrase your request."
            )
            yield self._create_event("error", {"message": error_msg})
        else:
            # Send final completed status for all output text parts
            for key, part in self.content_parts.items():
                if part.type == "output_text" and key not in self.sent_content:
                    self.sent_content.add(key)
                    yield self._create_event(
                        "response",
                        {"delta": "", "status": "completed", "id": key},
                    )

    def _handle_response_failed(self, chunk: Dict[str, Any]):
        """Handle response failure"""
        response = chunk.get("response", {})
        error = response.get("error", {})
        error_message = error.get("message", "Unknown error")

        yield self._create_event(
            "error", {"message": f"Response failed: {error_message}"}
        )

    def _create_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a simplified event with session_id"""
        return {"type": event_type, "session_id": self.session_id, **data}


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
        self.request = request
        self.db = db
        self.user_id = user_id  # Can be UUID or string, SQLAlchemy handles conversion

    async def _get_or_create_conversation(self, session_id: str, client) -> str:
        """
        Get or create a LlamaStack conversation for the session.

        Args:
            session_id: Chat session ID
            client: LlamaStack client

        Returns:
            LlamaStack conversation ID
        """
        # Get session from database
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise Exception(f"Session {session_id} not found")

        # Return existing conversation_id if available
        if session.conversation_id:
            logger.info(f"Using existing conversation: {session.conversation_id}")
            return session.conversation_id

        # Create new conversation in LlamaStack
        conversation = await client.conversations.create()
        conversation_id = conversation.id

        # Store conversation_id in our session
        session.conversation_id = conversation_id
        await self.db.commit()
        logger.info(f"Created new conversation: {conversation_id}")

        return conversation_id

    async def _run_input_shields(
        self, client, shield_ids: List[str], user_input: List[Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Run input shields manually before processing the user message.

        Args:
            client: LlamaStack client
            shield_ids: List of shield IDs to run
            user_input: User's input content items

        Returns:
            Violation dict if content is blocked, None otherwise
        """
        if not shield_ids:
            return None

        logger.info(f"Running input shields manually: {shield_ids}")

        # Extract text content for shield checking
        # If multimodal, concatenate all text parts
        text_content = ""
        for item in user_input:
            if hasattr(item, "type") and item.type == "input_text":
                text_content += getattr(item, "text", "")

        if not text_content:
            logger.debug("No text content to check with shields")
            return None

        try:
            # Run all shields and check for violations
            for shield_id in shield_ids:
                logger.debug(
                    f"Running shield: {shield_id} with text: {text_content[:100]}..."
                )
                shield_response = await client.safety.run_shield(
                    shield_id=shield_id,
                    messages=[{"role": "user", "content": text_content}],
                    params={},
                )
                logger.debug(f"Shield {shield_id} response: {shield_response}")

                # Check if content was blocked
                if hasattr(shield_response, "violation") and shield_response.violation:
                    violation_msg = (
                        shield_response.violation.user_message
                        if hasattr(shield_response.violation, "user_message")
                        else "Content policy violation"
                    )
                    logger.warning(
                        f"Content blocked by shield {shield_id}: {violation_msg}"
                    )
                    return {
                        "type": "error",
                        "message": violation_msg,
                    }

            return None

        except Exception as shield_error:
            logger.error(f"Error running shield: {shield_error}")
            # Continue without shield if it fails
            return None

    async def _prepare_conversation_input(self, user_input):
        """
        Prepare input with just the current user message.

        When using the conversation parameter, LlamaStack manages the conversation
        history automatically - we only need to send the new user message.

        Args:
            user_input: User input content
        """
        logger.debug("Preparing conversation input")

        # Prepare current user input only (user_input is always a list)
        content_items = []
        for item in user_input:
            content_item = item.model_dump()
            expand_image_url(content_item)
            content_items.append(content_item)

        # Use structured format for all content
        logger.debug(f"Using structured format ({len(content_items)} items)")
        return [{"role": "user", "content": content_items}]

    async def _update_session_title(
        self,
        session_id: str,
        user_input: Any,
    ) -> None:
        """
        Update session title based on first user message.

        Args:
            session_id: Chat session ID
            user_input: User message content
        """
        # Get session
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == self.user_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            # Session should already exist (created via create_chat_session endpoint)
            logger.warning(f"Session {session_id} not found, cannot update title")
            return

        # Only update title if it's still the default
        if session.title and not session.title.startswith("Chat"):
            # Title already customized, don't override
            return

        # Generate title from user message
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

        session.title = title

        try:
            await self.db.commit()
        except Exception as e:
            logger.error(f"Error updating session title: {e}")
            await self.db.rollback()

    async def stream(
        self,
        agent,  # VirtualAgent object (already fetched with template)
        session_id: str,
        prompt,  # Can be str or InterleavedContent
    ):
        """
        Stream a response using the Responses API with Conversations.

        This method streams responses from LlamaStack using the Conversations API,
        which manages message history automatically.

        Args:
            agent: Virtual agent object (already fetched with template)
            session_id: Session ID
            prompt: User's message/input

        Yields:
            SSE-formatted JSON strings containing response chunks
        """
        try:
            # Build tools in Responses API format
            tools = await build_responses_tools(
                agent.tools, agent.vector_store_ids, self.request
            )

            # Prepare input with just the current message
            openai_input = await self._prepare_conversation_input(prompt)

            # Prepare streaming request parameters
            response_params = {
                "model": agent.model_name,
                "input": openai_input,
                "stream": True,  # Enable streaming!
                "store": True,  # Persist messages in the conversation
            }

            # Add optional parameters
            if agent.temperature is not None:
                response_params["temperature"] = agent.temperature
            if agent.max_infer_iters is not None:
                response_params["max_infer_iters"] = agent.max_infer_iters
            if agent.prompt:
                response_params["instructions"] = agent.prompt
            if tools:
                response_params["tools"] = tools

            # Stream from LlamaStack with aggregation layer
            aggregator = StreamAggregator(str(session_id))

            async with get_client_from_request(self.request) as client:
                # Run input shields manually before creating the response
                if agent.input_shields and len(agent.input_shields) > 0:
                    violation = await self._run_input_shields(
                        client, agent.input_shields, prompt
                    )
                    if violation:
                        violation["session_id"] = str(session_id)
                        yield f"data: {json.dumps(jsonable_encoder(violation))}\n\n"
                        yield "data: [DONE]\n\n"
                        return
                # Get or create conversation for this session
                conversation_id = await self._get_or_create_conversation(
                    session_id, client
                )
                response_params["conversation"] = conversation_id

                # Log the request we're sending to LlamaStack
                logger.info(
                    f"Starting stream for session {session_id}, model={agent.model_name}, "
                    f"conversation={conversation_id}"
                )
                logger.debug(
                    f"Request params: {json.dumps(jsonable_encoder(response_params), indent=2)}"
                )

                async for chunk in await client.responses.create(**response_params):
                    # Convert chunk to dict
                    chunk_dict = jsonable_encoder(chunk)
                    logger.debug(f"Raw chunk: {chunk_dict}")

                    # Process through aggregator - yields simplified events
                    async for simplified_event in aggregator.process_chunk(chunk_dict):
                        logger.debug(f"Event: {simplified_event}")
                        yield f"data: {json.dumps(simplified_event)}\n\n"

            logger.info(f"Stream loop completed for session {session_id}")

            # Send [DONE] to signal stream completion
            yield "data: [DONE]\n\n"

            # Update session title based on first message
            await self._update_session_title(session_id, prompt)

        except Exception as e:
            logger.exception(f"Error in stream for agent {agent.id}: {e}")
            error_data = {
                "type": "error",
                "message": f"Error: {str(e)}",
                "session_id": str(session_id),
            }
            yield f"data: {json.dumps(jsonable_encoder(error_data))}\n\n"
