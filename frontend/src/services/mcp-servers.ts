import { MCP_SERVERS_API_ENDPOINT } from '@/config/api';
import { MCPServer, MCPServerCreate } from '@/types';

export const fetchMCPServers = async (): Promise<MCPServer[]> => {
  const response = await fetch(MCP_SERVERS_API_ENDPOINT);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as MCPServer[];
};

export const createMCPServer = async (
  newServer: MCPServerCreate
): Promise<MCPServer> => {
  const response = await fetch(MCP_SERVERS_API_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(newServer),
  });
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as MCPServer;
};

export const updateMCPServer = async (
  toolgroup_id: string,
  serverUpdate: MCPServerCreate
): Promise<MCPServer> => {
  const response = await fetch(MCP_SERVERS_API_ENDPOINT + toolgroup_id, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(serverUpdate),
  });
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as MCPServer;
};

export const deleteMCPServer = async (toolgroup_id: string): Promise<void> => {
  const response = await fetch(MCP_SERVERS_API_ENDPOINT + toolgroup_id, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  return;
};

export const syncMCPServers = async (): Promise<MCPServer[]> => {
  const response = await fetch(MCP_SERVERS_API_ENDPOINT + 'sync', {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as MCPServer[];
};