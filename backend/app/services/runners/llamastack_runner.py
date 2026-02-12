"""
LlamaStack runner implementation.

Handles streaming responses from LlamaStack using the Responses API
with Conversations for message history management.
"""

import json
import logging
import os
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from ...api.llamastack import get_client_from_request
from ...models import ChatSession
from .base import BaseRunner

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper classes (moved from chat.py)
# ---------------------------------------------------------------------------


class ContentPart:
    """Represents a single content part (reasoning or output text) within a message."""

    def __init__(self, item_id: str, content_index: int, part_type: str):
        self.item_id = item_id
        self.content_index = content_index
        self.type = part_type  # 'reasoning_text' or 'output_text'
        self.text = ""
        self.complete = False

    def add_delta(self, delta: str):
        self.text += delta

    def set_final_text(self, text: str):
        self.text = text
        self.complete = True

    def get_key(self):
        return f"{self.item_id}:{self.content_index}"


class ToolCall:
    """Represents a single tool call."""

    def __init__(self, item_id: str, name: str = None, server_label: str = None):
        self.item_id = item_id
        self.name = name
        self.server_label = server_label
        self.arguments = None
        self.output = None
        self.error = None
        self.complete = False

    def update_arguments(self, arguments: str):
        self.arguments = arguments

    def set_result(self, arguments: str = None, output: str = None, error: str = None):
        if arguments:
            self.arguments = arguments
        self.output = output
        self.error = error
        self.complete = True

    def to_dict(self):
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
        self.content_parts: Dict[str, ContentPart] = {}
        self.tool_calls: Dict[str, ToolCall] = {}
        self.sent_content = set()
        self.sent_tool_calls = set()
        self.has_output_text = False

    async def process_chunk(self, chunk: Dict[str, Any]):
        chunk_type = chunk.get("type", "")

        if chunk_type == "response.content_part.added":
            for event in self._handle_content_part_added(chunk):
                yield event
        elif chunk_type == "response.reasoning_text.delta":
            for event in self._handle_reasoning_delta(chunk):
                yield event
        elif chunk_type == "response.reasoning_text.done":
            for event in self._handle_reasoning_done(chunk):
                yield event
        elif chunk_type == "response.output_text.delta":
            for event in self._handle_output_text_delta(chunk):
                yield event
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
        elif chunk_type == "response.completed":
            for event in self._handle_response_completed(chunk):
                yield event
        elif chunk_type == "response.failed":
            for event in self._handle_response_failed(chunk):
                yield event
        elif chunk_type == "error":
            yield self._create_event(
                "error", {"message": chunk.get("content", "Unknown error")}
            )

    def _handle_content_part_added(self, chunk):
        item_id = chunk.get("item_id")
        content_index = chunk.get("content_index")
        part = chunk.get("part", {})
        part_type = part.get("type")

        if part_type == "reasoning_text":
            key = f"{item_id}:{content_index}"
            if key not in self.content_parts:
                self.content_parts[key] = ContentPart(
                    item_id, content_index, "reasoning_text"
                )
            yield self._create_event(
                "reasoning",
                {"text": "", "status": "in_progress", "id": key},
            )
        return []

    def _handle_reasoning_delta(self, chunk):
        item_id = chunk.get("item_id")
        content_index = chunk.get("content_index")
        delta = chunk.get("delta", "")
        key = f"{item_id}:{content_index}"

        if key not in self.content_parts:
            self.content_parts[key] = ContentPart(
                item_id, content_index, "reasoning_text"
            )

        part = self.content_parts[key]
        part.add_delta(delta)

        if delta:
            yield self._create_event(
                "reasoning",
                {"text": part.text, "status": "in_progress", "id": key},
            )

    def _handle_reasoning_done(self, chunk):
        item_id = chunk.get("item_id")
        content_index = chunk.get("content_index")
        text = chunk.get("text", "")
        key = f"{item_id}:{content_index}"

        if key not in self.content_parts:
            self.content_parts[key] = ContentPart(
                item_id, content_index, "reasoning_text"
            )

        part = self.content_parts[key]
        part.set_final_text(text)

        if key not in self.sent_content:
            self.sent_content.add(key)
            yield self._create_event(
                "reasoning",
                {"text": part.text, "status": "completed", "id": key},
            )

    def _handle_output_text_delta(self, chunk):
        item_id = chunk.get("item_id")
        content_index = chunk.get("content_index")
        delta = chunk.get("delta", "")
        key = f"{item_id}:{content_index}"

        if key not in self.content_parts:
            self.content_parts[key] = ContentPart(item_id, content_index, "output_text")

        self.has_output_text = True

        yield self._create_event(
            "response",
            {"delta": delta, "status": "in_progress", "id": key},
        )

    def _handle_output_item_added(self, chunk):
        item = chunk.get("item", {})
        item_type = item.get("type")
        item_id = item.get("id")

        tool_execution_types = [
            "mcp_call",
            "function_call",
            "web_search_call",
            "file_search_call",
        ]
        if item_type not in tool_execution_types:
            return

        tool_map = {
            "mcp_call": ("name", "server_label", "arguments"),
            "function_call": ("name", "server_label", "arguments"),
            "file_search_call": ("knowledge_search", "llamastack", "queries"),
            "web_search_call": ("web_search", "llamastack", "query"),
        }

        name_field, server_field, args_field = tool_map[item_type]
        is_standard = item_type in ("mcp_call", "function_call")
        name = item.get(name_field) if is_standard else name_field
        server_label = item.get(server_field) if is_standard else server_field

        tool_call = ToolCall(item_id=item_id, name=name, server_label=server_label)
        args_val = item.get(args_field)
        if args_val:
            tool_call.update_arguments(str(args_val) if not is_standard else args_val)

        self.tool_calls[item_id] = tool_call

        yield self._create_event(
            "tool_call",
            {**tool_call.to_dict(), "status": "in_progress"},
        )

    def _handle_tool_arguments(self, chunk):
        item_id = chunk.get("item_id")
        arguments = chunk.get("arguments")

        if item_id in self.tool_calls:
            self.tool_calls[item_id].update_arguments(arguments)
            yield self._create_event(
                "tool_call",
                {**self.tool_calls[item_id].to_dict(), "status": "in_progress"},
            )

    def _handle_output_item_done(self, chunk):
        item = chunk.get("item", {})
        item_type = item.get("type")
        item_id = item.get("id")

        tool_execution_types = [
            "mcp_call",
            "function_call",
            "web_search_call",
            "file_search_call",
        ]
        if item_type not in tool_execution_types:
            return

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

        if item_id not in self.tool_calls:
            is_standard = item_type in ("mcp_call", "function_call")
            name = item.get(name_field) if is_standard else name_field
            server_label = item.get(server_field) if is_standard else server_field
            tool_call = ToolCall(item_id=item_id, name=name, server_label=server_label)
            self.tool_calls[item_id] = tool_call
        else:
            tool_call = self.tool_calls[item_id]

        is_standard = item_type in ("mcp_call", "function_call")
        args_val = item.get(args_field)
        output_val = item.get(output_field) if output_field else None

        if output_field is None:
            status = item.get("status", "completed")
            output = f"Tool execution {status}"
        elif output_val is not None:
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

        if item_id not in self.sent_tool_calls:
            self.sent_tool_calls.add(item_id)
            yield self._create_event("tool_call", tool_call.to_dict())

    def _handle_response_completed(self, chunk):
        response = chunk.get("response", {})
        output = response.get("output", [])

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

        if not self.has_output_text:
            error_msg = (
                "The assistant couldn't generate a text response. "
                "Please try again or rephrase your request."
            )
            yield self._create_event("error", {"message": error_msg})
        else:
            for key, part in self.content_parts.items():
                if part.type == "output_text" and key not in self.sent_content:
                    self.sent_content.add(key)
                    yield self._create_event(
                        "response",
                        {"delta": "", "status": "completed", "id": key},
                    )

    def _handle_response_failed(self, chunk):
        response = chunk.get("response", {})
        error = response.get("error", {})
        error_message = error.get("message", "Unknown error")
        yield self._create_event(
            "error", {"message": f"Response failed: {error_message}"}
        )

    def _create_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return {"type": event_type, "session_id": self.session_id, **data}


