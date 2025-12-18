import React, { createContext, useContext, ReactNode } from 'react';
import { useQuery, QueryObserverResult } from '@tanstack/react-query';
import { fetchCurrentUser } from '@/services/users';
import { User } from '@/types/auth';

interface UserContextType {
  currentUser: User | null;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<QueryObserverResult<User, Error>>;
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
  } = useQuery<User, Error>({
    queryKey: ['currentUser'],
    queryFn: fetchCurrentUser,
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
    retry: (failureCount, error: Error) => {
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
    refetch,
  };

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
};

/**
 * Custom hook to access the current user
 *
 * Uses React Query to fetch the current authenticated user from the /profile endpoint.
 * The backend determines the current user based on OAuth proxy authentication headers.
 *
 * Authentication flow:
 * - If user is not authenticated (401/403), protected routes will redirect to /auth/login
 * - Backend handles OAuth flow with Keycloak and session management
 * - Users are auto-created in the database on first successful authentication
 *
 * @returns {UserContextType} Object containing:
 *   - currentUser: The current authenticated user object or null
 *   - isLoading: Loading state from React Query
 *   - error: Error message if any (including authentication errors)
 *   - refetch: Function to manually refetch user data
 */
// eslint-disable-next-line react-refresh/only-export-components
export const useCurrentUser = (): UserContextType => {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useCurrentUser must be used within a UserProvider');
  }
  return context;
};
