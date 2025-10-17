import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Model, Provider } from '@/types';
import {
  fetchModels,
  fetchEmbeddingModels,
  fetchProviders,
  registerModel,
  RegisterModelRequest,
} from '@/services/models';

export const useModels = () => {
  const queryClient = useQueryClient();

  // Query for LLM models
  const modelsQuery = useQuery<Model[], Error>({
    queryKey: ['models'],
    queryFn: fetchModels,
  });

  // Query for embedding models
  const embeddingModelsQuery = useQuery<Model[], Error>({
    queryKey: ['embeddingModels'],
    queryFn: fetchEmbeddingModels,
  });

  // Query for providers
  const providersQuery = useQuery<Provider[], Error>({
    queryKey: ['providers'],
    queryFn: fetchProviders,
  });

  // Mutation for registering a new model
  const registerModelMutation = useMutation<Model, Error, RegisterModelRequest>({
    mutationFn: registerModel,
    onSuccess: () => {
      // Invalidate and refetch models after successful registration
      void queryClient.invalidateQueries({ queryKey: ['models'] });
      void queryClient.invalidateQueries({ queryKey: ['embeddingModels'] });
    },
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

    // Register model mutation
    registerModel: registerModelMutation.mutate,
    isRegisteringModel: registerModelMutation.isPending,
    registerModelError: registerModelMutation.error,

    // Overall loading state
    isLoading: modelsQuery.isLoading || embeddingModelsQuery.isLoading || providersQuery.isLoading,
    hasError: !!(modelsQuery.error || embeddingModelsQuery.error || providersQuery.error),
  };
};
