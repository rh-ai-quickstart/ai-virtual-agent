import { AGENTS_API_ENDPOINT } from '@/config/api';
import { Agent, NewAgent, ErrorResponse } from '@/types';
import { getUserAgents } from '@/services/users';

export const fetchAgents = async (): Promise<Agent[]> => {
  const response = await fetch(AGENTS_API_ENDPOINT, {
    credentials: 'include',
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as Agent[];
};

/**
 * Fetch agents that are specifically assigned to a user
 *
 * TODO: This currently filters all agents by user assignment.
 * Once proper authentication is implemented, this should work with
 * the authenticated user's agent assignments.
 */
export const fetchUserAgents = async (userId: string): Promise<Agent[]> => {
  try {
    // Get the user's assigned agent IDs
    const userAgentIds = await getUserAgents(userId);

    // Get all available agents
    const allAgents = await fetchAgents();

    // Filter agents to only include those assigned to the user
    const userAgents = allAgents.filter((agent) => userAgentIds.includes(agent.id));

    return userAgents;
  } catch (error) {
    console.error('Error fetching user agents:', error);
    throw new Error('Failed to fetch user agents');
  }
};

export const createAgent = async (newAgent: NewAgent): Promise<Agent> => {
  const response = await fetch(AGENTS_API_ENDPOINT, {
    credentials: 'include',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(newAgent),
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as Agent;
};

export const deleteAgent = async (agent_id: string): Promise<void> => {
  const response = await fetch(AGENTS_API_ENDPOINT + agent_id, {
    credentials: 'include',
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  return;
};