# ---------------------------------------------------------------------------
# Shared helpers (moved from chat.py)
# ---------------------------------------------------------------------------


def expand_image_url(content_item: Dict[str, Any]) -> None:
    """Expand relative image URL to full URL for LlamaStack inference service."""
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

    Args:
        tools: List of virtual agent tools to convert
        vector_store_ids: List of LlamaStack vector store IDs for file_search tools
        request: FastAPI request for accessing LlamaStack

    Returns:
        List of tools in OpenAI Responses API format
    """
    responses_tools = []

    if not tools:
        return responses_tools

    for tool_info in tools:
        tool_id = tool_info["toolgroup_id"]

        if tool_id == "builtin::rag":
            if vector_store_ids:
                responses_tools.append(
                    {"type": "file_search", "vector_store_ids": vector_store_ids}
                )
        elif "web_search" in tool_id or "search" in tool_id:
            responses_tools.append({"type": "web_search"})
        elif tool_id.startswith("mcp::"):
            if request:
                try:
                    client = get_client_from_request(request)
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
            else:
                logger.warning(
                    f"Cannot get MCP server info for {tool_id} without request object"
                )
        else:
            responses_tools.append({"type": tool_id})

    return responses_tools


# ---------------------------------------------------------------------------
# LlamaStack Runner
# ---------------------------------------------------------------------------


class LlamaStackRunner(BaseRunner):
    """
    Runner for LlamaStack agents using the Responses API with Conversations.

    This is the default runner and implements the same logic that was
    previously in ChatService.stream().
    """

    async def _get_or_create_conversation(self, session_id: str, client) -> str:
        """Get or create a LlamaStack conversation for the session."""
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise Exception(f"Session {session_id} not found")

        if session.conversation_id:
            logger.info(f"Using existing conversation: {session.conversation_id}")
            return session.conversation_id

        conversation = await client.conversations.create()
        conversation_id = conversation.id

        session.conversation_id = conversation_id
        await self.db.commit()
        logger.info(f"Created new conversation: {conversation_id}")

        return conversation_id

    async def _run_input_shields(
        self, client, shield_ids: List[str], user_input: List[Any]
    ) -> Optional[Dict[str, Any]]:
        """Run input shields manually before processing the user message."""
        if not shield_ids:
            return None

        logger.info(f"Running input shields manually: {shield_ids}")

        text_content = ""
        for item in user_input:
            if hasattr(item, "type") and item.type == "input_text":
                text_content += getattr(item, "text", "")

        if not text_content:
            logger.debug("No text content to check with shields")
            return None

        try:
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
            return None

    async def _prepare_conversation_input(self, user_input):
        """Prepare input with just the current user message."""
        logger.debug("Preparing conversation input")

        content_items = []
        for item in user_input:
            content_item = item.model_dump()
            expand_image_url(content_item)
            content_items.append(content_item)

        logger.debug(f"Using structured format ({len(content_items)} items)")
        return [{"role": "user", "content": content_items}]

    async def stream(
        self,
        agent,
        session_id: str,
        prompt,
    ) -> AsyncIterator[str]:
        """Stream a response using the LlamaStack Responses API with Conversations."""
        try:
            tools = await build_responses_tools(
                agent.tools, agent.vector_store_ids, self.request
            )

            openai_input = await self._prepare_conversation_input(prompt)

            response_params = {
                "model": agent.model_name,
                "input": openai_input,
                "stream": True,
            }

            if agent.temperature is not None:
                response_params["temperature"] = agent.temperature
            if agent.max_infer_iters is not None:
                response_params["max_infer_iters"] = agent.max_infer_iters
            if agent.prompt:
                response_params["instructions"] = agent.prompt

            if tools:
                response_params["tools"] = tools

            aggregator = StreamAggregator(str(session_id))

            async with get_client_from_request(self.request) as client:
                # Run input shields
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

                logger.info(
                    f"Starting stream for session {session_id}, "
                    f"model={response_params['model']}, "
                    f"conversation={conversation_id}"
                )
                logger.debug(
                    f"Request params: "
                    f"{json.dumps(jsonable_encoder(response_params), indent=2)}"
                )

                async for chunk in await client.responses.create(**response_params):
                    chunk_dict = jsonable_encoder(chunk)
                    logger.debug(f"Raw chunk: {chunk_dict}")

                    async for simplified_event in aggregator.process_chunk(chunk_dict):
                        logger.debug(f"Event: {simplified_event}")
                        yield f"data: {json.dumps(simplified_event)}\n\n"

            logger.info(f"Stream loop completed for session {session_id}")

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

    async def _update_session_title(self, session_id: str, user_input: Any) -> None:
        """Update session title based on first user message."""
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.id == session_id)
            .where(ChatSession.user_id == self.user_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            logger.warning(f"Session {session_id} not found, cannot update title")
            return

        if session.title and not session.title.startswith("Chat"):
            return

        title = "New Chat"
        if isinstance(user_input, list) and user_input:
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
