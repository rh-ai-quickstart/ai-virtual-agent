import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  User,
  NewUser,
  fetchUsers,
  fetchCurrentUser,
  fetchUserById,
  updateUserAgents,
  getUserAgents,
  removeUserAgents,
  createUser,
} from '@/services/users';

export const useUsers = () => {
  const queryClient = useQueryClient();

  // Query for all users
  const usersQuery = useQuery<User[], Error>({
    queryKey: ['users'],
    queryFn: fetchUsers,
  });

  // Query for current user
  const currentUserQuery = useQuery<User, Error>({
    queryKey: ['users', 'current'],
    queryFn: fetchCurrentUser,
    retry: (failureCount, error) => {
      // Don't retry if user is not authenticated
      if (error.message === 'User not authenticated') {
        return false;
      }
      return failureCount < 3;
    },
  });

  // Hook for fetching a specific user
  const useUser = (userId: string) => {
    return useQuery<User, Error>({
      queryKey: ['users', userId],
      queryFn: () => fetchUserById(userId),
      enabled: !!userId,
    });
  };

  // Hook for fetching user's assigned agents
  const useUserAgents = (userId: string) => {
    return useQuery<string[], Error>({
      queryKey: ['users', userId, 'agents'],
      queryFn: () => getUserAgents(userId),
      enabled: !!userId,
    });
  };

  // Mutation for updating user agents
  const updateUserAgentsMutation = useMutation<User, Error, { userId: string; agentIds: string[] }>(
    {
      mutationFn: ({ userId, agentIds }) => updateUserAgents(userId, agentIds),
      onSuccess: (_, variables) => {
        // Invalidate related queries
        void queryClient.invalidateQueries({ queryKey: ['users', variables.userId] });
        void queryClient.invalidateQueries({ queryKey: ['users', variables.userId, 'agents'] });
      },
      onError: (error) => {
        console.error('Failed to update user agents:', error);
      },
    }
  );

  // Mutation for removing user agents
  const removeUserAgentsMutation = useMutation<User, Error, { userId: string; agentIds: string[] }>(
    {
      mutationFn: ({ userId, agentIds }) => removeUserAgents(userId, agentIds),
      onSuccess: (_, variables) => {
        // Invalidate related queries
        void queryClient.invalidateQueries({ queryKey: ['users', variables.userId] });
        void queryClient.invalidateQueries({ queryKey: ['users', variables.userId, 'agents'] });
      },
      onError: (error) => {
        console.error('Failed to remove user agents:', error);
      },
    }
  );

  // Mutation for creating a new user
  const createUserMutation = useMutation<User, Error, NewUser>({
    mutationFn: createUser,
    onSuccess: () => {
      // Invalidate users list to refresh the data
      void queryClient.invalidateQueries({ queryKey: ['users'] });
    },
    onError: (error) => {
      console.error('Failed to create user:', error);
    },
  });

  // Helper function to refresh users data
  const refreshUsers = () => {
    void queryClient.invalidateQueries({ queryKey: ['users'] });
  };

  return {
    // Query data and states
    users: usersQuery.data,
    isLoading: usersQuery.isLoading,
    error: usersQuery.error,

    // Current user
    currentUser: currentUserQuery.data,
    isLoadingCurrentUser: currentUserQuery.isLoading,
    currentUserError: currentUserQuery.error,

    // Hooks for specific users and their agents
    useUser,
    useUserAgents,

    // Mutations
    createUser: (newUser: NewUser) => createUserMutation.mutateAsync(newUser),
    updateUserAgents: (userId: string, agentIds: string[]) =>
      updateUserAgentsMutation.mutateAsync({ userId, agentIds }),
    removeUserAgents: (userId: string, agentIds: string[]) =>
      removeUserAgentsMutation.mutateAsync({ userId, agentIds }),

    // Mutation states
    isCreating: createUserMutation.isPending,
    createError: createUserMutation.error,
    isUpdatingAgents: updateUserAgentsMutation.isPending,
    isRemovingAgents: removeUserAgentsMutation.isPending,
    updateError: updateUserAgentsMutation.error,
    removeError: removeUserAgentsMutation.error,

    // Utilities
    refreshUsers,
  };
};
