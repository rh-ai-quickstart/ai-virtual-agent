import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AgentTemplate,
  TemplateInitializationRequest,
  TemplateInitializationResponse,
  getAvailableTemplates,
  getTemplateDetails,
  initializeAgentFromTemplate,
  initializeAllTemplates,
  initializeSuite,
  getSuitesByCategory,
  getSuiteDetails,
  getCategoriesInfo,
  initializeTemplate,
} from '@/services/agent-templates';

export const useAgentTemplates = () => {
  const queryClient = useQueryClient();

  // Query for available templates
  const templatesQuery = useQuery<string[], Error>({
    queryKey: ['agentTemplates'],
    queryFn: getAvailableTemplates,
  });

  // Query for suites by category
  const suitesByCategoryQuery = useQuery<Record<string, string[]>, Error>({
    queryKey: ['agentTemplates', 'suitesByCategory'],
    queryFn: getSuitesByCategory,
  });

  // Query for categories info
  const categoriesInfoQuery = useQuery<
    Record<string, { name: string; description: string; icon: string; suite_count: number }>,
    Error
  >({
    queryKey: ['agentTemplates', 'categoriesInfo'],
    queryFn: getCategoriesInfo,
  });

  // Hook for fetching template details
  const useTemplateDetails = (templateName: string) => {
    return useQuery<AgentTemplate, Error>({
      queryKey: ['agentTemplates', 'details', templateName],
      queryFn: () => getTemplateDetails(templateName),
      enabled: !!templateName,
    });
  };

  // Hook for fetching suite details
  const useSuiteDetails = (suiteId: string) => {
    return useQuery<
      {
        id: string;
        name: string;
        description: string;
        category: string;
        agent_count: number;
        agent_names: string[];
      },
      Error
    >({
      queryKey: ['agentTemplates', 'suite', suiteId],
      queryFn: () => getSuiteDetails(suiteId),
      enabled: !!suiteId,
    });
  };

  // Mutation for initializing agent from template
  const initializeAgentMutation = useMutation<
    TemplateInitializationResponse,
    Error,
    TemplateInitializationRequest
  >({
    mutationFn: initializeAgentFromTemplate,
    onSuccess: () => {
      // Invalidate agents queries to show new agent
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
    onError: (error) => {
      console.error('Failed to initialize agent from template:', error);
    },
  });

  // Mutation for initializing all templates
  const initializeAllTemplatesMutation = useMutation<TemplateInitializationResponse[], Error>({
    mutationFn: initializeAllTemplates,
    onSuccess: () => {
      // Invalidate agents queries to show new agents
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
    onError: (error) => {
      console.error('Failed to initialize all templates:', error);
    },
  });

  // Mutation for initializing a suite
  const initializeSuiteMutation = useMutation<TemplateInitializationResponse[], Error, string>({
    mutationFn: initializeSuite,
    onSuccess: () => {
      // Invalidate agents queries to show new agents
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
    onError: (error) => {
      console.error('Failed to initialize suite:', error);
    },
  });

  // Mutation for initializing template with persona
  const initializeTemplateMutation = useMutation<
    { agent: TemplateInitializationResponse; persona: string },
    Error,
    { templateName: string; customName?: string; customPrompt?: string }
  >({
    mutationFn: ({ templateName, customName, customPrompt }) =>
      initializeTemplate(templateName, customName, customPrompt),
    onSuccess: () => {
      // Invalidate agents queries to show new agent
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
    onError: (error) => {
      console.error('Failed to initialize template:', error);
    },
  });

  // Helper function to refresh templates data
  const refreshTemplates = () => {
    void queryClient.invalidateQueries({ queryKey: ['agentTemplates'] });
  };

  return {
    // Query data and states
    templates: templatesQuery.data,
    isLoading: templatesQuery.isLoading,
    error: templatesQuery.error,

    // Suites by category
    suitesByCategory: suitesByCategoryQuery.data,
    isLoadingSuites: suitesByCategoryQuery.isLoading,
    suitesError: suitesByCategoryQuery.error,

    // Categories info
    categoriesInfo: categoriesInfoQuery.data,
    isLoadingCategories: categoriesInfoQuery.isLoading,
    categoriesError: categoriesInfoQuery.error,

    // Hooks for specific template and suite details
    useTemplateDetails,
    useSuiteDetails,

    // Mutations
    initializeAgent: initializeAgentMutation.mutateAsync,
    initializeAllTemplates: initializeAllTemplatesMutation.mutateAsync,
    initializeSuite: initializeSuiteMutation.mutateAsync,
    initializeTemplate: (templateName: string, customName?: string, customPrompt?: string) =>
      initializeTemplateMutation.mutateAsync({ templateName, customName, customPrompt }),

    // Mutation states
    isInitializingAgent: initializeAgentMutation.isPending,
    isInitializingAll: initializeAllTemplatesMutation.isPending,
    isInitializingSuite: initializeSuiteMutation.isPending,
    isInitializingTemplate: initializeTemplateMutation.isPending,
    initializeError: initializeAgentMutation.error,
    initializeAllError: initializeAllTemplatesMutation.error,
    initializeSuiteError: initializeSuiteMutation.error,
    initializeTemplateError: initializeTemplateMutation.error,

    // Utilities
    refreshTemplates,
  };
};
