import { USERS_API_ENDPOINT } from '@/config/api';
import { User } from '@/types/auth';

// Re-export types for backward compatibility
export type { User } from '@/types/auth';

export const fetchUsers = async (): Promise<User[]> => {
  const response = await fetch(USERS_API_ENDPOINT);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as User[];
};

export const fetchCurrentUser = async (): Promise<User> => {
  const response = await fetch(`${USERS_API_ENDPOINT}profile/`);
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('User not authenticated');
    }
    if (response.status === 403) {
      throw new Error('User not found');
    }
    throw new Error('Failed to fetch current user');
  }
  const data: unknown = await response.json();
  return data as User;
};

export const fetchUserById = async (userId: string): Promise<User> => {
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}`);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as User;
};

export const updateUserAgents = async (userId: string, agentIds: string[]): Promise<User> => {
  // Note: This adds the specified agents to the user's agent list
  // Agents are shared across users and duplicate agent IDs are prevented
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}/agents`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ agent_ids: agentIds }),
  });
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as User;
};

export const getUserAgents = async (userId: string): Promise<string[]> => {
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}/agents`);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as string[];
};

export const removeUserAgents = async (userId: string, agentIds: string[]): Promise<User> => {
  // Note: This removes the specified agents from the user's agent list
  // Agents remain in LlamaStack and can be assigned to other users
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}/agents`, {
    method: 'DELETE',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ agent_ids: agentIds }),
  });
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as User;
};
