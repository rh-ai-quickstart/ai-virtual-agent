import { MCP_SERVERS_API_ENDPOINT } from '@/config/api';
import { MCPServer, MCPServerCreate, DiscoveredMCPServer, ErrorResponse } from '@/types';

export const fetchMCPServers = async (): Promise<MCPServer[]> => {
  const response = await fetch(MCP_SERVERS_API_ENDPOINT, { credentials: 'include' });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as MCPServer[];
};

export const createMCPServer = async (newServer: MCPServerCreate): Promise<MCPServer> => {
  const response = await fetch(MCP_SERVERS_API_ENDPOINT, {
    credentials: 'include',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(newServer),
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as MCPServer;
};

export const updateMCPServer = async (
  toolgroup_id: string,
  serverUpdate: MCPServerCreate
): Promise<MCPServer> => {
  const response = await fetch(MCP_SERVERS_API_ENDPOINT + toolgroup_id, {
    credentials: 'include',
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(serverUpdate),
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as MCPServer;
};

export const deleteMCPServer = async (toolgroup_id: string): Promise<void> => {
  const response = await fetch(MCP_SERVERS_API_ENDPOINT + toolgroup_id, {
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

export const syncMCPServers = async (): Promise<MCPServer[]> => {
  const response = await fetch(MCP_SERVERS_API_ENDPOINT + 'sync', {
    credentials: 'include',
    method: 'POST',
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as MCPServer[];
};

export const discoverMCPServers = async (): Promise<DiscoveredMCPServer[]> => {
  const response = await fetch(MCP_SERVERS_API_ENDPOINT + 'discover', { credentials: 'include' });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to discover MCP servers' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to discover MCP servers');
  }
  const data: unknown = await response.json();
  return data as DiscoveredMCPServer[];
};
