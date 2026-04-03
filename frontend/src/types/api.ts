export interface Model {
  model_name: string;
  provider_resource_id: string;
  model_type: string;
  display_name?: string;
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

export interface ErrorResponse {
  detail?: string;
}
