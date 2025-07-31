import { useQuery } from '@tanstack/react-query';
import { ToolGroup } from '@/types';
import { fetchTools } from '@/services/tools';

export const useTools = () => {
  const toolsQuery = useQuery<ToolGroup[], Error>({
    queryKey: ['tools'],
    queryFn: fetchTools,
  });

  return {
    tools: toolsQuery.data,
    isLoading: toolsQuery.isLoading,
    error: toolsQuery.error,
  };
};
