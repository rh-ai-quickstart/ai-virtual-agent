import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MCPServer, MCPServerCreate } from '@/types';
import {
  fetchMCPServers,
  createMCPServer,
  updateMCPServer,
  deleteMCPServer,
  syncMCPServers,
} from '@/services/mcp-servers';

export const useMCPServers = () => {
  const queryClient = useQueryClient();

  // Query for MCP servers
  const mcpServersQuery = useQuery<MCPServer[], Error>({
    queryKey: ['mcpServers'],
    queryFn: fetchMCPServers,
  });

  // Mutation for creating MCP servers
  const createMCPServerMutation = useMutation<MCPServer, Error, MCPServerCreate>({
    mutationFn: createMCPServer,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['mcpServers'] });
    },
    onError: (error) => {
      console.error('Failed to create MCP server:', error);
    },
  });

  // Mutation for updating MCP servers
  const updateMCPServerMutation = useMutation<
    MCPServer,
    Error,
    { toolgroup_id: string; serverUpdate: MCPServerCreate }
  >({
    mutationFn: ({ toolgroup_id, serverUpdate }) => updateMCPServer(toolgroup_id, serverUpdate),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['mcpServers'] });
    },
    onError: (error) => {
      console.error('Failed to update MCP server:', error);
    },
  });

  // Mutation for deleting MCP servers
  const deleteMCPServerMutation = useMutation<void, Error, string>({
    mutationFn: deleteMCPServer,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['mcpServers'] });
    },
    onError: (error) => {
      console.error('Failed to delete MCP server:', error);
    },
  });

  // Mutation for syncing MCP servers
  const syncMCPServersMutation = useMutation<MCPServer[], Error>({
    mutationFn: syncMCPServers,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['mcpServers'] });
    },
    onError: (error) => {
      console.error('Failed to sync MCP servers:', error);
    },
  });

  // Helper function to refresh MCP servers
  const refreshMCPServers = () => {
    void queryClient.invalidateQueries({ queryKey: ['mcpServers'] });
  };

  return {
    // Query data and states
    mcpServers: mcpServersQuery.data,
    isLoading: mcpServersQuery.isLoading,
    error: mcpServersQuery.error,

    // Mutations
    createMCPServer: createMCPServerMutation.mutateAsync,
    updateMCPServer: (toolgroup_id: string, serverUpdate: MCPServerCreate) =>
      updateMCPServerMutation.mutateAsync({ toolgroup_id, serverUpdate }),
    deleteMCPServer: deleteMCPServerMutation.mutateAsync,
    syncMCPServers: syncMCPServersMutation.mutateAsync,

    // Mutation states
    isCreating: createMCPServerMutation.isPending,
    isUpdating: updateMCPServerMutation.isPending,
    isDeleting: deleteMCPServerMutation.isPending,
    isSyncing: syncMCPServersMutation.isPending,
    createError: createMCPServerMutation.error,
    updateError: updateMCPServerMutation.error,
    deleteError: deleteMCPServerMutation.error,
    syncError: syncMCPServersMutation.error,

    // Utilities
    refreshMCPServers,
  };
};
