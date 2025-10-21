"""
Main API router that includes all v1 endpoints.
"""

from fastapi import APIRouter

from .agent_templates import router as agent_templates_router
from .attachments import router as attachments_router

# Import individual routers
from .chat import router as chat_router
from .chat_sessions import router as chat_sessions_router
from .knowledge_bases import router as knowledge_bases_router
from .llama_stack import router as llama_stack_router
from .users import router as users_router
from .virtual_agents import router as virtual_agents_router

api_router = APIRouter()

# Include individual routers
api_router.include_router(
    llama_stack_router, prefix="/llama_stack", tags=["llama_stack"]
)
api_router.include_router(chat_router, tags=["chat"])
api_router.include_router(attachments_router, tags=["attachments"])
api_router.include_router(knowledge_bases_router, tags=["knowledge_bases"])
api_router.include_router(agent_templates_router, tags=["agent_templates"])
api_router.include_router(chat_sessions_router, tags=["chat_sessions"])
api_router.include_router(users_router, tags=["users"])
api_router.include_router(virtual_agents_router, tags=["virtual_agents"])


# Health check endpoint
@api_router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
