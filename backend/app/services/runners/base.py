"""
Base runner interface for agent frameworks.

All runner implementations (LlamaStack, LangGraph, CrewAI) must implement
this interface so the ChatService can delegate to any runner transparently.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BaseRunner(ABC):
    """
    Abstract base class for agent runners.

    Each runner handles a specific agent framework and translates its
    responses into a unified SSE event stream for the frontend.

    Args:
        request: FastAPI request object (for accessing external services)
        db: Database session
        user_id: ID of the authenticated user
    """

    def __init__(self, request: Request, db: AsyncSession, user_id: Any):
        self.request = request
        self.db = db
        self.user_id = user_id

    @abstractmethod
    async def stream(
        self,
        agent: Any,  # VirtualAgent object
        session_id: str,
        prompt: Any,  # Can be str or InterleavedContent
    ) -> AsyncIterator[str]:
        """
        Stream a response for the given agent and prompt.

        Must yield SSE-formatted strings (e.g. 'data: {"type": ...}\\n\\n')
        using the normalized event types the frontend expects:
        - reasoning: thinking/reasoning text
        - response: output text deltas
        - tool_call: tool invocations and results
        - error: error messages
        - node_started: graph node began execution (LangGraph/CrewAI)
        - node_completed: graph node finished (LangGraph/CrewAI)

        The stream must end with 'data: [DONE]\\n\\n'.

        Args:
            agent: VirtualAgent object (already fetched with template)
            session_id: Chat session ID
            prompt: User's message/input

        Yields:
            SSE-formatted JSON strings
        """
        ...  # pragma: no cover
