import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Agent, NewAgent } from '@/types/agent';
import { fetchAgents, fetchUserAgents, createAgent, deleteAgent } from '@/services/agents';

export const useAgents = () => {
  const queryClient = useQueryClient();

  // Query for all agents
  const agentsQuery = useQuery<Agent[], Error>({
    queryKey: ['agents'],
    queryFn: fetchAgents,
  });

  // Query for user-specific agents
  const useUserAgents = (userId: string) => {
    return useQuery<Agent[], Error>({
      queryKey: ['agents', 'user', userId],
      queryFn: () => fetchUserAgents(userId),
      enabled: !!userId,
    });
  };

  // Mutation for creating agents
  const createAgentMutation = useMutation<Agent, Error, NewAgent>({
    mutationFn: createAgent,
    onSuccess: () => {
      // Invalidate agents queries to refetch data
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
    onError: (error) => {
      console.error('Failed to create agent:', error);
    },
  });

  // Mutation for deleting agents
  const deleteAgentMutation = useMutation<void, Error, string>({
    mutationFn: deleteAgent,
    onSuccess: () => {
      // Invalidate agents queries to refetch data
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
    onError: (error) => {
      console.error('Failed to delete agent:', error);
    },
  });

  // Helper function to refresh agents data
  const refreshAgents = () => {
    void queryClient.invalidateQueries({ queryKey: ['agents'] });
  };

  return {
    // Query data and states
    agents: agentsQuery.data,
    isLoading: agentsQuery.isLoading,
    error: agentsQuery.error,

    // User agents query hook
    useUserAgents,

    // Mutations
    createAgent: createAgentMutation.mutateAsync,
    deleteAgent: deleteAgentMutation.mutateAsync,

    // Mutation states
    isCreating: createAgentMutation.isPending,
    isDeleting: deleteAgentMutation.isPending,
    createError: createAgentMutation.error,
    deleteError: deleteAgentMutation.error,

    // Utilities
    refreshAgents,
  };
};
