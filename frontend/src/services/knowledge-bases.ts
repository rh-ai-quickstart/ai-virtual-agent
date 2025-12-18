import { KNOWLEDGE_BASES_API_ENDPOINT } from '@/config/api';
import { KnowledgeBase, KnowledgeBaseWithStatus, ErrorResponse } from '@/types';

export const fetchKnowledgeBasesWithStatus = async (): Promise<KnowledgeBaseWithStatus[]> => {
  const response = await fetch(KNOWLEDGE_BASES_API_ENDPOINT, { credentials: 'include' });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as KnowledgeBaseWithStatus[];
};

export const createKnowledgeBase = async (
  newKnowledgeBase: Omit<KnowledgeBase, 'created_at' | 'updated_at'>
): Promise<KnowledgeBase> => {
  const response = await fetch(KNOWLEDGE_BASES_API_ENDPOINT, {
    credentials: 'include',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(newKnowledgeBase),
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as KnowledgeBase;
};

export const deleteKnowledgeBase = async (vectorStoreName: string): Promise<void> => {
  const response = await fetch(KNOWLEDGE_BASES_API_ENDPOINT + vectorStoreName, {
    credentials: 'include',
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Network response was not ok' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Network response was not ok');
  }
};
