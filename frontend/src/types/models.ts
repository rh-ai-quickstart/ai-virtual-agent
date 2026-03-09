export type ModelType = 'llm';

export interface Model {
  model_id: string; // Primary key - LlamaStack identifier
  provider_id: string | null;
  provider_model_id: string | null;
  model_type: ModelType;
  metadata: Record<string, unknown>;
  created_at?: string;
  is_shield?: boolean;
}

export interface ModelCreate {
  model_id: string;
  provider_id: string | null;
  provider_model_id: string | null;
  model_type: ModelType;
  metadata?: Record<string, unknown>;
}

export interface ModelUpdate {
  provider_id?: string | null;
  provider_model_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ModelProvider {
  provider_id: string;
  provider_type: string;
  api: string;
  config?: Record<string, unknown>;
}

export interface ProviderCreate {
  provider_id: string;
  provider_type: 'remote::vllm' | 'remote::ollama';
  config: Record<string, unknown>;
}

export interface VLLMConfig {
  base_url: string;
  api_token?: string;
  max_tokens?: number;
  tls_verify?: boolean;
}

export interface OllamaConfig {
  base_url: string;
}
