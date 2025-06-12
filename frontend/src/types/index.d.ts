export interface KnowledgeBase {
  vector_db_name: string; // Primary key - LlamaStack identifier
  name: string;
  version: string;
  embedding_model: string;
  provider_id?: string;
  is_external: boolean;
  source?: string;
  source_configuration?: Record<string, unknown>;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

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

// Keep Tool interface for backward compatibility (will be deprecated)
export type Tool = ToolGroup;

export interface ToolAssociationInfo {
  toolgroup_id: string;
}

export interface Model {
  model_name: string;
  provider_resource_id: string;
  model_type: string;
}

export interface EmbeddingModel {
  name: string;
  provider_resource_id: string;
  model_type: string;
}

export interface Provider {
  provider_id: string;
  provider_type: string;
  config: Record<string, unknown>;
  api: string;
}

export type KnowledgeBaseStatus = 'ready' | 'pending' | 'orphaned';

export interface KnowledgeBaseWithStatus extends KnowledgeBase {
  status: KnowledgeBaseStatus;
}

export interface LSKnowledgeBase {
  kb_name: string;
  provider_resource_id: string;
  provider_id: string;
  type: string;
  embedding_model: string;
}
