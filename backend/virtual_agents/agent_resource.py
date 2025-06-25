# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from __future__ import annotations

from typing import Type, cast

import httpx
from llama_stack_client._base_client import make_request_options
from llama_stack_client._types import NOT_GIVEN, Body, Headers, NotGiven, Query
from llama_stack_client._wrappers import DataWrapper
from llama_stack_client.resources.agents import AsyncAgentsResource

from .agent_model import VirtualAgent, VirtualAgentListResponse
from .session_resource import EnhancedSessionResource

__all__ = ["EnhancedAgentResource"]


class EnhancedAgentResource(AsyncAgentsResource):
    async def retrieve(
        self,
        agent_id: str,
        *,
        # Use the following arguments if you need to pass additional
        # parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined
        # on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VirtualAgent:
        """
        Args:
          extra_headers: Send extra headers

          extra_query: Add additional query parameters to the request

          extra_body: Add additional JSON properties to the request

          timeout: Override the client-level default timeout for this request,
                  in seconds
        """
        if not agent_id:
            raise ValueError(
                f"Expected a non-empty value for `agent_id` but received {agent_id!r}"
            )
        return await self._get(
            f"/v1/agents/{agent_id}",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
            ),
            cast_to=VirtualAgent,
        )

    async def list(
        self,
        *,
        # Use the following arguments if you need to pass additional
        # parameters to the API that aren't available via kwargs.
        # The extra values given here take precedence over values defined
        # on the client or passed to this method.
        extra_headers: Headers | None = None,
        extra_query: Query | None = None,
        extra_body: Body | None = None,
        timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
    ) -> VirtualAgentListResponse:
        return await self._get(
            "/v1/agents",
            options=make_request_options(
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
                post_parser=DataWrapper[VirtualAgentListResponse]._unwrapper,
            ),
            cast_to=cast(
                Type[VirtualAgentListResponse], DataWrapper[VirtualAgentListResponse]
            ),
        )

    @property
    def session(self) -> EnhancedSessionResource:
        return EnhancedSessionResource(self._client)
