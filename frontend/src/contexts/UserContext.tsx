import React, { createContext, useContext, ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchCurrentUser } from '@/services/users';
import { User } from '@/types/auth';

interface UserContextType {
  currentUser: User | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

interface UserProviderProps {
  children: ReactNode;
}

export const UserProvider: React.FC<UserProviderProps> = ({ children }) => {
  const {
    data: currentUser,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['currentUser'],
    queryFn: fetchCurrentUser,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: (failureCount, error) => {
      // Don't retry on authentication errors
      if (error.message === 'User not authenticated' || error.message === 'User not found') {
        return false;
      }
      return failureCount < 3;
    },
  });

  const value: UserContextType = {
    currentUser: currentUser || null,
    isLoading,
    error: error?.message || null,
    refetch: () => void refetch(),
  };

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
};

/**
 * Custom hook to access the current user
 *
 * Uses React Query to fetch the current authenticated user from the /profile endpoint.
 * The backend determines the current user based on authentication headers.
 *
 * TODO: Handle authentication flow properly:
 * 1. Redirect to login page when user is not authenticated (401/403 errors), this
 *    might be default behavior when using oauth-proxy.
 * 2. Implement proper login/logout flows, need to determine oauth-proxy logout flow
 * 3. Handle token refresh and session management this may not be needed as oauth-proxy
 *    will handle this in our current implementation.
 *
 * @returns {UserContextType} Object containing:
 *   - currentUser: The current authenticated user object or null
 *   - isLoading: Loading state from React Query
 *   - error: Error message if any (including authentication errors)
 *   - refetch: Function to manually refetch user data
 */
export const useCurrentUser = (): UserContextType => {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useCurrentUser must be used within a UserProvider');
  }
  return context;
};
