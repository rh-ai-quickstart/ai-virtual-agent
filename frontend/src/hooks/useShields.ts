import { useQuery } from '@tanstack/react-query';
import { Shield } from '@/types/auth';
import { fetchShields } from '@/services/shields';

export const useShields = () => {
  const shieldsQuery = useQuery<Shield[], Error>({
    queryKey: ['shields'],
    queryFn: fetchShields,
  });

  return {
    shields: shieldsQuery.data,
    isLoading: shieldsQuery.isLoading,
    error: shieldsQuery.error,
  };
};
