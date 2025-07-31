export type ToolType = 'builtin' | 'mcp_server';

export interface ToolGroup {
  toolgroup_id: string; // Primary key - LlamaStack identifier
  name: string;
  description?: string;
  endpoint_url?: string;
  configuration?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export interface MCPServer {
  toolgroup_id: string; // Primary key - LlamaStack identifier
  name: string;
  description: string;
  endpoint_url: string;
  configuration: Record<string, unknown>;
  provider_id: string;
  created_at?: string;
}

export interface MCPServerCreate {
  toolgroup_id: string; // NOW REQUIRED!
  name: string;
  description: string;
  endpoint_url: string;
  configuration: Record<string, unknown>;
}

// Keep Tool interface for backward compatibility (will be deprecated)
export type Tool = ToolGroup;

export interface ToolAssociationInfo {
  toolgroup_id: string;
}
