import { useQuery } from '@tanstack/react-query';
import { Model, EmbeddingModel, Provider } from '@/types';
import { fetchModels, fetchEmbeddingModels, fetchProviders } from '@/services/models';

export const useModels = () => {
  // Query for LLM models
  const modelsQuery = useQuery<Model[], Error>({
    queryKey: ['models'],
    queryFn: fetchModels,
  });

  // Query for embedding models
  const embeddingModelsQuery = useQuery<EmbeddingModel[], Error>({
    queryKey: ['embeddingModels'],
    queryFn: fetchEmbeddingModels,
  });

  // Query for providers
  const providersQuery = useQuery<Provider[], Error>({
    queryKey: ['providers'],
    queryFn: fetchProviders,
  });

  return {
    // LLM models
    models: modelsQuery.data,
    isLoadingModels: modelsQuery.isLoading,
    modelsError: modelsQuery.error,

    // Embedding models
    embeddingModels: embeddingModelsQuery.data,
    isLoadingEmbeddingModels: embeddingModelsQuery.isLoading,
    embeddingModelsError: embeddingModelsQuery.error,

    // Providers
    providers: providersQuery.data,
    isLoadingProviders: providersQuery.isLoading,
    providersError: providersQuery.error,

    // Overall loading state
    isLoading: modelsQuery.isLoading || embeddingModelsQuery.isLoading || providersQuery.isLoading,
    hasError: !!(modelsQuery.error || embeddingModelsQuery.error || providersQuery.error),
  };
};
