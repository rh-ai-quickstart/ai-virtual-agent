import os

from dotenv import load_dotenv
from llama_stack_client import LlamaStackClient

from ..virtual_agents.agent_resource import EnhancedAgentResource

load_dotenv()

LLAMASTACK_URL = os.getenv("LLAMASTACK_URL", "http://localhost:8321")

client = LlamaStackClient(
    base_url=LLAMASTACK_URL,
)

client.agents = EnhancedAgentResource(client)
