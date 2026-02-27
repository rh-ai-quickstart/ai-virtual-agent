"""
Chat service — dispatches to the appropriate runner based on agent runner_type.

The actual streaming logic lives in the runner implementations under
backend/app/services/runners/.
"""

import logging
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from .runners.base import BaseRunner
from .runners.llamastack_runner import LlamaStackRunner
from ..models.agent import VirtualAgent

logger = logging.getLogger(__name__)

# Valid runner type values
VALID_RUNNER_TYPES = {"llamastack", "langgraph", "crewai"}


class ChatService:
    """
    Chat service that delegates to the appropriate runner based on agent config.

    This class is the single entry point for the chat API endpoint.
    It resolves the runner from the agent's ``runner_type`` field and
    delegates the streaming call.

    Args:
        request: FastAPI request object
        db: Database session
        user_id: ID of the authenticated user
    """

    def __init__(self, request: Request, db: AsyncSession, user_id: Any):
        self.request = request
        self.db = db
        self.user_id = user_id

    def _get_runner(self, runner_type: str) -> BaseRunner:
        """
        Resolve the runner implementation for a given runner type.

        Args:
            runner_type: One of "llamastack", "langgraph", "crewai"

        Returns:
            A runner instance

        Raises:
            ValueError: If the runner_type is not supported
        """
        print(f"Runner type: {runner_type}")
        logger.info(f"Runner type: {runner_type}")
        if runner_type == "llamastack" or not runner_type:
            logger.info("Using LlamaStack runner")
            return LlamaStackRunner(self.request, self.db, self.user_id)
        elif runner_type == "langgraph":
            logger.info("Using LangGraph runner")
            from .runners.langgraph_runner import LangGraphRunner
            return LangGraphRunner(self.request, self.db, self.user_id)
        elif runner_type == "crewai" or runner_type == "crewai_react":
            logger.info("Using CrewAI runner")
            from .runners.crewai_runner import CrewAIRunner
            return CrewAIRunner(self.request, self.db, self.user_id)
        else:
            raise ValueError(
                f"Unsupported runner type: '{runner_type}'. "
                f"Valid types: {', '.join(sorted(VALID_RUNNER_TYPES))}"
            )

    async def stream(
        self,
        agent: VirtualAgent,  # VirtualAgent object (already fetched with template)
        session_id: str,
        prompt,  # Can be str or InterleavedContent
    ):
        """
        Stream a response by delegating to the agent's configured runner.

        Args:
            agent: Virtual agent object (already fetched with template)
            session_id: Session ID
            prompt: User's message/input

        Yields:
            SSE-formatted JSON strings containing response chunks
        """
        runner_type = getattr(agent, "runner_type", None) or "llamastack"
        logger.info(
            f"Chat request for agent {agent.id} "
            f"(runner_type={runner_type}, session={session_id})"
        )

        runner = self._get_runner(runner_type)

        async for event in runner.stream(agent, session_id, prompt):
            yield event
