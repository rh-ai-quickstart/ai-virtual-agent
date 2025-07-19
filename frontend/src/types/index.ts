// Template types
export type {
  TemplateSuite,
  TemplateDeployRequest,
  TemplateDeployResponse,
  TemplateCategory,
  TemplateDeployment,
  TemplatePersona,
  AgentConfig,
  ToolAssociationInfo,
} from './templates';

// Agent types
export interface Agent {
  id: string;
  name: string;
  model_name: string;
  prompt: string;
  tools: Array<{ toolgroup_id: string }>;
  knowledge_base_ids: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
  metadata?: {
    template_id?: string;
    template_name?: string;
    persona?: string;
    deployed_from_template?: boolean;
    deployment_timestamp?: string;
  };
}

// Model types
export interface Model {
  id: string;
  name: string;
  model_name: string;
  provider: string;
  context_length: number;
  max_tokens: number;
  temperature: number;
  repetition_penalty: number;
  top_p: number;
  max_infer_iters: number;
  input_shields: string[];
  output_shields: string[];
  created_at: string;
  updated_at: string;
}

// Tool types
export interface ToolGroup {
  id: string;
  name: string;
  description: string;
  toolgroup_id: string;
  tools: Tool[];
}

export interface Tool {
  id: string;
  name: string;
  description: string;
  toolgroup_id: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

// Knowledge Base types
export interface KnowledgeBase {
  id: string;
  name: string;
  description: string;
  embedding_model: string;
  provider: string;
  status: KnowledgeBaseStatus;
  created_by: string;
  created_at: string;
  updated_at: string;
  version?: string;
  provider_id?: string;
  vector_db_name?: string;
  is_external?: boolean;
  source?: string;
  source_configuration?: Record<string, any>;
}

export interface KnowledgeBaseWithStatus extends KnowledgeBase {
  status: KnowledgeBaseStatus;
  vector_db_name?: string;
}

export interface LSKnowledgeBase {
  id: string;
  name: string;
  description: string;
  embedding_model: string;
  provider: string;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  kb_name: string;
  provider_resource_id: string;
  provider_id: string;
  type: string;
}

export type KnowledgeBaseStatus = 'idle' | 'processing' | 'ready' | 'error' | 'succeeded' | 'running' | 'failed' | 'orphaned' | 'unknown';

// Embedding Model types
export interface EmbeddingModel {
  id: string;
  name: string;
  provider: string;
  dimensions: number;
  max_tokens: number;
  created_at: string;
  updated_at: string;
}

// Provider types
export interface Provider {
  provider_id: string;
  provider_type: string;
  api: string;
}

export type ProviderType = 'openai' | 'anthropic' | 'meta' | 'google' | 'local'; 