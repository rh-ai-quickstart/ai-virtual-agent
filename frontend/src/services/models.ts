import {
  EMBEDDING_MODELS_API_ENDPOINT,
  LLMS_API_ENDPOINT,
  MODELS_REGISTER_API_ENDPOINT,
  PROVIDER_MODELS_API_ENDPOINT,
  PROVIDERS_API_ENDPOINT,
} from '@/config/api';
import { Model, Provider } from '@/types';

export const fetchModels = async (): Promise<Model[]> => {
  const response = await fetch(LLMS_API_ENDPOINT);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as Model[];
};

export const fetchEmbeddingModels = async (): Promise<Model[]> => {
  const response = await fetch(EMBEDDING_MODELS_API_ENDPOINT);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as Model[];
};

export const fetchProviders = async (): Promise<Provider[]> => {
  const response = await fetch(PROVIDERS_API_ENDPOINT);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as Provider[];
};

export interface ProviderConfig {
  provider_id: string;
  provider_type: string;
  config: Record<string, unknown>;
}

export interface RegisterModelRequest {
  provider: ProviderConfig;
  model_id: string;
  metadata?: Record<string, unknown>;
}

export const fetchProviderModels = async (providerUrl: string): Promise<string[]> => {
  const url = new URL(PROVIDER_MODELS_API_ENDPOINT, window.location.origin);
  url.searchParams.append('provider_url', providerUrl);

  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error('Failed to fetch models from provider');
  }
  const data: unknown = await response.json();
  return data as string[];
};

export const registerModel = async (modelData: RegisterModelRequest) => {
  const response = await fetch(MODELS_REGISTER_API_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(modelData),
  });
  if (!response.ok) {
    const error = (await response.json()) as { detail?: string };
    throw new Error(error.detail ?? 'Failed to register model');
  }
  return (await response.json()) as Model;
};
