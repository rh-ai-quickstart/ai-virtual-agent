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

export type KnowledgeBaseStatus = 'succeeded' | 'running' | 'failed' | 'unknown' | 'orphaned';

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
