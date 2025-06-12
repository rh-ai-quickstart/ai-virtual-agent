# File generated from our OpenAPI spec by Stainless. See CONTRIBUTING.md for details.

from typing import List

from llama_stack_client import BaseModel
from llama_stack_client.types.shared_params.agent_config import AgentConfig
from typing_extensions import Literal, TypeAlias

__all__ = ["VirtualAgent", "VirtualAgentListResponse"]


class VirtualAgent(BaseModel):
    agent_id: str
    agent_config: AgentConfig
    type: Literal["virtual_agent"]


VirtualAgentListResponse: TypeAlias = List[VirtualAgent]
