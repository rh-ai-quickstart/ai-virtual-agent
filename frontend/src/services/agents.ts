import { AGENTS_API_ENDPOINT } from '@/config/api';
import { Agent, NewAgent } from '@/routes/config/agents';

export const fetchAgents = async (): Promise<Agent[]> => {
  const response = await fetch(AGENTS_API_ENDPOINT);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as Agent[];
};

export const createAgent = async (newAgent: NewAgent): Promise<Agent> => {
  const response = await fetch(AGENTS_API_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(newAgent),
  });
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as Agent;
};

export const deleteAgent = async (agent_id: string): Promise<void> => {
  const response = await fetch(AGENTS_API_ENDPOINT + agent_id, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  return;
};
