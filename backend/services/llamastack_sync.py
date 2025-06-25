"""
LlamaStack synchronization service for event-driven sync operations.
"""

import logging
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..api.llamastack import sync_client

log = logging.getLogger(__name__)


class LlamaStackSyncService:
    """Service for synchronizing data with LlamaStack"""

    @staticmethod
    async def sync_knowledge_base_create(kb: models.KnowledgeBase) -> bool:
        """
        Sync a newly created knowledge base to LlamaStack.
        Returns True if successful, False otherwise.
        """
        try:
            log.info(f"Syncing knowledge base creation to LlamaStack: {kb.name}")

            # Register the vector database in LlamaStack
            await sync_client.vector_dbs.register(
                vector_db_id=kb.vector_db_name,
                embedding_model=kb.embedding_model,
                embedding_dimension=384,  # Default dimension
                provider_id=kb.provider_id or "pgvector",
            )

            log.info(f"Successfully synced knowledge base creation: {kb.name}")
            return True

        except Exception as e:
            log.error(f"Failed to sync knowledge base creation to LlamaStack: {str(e)}")
            return False

    @staticmethod
    async def sync_knowledge_base_update(kb: models.KnowledgeBase) -> bool:
        """
        Sync a knowledge base update to LlamaStack.
        Note: LlamaStack doesn't have update operations, so we re-register.
        """
        try:
            log.info(f"Syncing knowledge base update to LlamaStack: {kb.name}")

            # Since LlamaStack doesn't have update, we re-register
            # This might overwrite existing data, but ensures consistency
            await sync_client.vector_dbs.register(
                vector_db_id=kb.vector_db_name,
                embedding_model=kb.embedding_model,
                embedding_dimension=384,
                provider_id=kb.provider_id or "pgvector",
            )

            log.info(f"Successfully synced knowledge base update: {kb.name}")
            return True

        except Exception as e:
            log.error(f"Failed to sync knowledge base update to LlamaStack: {str(e)}")
            return False

    @staticmethod
    async def sync_knowledge_base_delete(kb_name: str, vector_db_name: str) -> bool:
        """
        Sync a knowledge base deletion to LlamaStack.
        Note: LlamaStack doesn't have delete operations, so we log this action.
        """
        try:
            log.warning(
                "Knowledge base deleted from local DB but cannot be removed "
                f"from LlamaStack (no delete API): {kb_name}"
            )
            # TODO: When LlamaStack supports delete operations, implement here
            return True

        except Exception as e:
            log.error(f"Failed to handle knowledge base deletion sync: {str(e)}")
            return False

    @staticmethod
    async def sync_mcp_server_create(server: models.MCPServer) -> bool:
        """
        Sync a newly created MCP server to LlamaStack.
        Note: MCP servers are typically registered directly with LlamaStack.
        """
        try:
            log.info(f"MCP server created locally: {server.name}")
            # MCP servers are usually managed externally and discovered by LlamaStack
            # We don't need to register them as they should be auto-discovered
            log.info(f"MCP server sync completed: {server.name}")
            return True

        except Exception as e:
            log.error(f"Failed to sync MCP server creation: {str(e)}")
            return False

    @staticmethod
    async def sync_mcp_server_update(server: models.MCPServer) -> bool:
        """
        Sync an MCP server update to LlamaStack.
        """
        try:
            log.info(f"MCP server updated locally: {server.name}")
            # MCP servers are managed externally, updates should be
            # reflected automatically
            return True

        except Exception as e:
            log.error(f"Failed to sync MCP server update: {str(e)}")
            return False

    @staticmethod
    async def sync_mcp_server_delete(server_name: str) -> bool:
        """
        Sync an MCP server deletion to LlamaStack.
        """
        try:
            log.warning(f"MCP server deleted from local DB: {server_name}")
            # MCP servers are managed externally, LlamaStack will discover the removal
            return True

        except Exception as e:
            log.error(f"Failed to handle MCP server deletion sync: {str(e)}")
            return False

    @staticmethod
    async def validate_sync_status(db: AsyncSession) -> Dict[str, Any]:
        """
        Validate that local database is in sync with LlamaStack.
        Returns a report of sync status.
        """
        try:
            log.info("Validating sync status with LlamaStack")

            # Get LlamaStack vector databases
            llamastack_vdbs = await sync_client.vector_dbs.list()
            llamastack_vdb_names = {vdb.identifier for vdb in llamastack_vdbs}

            # Get local knowledge bases
            from sqlalchemy import select

            result = await db.execute(select(models.KnowledgeBase))
            local_kbs = result.scalars().all()
            local_vdb_names = {kb.vector_db_name for kb in local_kbs}

            # Compare
            only_in_llamastack = llamastack_vdb_names - local_vdb_names
            only_in_local = local_vdb_names - llamastack_vdb_names
            in_both = llamastack_vdb_names & local_vdb_names

            return {
                "sync_status": (
                    "ok"
                    if not only_in_llamastack and not only_in_local
                    else "drift_detected"
                ),
                "total_local": len(local_vdb_names),
                "total_llamastack": len(llamastack_vdb_names),
                "in_sync": len(in_both),
                "only_in_llamastack": list(only_in_llamastack),
                "only_in_local": list(only_in_local),
                "timestamp": None,  # Will be set by caller
            }

        except Exception as e:
            log.error(f"Failed to validate sync status: {str(e)}")
            return {"sync_status": "error", "error": str(e), "timestamp": None}
