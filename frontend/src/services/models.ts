import {
  EMBEDDING_MODELS_API_ENDPOINT,
  LLMS_API_ENDPOINT,
  PROVIDERS_API_ENDPOINT,
} from '@/config/api';
import { EmbeddingModel, Model, Provider } from '@/types';

export const fetchModels = async (): Promise<Model[]> => {
  const response = await fetch(LLMS_API_ENDPOINT);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as Model[];
};

export const fetchEmbeddingModels = async (): Promise<EmbeddingModel[]> => {
  const response = await fetch(EMBEDDING_MODELS_API_ENDPOINT);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as EmbeddingModel[];
};

export const fetchProviders = async (): Promise<Provider[]> => {
  const response = await fetch(PROVIDERS_API_ENDPOINT);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as Provider[];
};
