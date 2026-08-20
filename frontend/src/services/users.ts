import { USERS_API_ENDPOINT } from '@/config/api';
import { User } from '@/types/auth';
import { ErrorResponse } from '@/types';

export type { User } from '@/types/auth';

export const fetchUsers = async (): Promise<User[]> => {
  const response = await fetch(USERS_API_ENDPOINT);
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
  const response = await fetch(`${USERS_API_ENDPOINT}profile`);
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
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}`);
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
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}/agents`, {
    method: 'POST',
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
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}/agents`);
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
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}/agents`, {
    method: 'DELETE',
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

export const deleteUser = async (userId: string): Promise<void> => {
  const response = await fetch(`${USERS_API_ENDPOINT}${userId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to delete user' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to delete user');
  }
};
