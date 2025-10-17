export interface Model {
  model_id: string;
  model_type: string;
  provider_id: string;
  provider_type: string;
  provider_config: Record<string, unknown>;
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
  parse(text: string): string | null;
};
