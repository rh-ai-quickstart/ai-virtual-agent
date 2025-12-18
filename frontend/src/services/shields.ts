import { SHIELDS_API_ENDPOINT } from '@/config/api';
import { Shield } from '@/types/auth';
import { ErrorResponse } from '@/types';

// Re-export types for backward compatibility
export type { Shield } from '@/types/auth';

interface BackendShield {
  identifier: string;
  provider_id: string;
  name: string;
  type: string;
}

export const fetchShields = async (): Promise<Shield[]> => {
  const response = await fetch(SHIELDS_API_ENDPOINT, { credentials: 'include' });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: BackendShield[] = (await response.json()) as BackendShield[];

  // Map backend response to frontend expected structure
  // Use shield identifier (e.g., "meta-llama/Llama-Guard-3-1B") for guardrails
  return data.map((shield) => ({
    identifier: shield.identifier,
    name: shield.name,
  }));
};
