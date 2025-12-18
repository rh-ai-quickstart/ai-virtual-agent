import { LLAMA_STACK_TOOLS_API_ENDPOINT } from '@/config/api';
import { ToolGroup, ErrorResponse } from '@/types';

export const fetchTools = async (): Promise<ToolGroup[]> => {
  const response = await fetch(LLAMA_STACK_TOOLS_API_ENDPOINT, { credentials: 'include' });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as ToolGroup[];
};
