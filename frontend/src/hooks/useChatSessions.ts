import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ChatSessionSummary,
  ChatSessionDetail,
  fetchChatSessions,
  fetchChatSession,
  deleteChatSession,
  createChatSession,
} from '@/services/chat-sessions';

export const useChatSessions = (agentId?: string) => {
  const queryClient = useQueryClient();

  // Query for chat sessions (optionally filtered by agent)
  const chatSessionsQuery = useQuery<ChatSessionSummary[], Error>({
    queryKey: ['chatSessions', agentId],
    queryFn: () => fetchChatSessions(agentId),
  });

  // Hook for fetching a specific session
  const useChatSession = (sessionId: string, sessionAgentId: string) => {
    return useQuery<ChatSessionDetail, Error>({
      queryKey: ['chatSession', sessionId, sessionAgentId],
      queryFn: () => fetchChatSession(sessionId, sessionAgentId),
      enabled: !!sessionId && !!sessionAgentId,
    });
  };

  // Mutation for deleting sessions
  const deleteChatSessionMutation = useMutation<
    void,
    Error,
    { sessionId: string; agentId: string }
  >({
    mutationFn: ({ sessionId, agentId }) => deleteChatSession(sessionId, agentId),
    onSuccess: () => {
      // Invalidate sessions queries
      void queryClient.invalidateQueries({ queryKey: ['chatSessions'] });
    },
    onError: (error) => {
      console.error('Failed to delete chat session:', error);
    },
  });

  // Mutation for creating sessions
  const createChatSessionMutation = useMutation<
    ChatSessionDetail,
    Error,
    { agentId: string; sessionName?: string }
  >({
    mutationFn: ({ agentId, sessionName }) => createChatSession(agentId, sessionName),
    onSuccess: () => {
      // Invalidate sessions queries
      void queryClient.invalidateQueries({ queryKey: ['chatSessions'] });
    },
    onError: (error) => {
      console.error('Failed to create chat session:', error);
    },
  });

  // Helper function to refresh sessions
  const refreshSessions = () => {
    void queryClient.invalidateQueries({ queryKey: ['chatSessions'] });
  };

  return {
    // Query data and states
    chatSessions: chatSessionsQuery.data,
    isLoading: chatSessionsQuery.isLoading,
    error: chatSessionsQuery.error,

    // Session detail hook
    useChatSession,

    // Mutations
    deleteSession: (sessionId: string, sessionAgentId: string) =>
      deleteChatSessionMutation.mutateAsync({ sessionId, agentId: sessionAgentId }),
    createSession: (sessionAgentId: string, sessionName?: string) =>
      createChatSessionMutation.mutateAsync({ agentId: sessionAgentId, sessionName }),

    // Mutation states
    isDeleting: deleteChatSessionMutation.isPending,
    isCreating: createChatSessionMutation.isPending,
    deleteError: deleteChatSessionMutation.error,
    createError: createChatSessionMutation.error,

    // Utilities
    refreshSessions,
  };
};
