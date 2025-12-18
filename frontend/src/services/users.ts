import { USERS_API_ENDPOINT } from '@/config/api';
import { User } from '@/types/auth';
import { ErrorResponse } from '@/types';

// Re-export types for backward compatibility
export type { User } from '@/types/auth';

export const fetchUsers = async (): Promise<User[]> => {
  const response = await fetch(USERS_API_ENDPOINT, {
    credentials: 'include',
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as User[];
};

export const fetchCurrentUser = async (): Promise<User> => {
  const response = await fetch(`${USERS_API_ENDPOINT}profile`, {
    credentials: 'include',
  });
  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('User not authenticated');
    }
    if (response.status === 403) {
      throw new Error('User not found');
    }
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to fetch current user' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to fetch current user');
  }
  const data: unknown = await response.json();
  return data as User;
};

export const fetchUserById = async (userId: string): Promise<User> => {
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}`, {
    credentials: 'include',
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as User;
};

export const updateUserAgents = async (userId: string, agentIds: string[]): Promise<User> => {
  // Note: This adds the specified agents to the user's agent list
  // Agents are shared across users and duplicate agent IDs are prevented
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}/agents`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ agent_ids: agentIds }),
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as User;
};

export const getUserAgents = async (userId: string): Promise<string[]> => {
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}/agents`, {
    credentials: 'include',
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as string[];
};

export const removeUserAgents = async (userId: string, agentIds: string[]): Promise<User> => {
  // Note: This removes the specified agents from the user's agent list
  // Agents remain in LlamaStack and can be assigned to other users
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}/agents`, {
    method: 'DELETE',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ agent_ids: agentIds }),
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as User;
};

export interface NewUser {
  username: string;
  email: string;
  role: 'user' | 'devops' | 'admin';
  agent_ids?: string[];
}

export const createUser = async (newUser: NewUser): Promise<User> => {
  const response = await fetch(USERS_API_ENDPOINT, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(newUser),
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to create user' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to create user');
  }
  const data: unknown = await response.json();
  return data as User;
};

export interface UpdateUser {
  username?: string;
  email?: string;
  role?: 'user' | 'devops' | 'admin';
}

export const updateUser = async (userId: string, updates: UpdateUser): Promise<User> => {
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}`, {
    method: 'PUT',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to update user' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to update user');
  }
  const data: unknown = await response.json();
  return data as User;
};

export const deleteUser = async (userId: string): Promise<void> => {
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to delete user' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to delete user');
  }
};
