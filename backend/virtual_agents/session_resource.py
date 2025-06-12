from __future__ import annotations

import logging
from typing import List

import httpx
from fastapi import HTTPException
from llama_stack_client._types import NOT_GIVEN, Body, Headers, NotGiven, Query
from llama_stack_client.resources.agents.session import SessionResource

log = logging.getLogger(__name__)


class EnhancedSessionResource(SessionResource):
    def list(
        self,
        agent_id: str,
        *,
        _extra_headers: Headers | None = None,
        _extra_query: Query | None = None,
        _extra_body: Body | None = None,
        _timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> List[dict]:  # Return List[dict] instead of List[Session]
        """List all sessions for a specific agent"""
        if not agent_id:
            raise ValueError(
                f"Expected a non-empty value for `agent_id` but received {agent_id!r}"
            )

        log.info(f"Making request to: /v1/agents/{agent_id}/sessions")

        try:
            log.info("About to call self._get()...")

            import httpx

            # Use direct HTTP request to avoid client parsing issues
            with httpx.Client() as http_client:
                response = http_client.get(
                    f"http://localhost:8321/v1/agents/{agent_id}/sessions",
                    headers={"Accept": "application/json"},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

            log.info("Successfully got response from self._get()")
            log.info(f"Response type: {type(response)}")

            # Extract sessions data
            sessions_data = data.get("data", [])
            log.info(f"Found {len(sessions_data)} sessions in response")

            # Return the actual sessions data, not empty list!
            return sessions_data

        except Exception as e:
            log.error(f"Error in session list: {e}")
            log.error(f"Exception type: {type(e)}")
            import traceback

            log.error(f"Full traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500, detail=f"Failed to fetch sessions: {str(e)}"
            )

    def delete(
        self,
        session_id: str,
        agent_id: str,
        *,
        _extra_headers: Headers | None = None,
        _extra_query: Query | None = None,
        _extra_body: Body | None = None,
        _timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> dict:
        """Delete a session for a specific agent"""
        if not agent_id:
            raise ValueError(
                f"Expected a non-empty value for `agent_id` but received {agent_id!r}"
            )
        if not session_id:
            raise ValueError(
                "Expected a non-empty value for `session_id` but received "
                f"{session_id!r}"
            )

        log.info(
            "Making DELETE request to: " f"/v1/agents/{agent_id}/session/{session_id}"
        )

        try:
            import httpx

            # Use direct HTTP request to delete session
            with httpx.Client() as http_client:
                response = http_client.delete(
                    f"http://localhost:8321/v1/agents/{agent_id}/session/{session_id}",
                    headers={"Accept": "application/json"},
                    timeout=30.0,
                )
                response.raise_for_status()

                log.info(
                    f"Successfully deleted session {session_id} for agent "
                    f"{agent_id}"
                )
                return {"message": "Session deleted successfully"}

        except httpx.HTTPStatusError as e:
            log.error(
                "HTTP error deleting session: "
                f"{e.response.status_code} - {e.response.text}"
            )
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=404,
                    detail=f"Session {session_id} not found for agent {agent_id}",
                )
            else:
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Failed to delete session: {e.response.text}",
                )
        except Exception as e:
            log.error(f"Error deleting session: {e}")
            log.error(f"Exception type: {type(e)}")
            import traceback

            log.error(f"Full traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=500, detail=f"Failed to delete session: {str(e)}"
            )
