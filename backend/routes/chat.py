import asyncio
import enum
import json
import os
import re
from typing import List

from fastapi import Request
from llama_stack_client.lib.agents.react.tool_parser import ReActOutput
from llama_stack_client.types.shared.interleaved_content import (
    InterleavedContent,
)
from llama_stack_client.types.shared.user_message import UserMessage
from llama_stack_client.types.shared_params.agent_config import (
    AgentConfig,
    Toolgroup,
)

from ..agents import ExistingAsyncAgent, ExistingReActAgent
from ..api.llamastack import get_client_from_request
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class AgentType(enum.Enum):
    REGULAR = "Regular"
    REACT = "ReAct"


class Chat:
    """
    A stateless class for handling chat interactions with LlamaStack.

    This class no longer maintains local state and instead retrieves
    everything from LlamaStack APIs using agent_id and session_id.

    Args:
        logger: Logger object for logging messages.

    Methods:
        stream: Streams the chatbot's response based on agent_id,
                session_id, and prompt.
    """

    def __init__(self, logger, request: Request):
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        self.log = logger
        self.request = request

    def _get_client(self):
        return get_client_from_request(self.request)

    async def _get_agent_config(self, agent_id: str) -> AgentConfig | None:
        """
        Retrieve agent configuration from LlamaStack.

        Args:
            agent_id: The unique identifier of the agent

        Returns:
            Agent configuration object or None if not found
        """
        try:
            agent = await self._get_client().agents.retrieve(agent_id=agent_id)
            return agent.agent_config
        except Exception as e:
            self.log.error(f"Error retrieving agent config for {agent_id}: {e}")
            return None

    async def _get_toolgroups_for_agent(self, agent_id: str) -> List[Toolgroup]:
        """
        Retrieve tools configuration for an agent from LlamaStack.

        Args:
            agent_id: The unique identifier of the agent

        Returns:
            List of tools available to the agent
        """
        try:
            agent_config = await self._get_agent_config(agent_id)
            if agent_config and agent_config["toolgroups"]:
                return agent_config["toolgroups"]
            return []
        except Exception as e:
            self.log.error(f"Error retrieving tools for agent {agent_id}: {e}")
            return []

    async def _get_model_for_agent(self, agent_id: str) -> str:
        """
        Retrieve model configuration for an agent from LlamaStack.

        Args:
            agent_id: The unique identifier of the agent

        Returns:
            Model identifier string, defaults to llama-3.1-8b-instruct if
            not found
        """
        try:
            agent_config = await self._get_agent_config(agent_id)
            if agent_config and hasattr(agent_config, "model"):
                return agent_config.model
            # Fallback to default model if not found
            models = await self._get_client().models.list()
            model_list = [
                model.identifier for model in models if model.api_model_type == "llm"
            ]
            return model_list[0] if model_list else "llama-3.1-8b-instruct"
        except Exception as e:
            self.log.error(f"Error retrieving model for agent {agent_id}: {e}")
            return "llama-3.1-8b-instruct"

    async def _create_agent_with_existing_id(self, agent_id: str):
        """Create an agent instance using an existing agent_id from
        LlamaStack."""
        try:
            agent_config = await self._get_agent_config(agent_id)
            if not agent_config:
                raise Exception(f"Agent {agent_id} not found")

            model = await self._get_model_for_agent(agent_id)
            toolgroups = await self._get_toolgroups_for_agent(agent_id)

            # Determine agent type from database - for now, check if it's a
            # ReAct agent by looking for response_format.
            # This is a simpler approach that doesn't require database access
            agent_type = (
                AgentType.REACT
                if agent_config.get("response_format")
                else AgentType.REGULAR
            )

            # Create agent instance using existing ID
            if agent_type == AgentType.REACT:
                # Get the actual sampling parameters from the agent config
                agent_sampling_params = agent_config.get(
                    "sampling_params",
                    {
                        "strategy": {"type": "greedy"},
                        "max_tokens": 512,
                    },
                )

                return ExistingReActAgent(
                    self._get_client(),
                    agent_id=agent_id,
                    model=model,
                    tools=toolgroups,
                    response_format={
                        "type": "json_schema",
                        "json_schema": ReActOutput.model_json_schema(),
                    },
                    sampling_params=agent_sampling_params,
                )
            else:
                # Get the actual sampling parameters from the agent config
                agent_sampling_params = agent_config.get(
                    "sampling_params",
                    {
                        "strategy": {"type": "greedy"},
                        "max_tokens": 512,
                    },
                )

                return ExistingAsyncAgent(
                    self._get_client(),
                    agent_id=agent_id,
                    model=model,
                    tools=toolgroups,
                    sampling_params=agent_sampling_params,
                )
        except Exception as e:
            self.log.error(f"Error creating agent with ID {agent_id}: {e}")
            raise

    def _response_generator(
        self, turn_response, session_id: str, agent_type: AgentType
    ):
        if agent_type == AgentType.REACT:
            return self._handle_react_response(turn_response, session_id)
        else:
            return self._handle_regular_response(turn_response, session_id)

    def _handle_react_response(self, turn_response, session_id: str):
        """
        Simplified ReAct response handler with proper error handling.

        This method processes ReAct agent responses with:
        - Robust error handling for missing payloads
        - Simplified processing logic
        - Graceful fallbacks for malformed responses
        - Clear error messages for debugging
        """
        # Send session ID first to help client initialize the connection
        yield json.dumps({"type": "session", "sessionId": session_id})

        current_step_content = ""
        final_answer = None
        tool_results = []

        try:
            for response in turn_response:
                # Check if this is an error response from LlamaStack
                if hasattr(response, "error") and response.error:
                    error_message = response.error.get("message", str(response.error))
                    logger.error(f"LlamaStack error response: {error_message}")

                    # Handle specific websearch tool error
                    # Check for this error message: ValueError: Tool group 'builtin::websearch' not found
                    if "Tool group 'builtin::websearch' not found" in error_message:
                        error_message = (
                            "This assistant is not available right now. It needs internet search tools "
                            "(such as Tavily) that aren't set up yet. Please try a different assistant "
                            "or contact your administrator."
                        )

                    yield json.dumps(
                        {
                            "type": "error",
                            "content": error_message,
                        }
                    )
                    return

                # Robust payload validation
                if not hasattr(response, "event") or not hasattr(
                    response.event, "payload"
                ):
                    logger.error(f"Invalid response structure: {response}")
                    yield json.dumps(
                        {
                            "type": "error",
                            "content": (
                                "Received malformed response from server. "
                                "Please try again."
                            ),
                        }
                    )
                    return

                payload = response.event.payload

                # Handle step progress (accumulate text)
                if payload.event_type == "step_progress" and hasattr(
                    payload.delta, "text"
                ):
                    current_step_content += payload.delta.text
                    continue

                # Handle step completion
                if payload.event_type == "step_complete":
                    step_details = payload.step_details

                    if step_details.step_type == "inference":
                        # Process inference step with simplified logic
                        for chunk in self._process_inference_step_simple(
                            current_step_content, tool_results, final_answer
                        ):
                            yield chunk
                        current_step_content = ""

                    elif step_details.step_type == "tool_execution":
                        # Process tool execution
                        tool_results = self._process_tool_execution_simple(
                            step_details, tool_results
                        )
                        current_step_content = ""
                    else:
                        current_step_content = ""

            # Handle final tool results if no final answer
            if not final_answer and tool_results:
                for chunk in self._format_tool_results_simple(tool_results):
                    yield chunk

        except Exception as e:
            logger.error(f"Error in ReAct response processing: {e}")
            yield json.dumps(
                {
                    "type": "error",
                    "content": (
                        f"An error occurred while processing the response: {str(e)}"
                    ),
                }
            )

    def _process_inference_step(self, current_step_content, tool_results, final_answer):
        """Original method for backward compatibility"""
        try:
            react_output_data = json.loads(current_step_content)
            answer = react_output_data.get("answer")

            if answer and answer != "null" and answer is not None:
                final_answer = answer

            if answer and answer != "null" and answer is not None:
                yield f"\n\n✅ **Final Answer:**\n{answer}"

        except json.JSONDecodeError:
            yield (
                f"\n\nFailed to parse ReAct step content:\n"
                f"```json\n{current_step_content}\n```"
            )
        except Exception as e:
            yield (
                f"\n\nFailed to process ReAct step: {e}\n"
                f"```json\n{current_step_content}\n```"
            )

        return final_answer

    def _process_inference_step_json(
        self, current_step_content, tool_results, final_answer
    ):
        """Simplified JSON-emitting version for unified ReAct format"""
        try:
            # Try to parse as JSON first
            react_output_data = json.loads(current_step_content.strip())
            thought = react_output_data.get("thought")
            action = react_output_data.get("action")
            answer = react_output_data.get("answer")

            if answer and answer != "null" and answer is not None:
                final_answer = answer

            # Emit unified ReAct response
            unified_response = {
                "type": "react_unified",
                "thought": thought if thought else None,
                "action": action if isinstance(action, dict) else None,
                "answer": answer if answer and answer != "null" else None,
                "tool_results": tool_results if tool_results else [],
            }
            yield json.dumps(unified_response)

        except json.JSONDecodeError:
            # If JSON parsing fails, treat as plain text
            cleaned_text = current_step_content.strip()
            if cleaned_text:
                unified_response = {
                    "type": "react_unified",
                    "thought": (
                        "I'm processing your request and providing a helpful "
                        "response."
                    ),
                    "action": None,
                    "answer": cleaned_text,
                    "tool_results": tool_results if tool_results else [],
                }
                yield json.dumps(unified_response)
            else:
                # Empty response fallback
                unified_response = {
                    "type": "react_unified",
                    "thought": "Processing your request.",
                    "action": None,
                    "answer": (
                        "I understand your question. Let me provide "
                        "helpful response."
                    ),
                    "tool_results": tool_results if tool_results else [],
                }
                yield json.dumps(unified_response)
        except Exception as e:
            # Final fallback for any other errors
            logger.error(f"Error processing ReAct step: {e}")
            yield json.dumps(
                {
                    "type": "react_unified",
                    "thought": "Processing your request.",
                    "action": None,
                    "answer": (
                        "I understand your question. Let me provide "
                        "helpful response."
                    ),
                    "tool_results": tool_results if tool_results else [],
                }
            )

        return final_answer

    def _format_tool_results_summary(self, tool_results):
        yield "\n\n**Here's what I found:**\n"
        for tool_name, content in tool_results:
            try:
                parsed_content = json.loads(content)

                if tool_name == "web_search" and "top_k" in parsed_content:
                    yield from self._format_web_search_results(parsed_content)
                elif "results" in parsed_content and isinstance(
                    parsed_content["results"], list
                ):
                    yield from self._format_results_list(parsed_content["results"])
                elif isinstance(parsed_content, dict) and len(parsed_content) > 0:
                    yield from self._format_dict_results(parsed_content)
                elif isinstance(parsed_content, list) and len(parsed_content) > 0:
                    yield from self._format_list_results(parsed_content)
            except json.JSONDecodeError:
                yield (
                    f"\n**{tool_name}** returned complex data. "
                    "Check the observation for details.\n"
                )
            except (TypeError, AttributeError, KeyError, IndexError) as e:
                logger.error(
                    f"Error processing {tool_name} result: {type(e).__name__}: {e}"
                )

    def _process_tool_execution(self, step_details, tool_results):
        try:
            if hasattr(step_details, "tool_responses") and step_details.tool_responses:
                for tool_response in step_details.tool_responses:
                    tool_name = tool_response.tool_name
                    content = tool_response.content
                    tool_results.append((tool_name, content))

                    logger.debug("")
                    try:
                        parsed_content = json.loads(content)
                        logger.debug(parsed_content)
                    except json.JSONDecodeError:
                        logger.debug(content)

            else:
                logger.debug("⚙️ Observation")
                logger.debug(
                    "Tool execution step completed, but no response data found."
                )
                pass
        except Exception as e:
            logger.error(f"Error processing tool execution: {str(e)}")

        return tool_results

    def _format_web_search_results(self, parsed_content):
        for i, result in enumerate(parsed_content["top_k"], 1):
            if i <= 3:
                title = result.get("title", "Untitled")
                url = result.get("url", "")
                content_text = result.get("content", "").strip()
                yield f"\n- **{title}**\n  {content_text}\n  [Source]({url})\n"

    def _format_results_list(self, results):
        for i, result in enumerate(results, 1):
            if i <= 3:
                if isinstance(result, dict):
                    name = result.get("name", result.get("title", "Result " + str(i)))
                    description = result.get(
                        "description",
                        result.get("content", result.get("summary", "")),
                    )
                    yield f"\n- **{name}**\n  {description}\n"
                else:
                    yield f"\n- {result}\n"

    def _format_dict_results(self, parsed_content):
        yield "\n```\n"
        for key, value in list(parsed_content.items())[:5]:
            if isinstance(value, str) and len(value) < 100:
                yield f"{key}: {value}\n"
            else:
                yield f"{key}: [Complex data]\n"
        yield "```\n"

    def _format_list_results(self, parsed_content):
        yield "\n"
        for _, item in enumerate(parsed_content[:3], 1):
            if isinstance(item, str):
                yield f"- {item}\n"
            elif isinstance(item, dict) and "text" in item:
                yield f"- {item['text']}\n"
            elif isinstance(item, dict) and len(item) > 0:
                first_value = next(iter(item.values()))
                if isinstance(first_value, str) and len(first_value) < 100:
                    yield f"- {first_value}\n"

    def _format_tool_results_summary_json(self, tool_results):
        """JSON-emitting version of tool results summary for AI SDK
        compatibility"""
        summary_text = "Here's what I found:\n"

        for tool_name, content in tool_results:
            try:
                parsed_content = json.loads(content)

                if tool_name == "web_search" and "top_k" in parsed_content:
                    # Format web search results
                    for i, result in enumerate(parsed_content["top_k"], 1):
                        if i <= 3:
                            title = result.get("title", "Untitled")
                            url = result.get("url", "")
                            content_text = result.get("content", "").strip()
                            summary_text += (
                                f"\n- **{title}**\n  {content_text}\n  "
                                f"[Source]({url})\n"
                            )

                elif "results" in parsed_content and isinstance(
                    parsed_content["results"], list
                ):
                    # Format results list
                    for i, result in enumerate(parsed_content["results"], 1):
                        if i <= 3:
                            if isinstance(result, dict):
                                name = result.get(
                                    "name",
                                    result.get("title", "Result " + str(i)),
                                )
                                description = result.get(
                                    "description",
                                    result.get("content", result.get("summary", "")),
                                )
                                summary_text += f"\n- **{name}**\n  {description}\n"
                            else:
                                summary_text += f"\n- {result}\n"

                elif isinstance(parsed_content, dict) and len(parsed_content) > 0:
                    # Format dictionary results
                    summary_text += "\n```\n"
                    for key, value in list(parsed_content.items())[:5]:
                        if isinstance(value, str) and len(value) < 100:
                            summary_text += f"{key}: {value}\n"
                        else:
                            summary_text += f"{key}: [Complex data]\n"
                    summary_text += "```\n"

                elif isinstance(parsed_content, list) and len(parsed_content) > 0:
                    # Format list results
                    summary_text += "\n"
                    for _, item in enumerate(parsed_content[:3], 1):
                        if isinstance(item, str):
                            summary_text += f"- {item}\n"
                        elif isinstance(item, dict) and "text" in item:
                            summary_text += f"- {item['text']}\n"
                        elif isinstance(item, dict) and len(item) > 0:
                            first_value = next(iter(item.values()))
                            if isinstance(first_value, str) and len(first_value) < 100:
                                summary_text += f"- {first_value}\n"

            except json.JSONDecodeError:
                summary_text += (
                    f"\n**{tool_name}** was used but returned complex data.\n"
                )
            except (TypeError, AttributeError, KeyError, IndexError) as e:
                summary_text += (
                    f"\n**{tool_name}** was used but encountered an error: "
                    f"{type(e).__name__}\n"
                )

        # Return as JSON object with type and content
        yield json.dumps({"type": "text", "content": summary_text})

    def _handle_regular_response(self, turn_response, session_id: str):
        # Send session ID first to help client initialize the connection
        yield json.dumps({"type": "session", "sessionId": session_id})

        current_step_content = ""

        try:
            for response in turn_response:
                # Check if this is an error response from LlamaStack
                if hasattr(response, "error") and response.error:
                    error_message = response.error.get("message", str(response.error))
                    logger.error(f"LlamaStack error response: {error_message}")

                    # Handle specific websearch tool error
                    if "Tool group 'builtin::websearch' not found" in error_message:
                        error_message = (
                            "This assistant is not available right now. It needs internet search tools "
                            "(such as Tavily) that aren't set up yet. Please try a different assistant "
                            "or contact your administrator."
                        )

                    yield json.dumps(
                        {
                            "type": "error",
                            "content": error_message,
                        }
                    )
                    return

                # Robust payload validation (same as ReAct)
                if not hasattr(response, "event") or not hasattr(
                    response.event, "payload"
                ):
                    logger.error(f"Invalid response structure: {response}")
                    yield json.dumps(
                        {
                            "type": "error",
                            "content": (
                                "Received malformed response from server. "
                                "Please try again."
                            ),
                        }
                    )
                    return

                payload = response.event.payload
                logger.debug(f"Regular agent response: {payload}")

                # Handle step progress (accumulate text like ReAct)
                if payload.event_type == "step_progress" and hasattr(
                    payload.delta, "text"
                ):
                    text_chunk = payload.delta.text
                    logger.debug(f"Regular agent received text chunk: '{text_chunk}'")
                    current_step_content += text_chunk
                    logger.debug(
                        f"Regular agent accumulated text: '{current_step_content}'"
                    )
                    continue

                # Handle step completion (send accumulated content)
                if payload.event_type == "step_complete":
                    step_details = payload.step_details

                    if step_details.step_type == "inference":
                        # Send accumulated content as single chunk (like ReAct)
                        if current_step_content.strip():
                            # Clean the content like ReAct agents do
                            cleaned_text = current_step_content.strip()
                            # Filter out system tokens like [Inst] << SYSt>>
                            cleaned_text = re.sub(
                                r"\[Inst\].*?<<\s*SYSt\s*>>",
                                "",
                                cleaned_text,
                                flags=re.DOTALL,
                            )
                            cleaned_text = re.sub(r"<<\s*SYSt\s*>>", "", cleaned_text)
                            cleaned_text = re.sub(r"\[Inst\]", "", cleaned_text)
                            cleaned_text = cleaned_text.strip()

                            if cleaned_text:
                                logger.debug(
                                    f"Regular agent sending cleaned inference "
                                    f"response: '{cleaned_text}'"
                                )
                                yield json.dumps(
                                    {
                                        "type": "text",
                                        "content": cleaned_text,
                                    }
                                )
                        current_step_content = ""

                    elif step_details.step_type == "tool_execution":
                        # Send accumulated content before tool info
                        if current_step_content.strip():
                            yield json.dumps(
                                {
                                    "type": "text",
                                    "content": current_step_content,
                                }
                            )
                        current_step_content = ""

                        if step_details.tool_calls:
                            tool_call = step_details.tool_calls[0]
                            tool_name = str(tool_call.tool_name)
                            yield json.dumps(
                                {
                                    "type": "tool",
                                    "content": f'Using "{tool_name}" tool:',
                                    "tool": {"name": tool_name},
                                }
                            )
                    else:
                        current_step_content = ""

            # Send any remaining accumulated content
            if current_step_content.strip():
                # Clean the content like ReAct agents do
                cleaned_text = current_step_content.strip()
                # Filter out system tokens like [Inst] << SYSt>>
                cleaned_text = re.sub(
                    r"\[Inst\].*?<<\s*SYSt\s*>>",
                    "",
                    cleaned_text,
                    flags=re.DOTALL,
                )
                cleaned_text = re.sub(r"<<\s*SYSt\s*>>", "", cleaned_text)
                cleaned_text = re.sub(r"\[Inst\]", "", cleaned_text)
                cleaned_text = cleaned_text.strip()

                if cleaned_text:
                    logger.debug(
                        f"Regular agent sending cleaned final response: "
                        f"'{cleaned_text}'"
                    )
                    yield json.dumps(
                        {
                            "type": "text",
                            "content": cleaned_text,
                        }
                    )

        except Exception as e:
            logger.error(f"Error in Regular response processing: {e}")
            yield json.dumps(
                {
                    "type": "error",
                    "content": (
                        f"An error occurred while processing the response: {str(e)}"
                    ),
                }
            )

    def stream(
        self,
        agent_id: str,
        session_id: str,
        prompt: InterleavedContent,
        agent_type_str: str = "ReAct",
    ):
        """
        Stream chat response using LlamaStack with timeout and resource
        management.

        Args:
            agent_id: The ID of the agent from LlamaStack
            session_id: The ID of the session from LlamaStack
            prompt: The user's message
            agent_type_str: The agent type ("ReAct" or "Regular")
        """
        try:
            # Create agent instance using existing agent_id
            agent = asyncio.run(self._create_agent_with_existing_id(agent_id))

            self.log.info(f"Using agent: {agent_id} with session: {session_id}")

            # Get existing messages from the session
            messages = [UserMessage(role="user", content=prompt)]

            async def async_iterator_to_iterator():
                # Create turn with LlamaStack with timeout
                try:
                    response = await asyncio.wait_for(
                        agent.create_turn(
                            session_id=session_id,
                            messages=messages,
                            stream=True,
                        ),
                        timeout=120.0,  # 120 second timeout for large models
                    )
                    result_list = []
                    async for item in response:
                        result_list.append(item)
                    return result_list
                except asyncio.TimeoutError:
                    self.log.error(f"Timeout occurred for agent {agent_id}")
                    raise Exception(
                        (
                            "Request timed out after 2 minutes. Large models "
                            "may take longer to respond. Please try again or "
                            "use a simpler question."
                        )
                    )
                except Exception as e:
                    self.log.error(f"Error in agent turn creation: {e}")
                    raise

            turn_response = asyncio.run(async_iterator_to_iterator())

            # Use passed agent type
            agent_type = (
                AgentType.REACT if agent_type_str == "ReAct" else AgentType.REGULAR
            )

            # Stream the response
            yield from self._response_generator(turn_response, session_id, agent_type)

        except Exception as e:
            self.log.error(
                f"Error in stream for agent {agent_id}, session {session_id}: {e}"
            )

            # Handle specific websearch tool error with user-friendly message
            error_message = str(e)
            if "Tool group 'builtin::websearch' not found" in error_message:
                error_message = (
                    "This assistant is not available right now. It needs internet search tools "
                    "(such as Tavily) that aren't set up yet. Please try a different assistant "
                    "or contact your administrator."
                )
            else:
                error_message = (
                    f"Error occurred while processing your request: {error_message}"
                )

            # Log what we're about to yield for debugging
            error_response = json.dumps(
                {
                    "type": "error",
                    "content": error_message,
                }
            )
            self.log.error(f"Yielding error response: {error_response}")

            yield error_response

    def _process_inference_step_simple(
        self, current_step_content, tool_results, final_answer
    ):
        """
        Simplified inference step processing with robust error handling.

        This method handles both JSON and plain text responses gracefully.
        """
        try:
            # Try to parse as JSON first
            if current_step_content.strip().startswith("{"):
                react_output_data = json.loads(current_step_content.strip())
                thought = react_output_data.get("thought")
                answer = react_output_data.get("answer")

                if answer and answer != "null" and answer is not None:
                    final_answer = answer

                unified_response = {
                    "type": "react_unified",
                    "thought": (thought if thought else "Processing your request..."),
                    "action": None,
                    "answer": (
                        answer
                        if answer and answer != "null"
                        else "I'm working on your question."
                    ),
                    "tool_results": tool_results if tool_results else [],
                }
                yield json.dumps(unified_response)
            else:
                # Handle plain text response
                cleaned_text = current_step_content.strip()
                if cleaned_text:
                    unified_response = {
                        "type": "react_unified",
                        "thought": (
                            "I'm processing your request and providing a "
                            "helpful response."
                        ),
                        "action": None,
                        "answer": cleaned_text,
                        "tool_results": tool_results if tool_results else [],
                    }
                    yield json.dumps(unified_response)
                else:
                    # Empty response fallback
                    unified_response = {
                        "type": "react_unified",
                        "thought": "Processing your request.",
                        "action": None,
                        "answer": (
                            "I understand your question. Let me provide "
                            "helpful response."
                        ),
                        "tool_results": tool_results if tool_results else [],
                    }
                    yield json.dumps(unified_response)

        except json.JSONDecodeError:
            # JSON parsing failed, treat as plain text
            cleaned_text = current_step_content.strip()
            if cleaned_text:
                unified_response = {
                    "type": "react_unified",
                    "thought": (
                        "I'm processing your request and providing a helpful "
                        "response."
                    ),
                    "action": None,
                    "answer": cleaned_text,
                    "tool_results": tool_results if tool_results else [],
                }
                yield json.dumps(unified_response)
            else:
                # Empty response fallback
                unified_response = {
                    "type": "react_unified",
                    "thought": "Processing your request.",
                    "action": None,
                    "answer": (
                        "I understand your question. Let me provide "
                        "helpful response."
                    ),
                    "tool_results": tool_results if tool_results else [],
                }
                yield json.dumps(unified_response)
        except Exception as e:
            logger.error(f"Error in inference step processing: {e}")
            # Final fallback
            yield json.dumps(
                {
                    "type": "react_unified",
                    "thought": "Processing your request.",
                    "action": None,
                    "answer": (
                        "I understand your question. Let me provide "
                        "helpful response."
                    ),
                    "tool_results": tool_results if tool_results else [],
                }
            )

        return final_answer

    def _process_tool_execution_simple(self, step_details, tool_results):
        """Simplified tool execution processing."""
        try:
            if step_details.tool_calls:
                tool_call = step_details.tool_calls[0]
                tool_name = str(tool_call.tool_name)
                tool_results.append(
                    {"name": tool_name, "result": "Tool executed successfully"}
                )
        except Exception as e:
            logger.error(f"Error in tool execution processing: {e}")

        return tool_results

    def _format_tool_results_simple(self, tool_results):
        """Simplified tool results formatting."""
        try:
            if tool_results:
                yield json.dumps(
                    {
                        "type": "tool_results",
                        "content": (
                            f"Used {len(tool_results)} tools to help answer "
                            f"your question."
                        ),
                        "tools": tool_results,
                    }
                )
        except Exception as e:
            logger.error(f"Error in tool results formatting: {e}")
