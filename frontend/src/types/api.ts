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

export interface LlamaStackResponse {
  type: string;
  content: string;
  sessionId?: string;
  tool?: {
    name: string;
    params?: Record<string, unknown>;
  };
  thought?: string;
  answer?: string;
}

export type LlamaStackParser = {
  parse(text: string, agentType?: 'Regular' | 'ReAct'): string | null;
};
