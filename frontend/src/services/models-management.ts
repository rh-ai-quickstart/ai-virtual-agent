import { MODELS_API_ENDPOINT, MODEL_PROVIDERS_API_ENDPOINT } from '@/config/api';
import { Model, ModelCreate, ModelUpdate, ModelProvider, ProviderCreate } from '@/types/models';
import { ErrorResponse } from '@/types';

export const fetchModels = async (): Promise<Model[]> => {
  const response = await fetch(MODELS_API_ENDPOINT, { credentials: 'include' });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as Model[];
};

export const createModel = async (newModel: ModelCreate): Promise<Model> => {
  const response = await fetch(MODELS_API_ENDPOINT, {
    credentials: 'include',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(newModel),
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to create model' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to create model');
  }
  const data: unknown = await response.json();
  return data as Model;
};

export const updateModel = async (model_id: string, modelUpdate: ModelUpdate): Promise<Model> => {
  const response = await fetch(MODELS_API_ENDPOINT + model_id, {
    credentials: 'include',
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(modelUpdate),
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to update model' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to update model');
  }
  const data: unknown = await response.json();
  return data as Model;
};

export const deleteModel = async (model_id: string): Promise<void> => {
  const response = await fetch(MODELS_API_ENDPOINT + model_id, {
    credentials: 'include',
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to delete model' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to delete model');
  }
  return;
};

export const fetchModelProviders = async (): Promise<ModelProvider[]> => {
  const response = await fetch(MODEL_PROVIDERS_API_ENDPOINT, { credentials: 'include' });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to fetch model providers' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to fetch model providers');
  }
  const data: unknown = await response.json();
  return data as ModelProvider[];
};

export const createProvider = async (newProvider: ProviderCreate): Promise<ModelProvider> => {
  const response = await fetch('/api/v1/models/providers/', {
    credentials: 'include',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(newProvider),
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to create provider' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to create provider');
  }
  const data: unknown = await response.json();
  return data as ModelProvider;
};
