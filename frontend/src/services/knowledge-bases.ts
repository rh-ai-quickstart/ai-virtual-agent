import {
  KNOWLEDGE_BASES_API_ENDPOINT,
  LLAMA_STACK_KNOWLEDGE_BASES_API_ENDPOINT,
} from '@/config/api';
import { KnowledgeBase, KnowledgeBaseWithStatus, LSKnowledgeBase } from '@/types';
import { mergeKnowledgeBasesWithStatus } from '@/utils/knowledge-base-status';

export const fetchKnowledgeBases = async (): Promise<KnowledgeBase[]> => {
  const response = await fetch(KNOWLEDGE_BASES_API_ENDPOINT);
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as KnowledgeBase[];
};

export const createKnowledgeBase = async (
  newKnowledgeBase: Omit<KnowledgeBase, 'created_at' | 'updated_at'>
): Promise<KnowledgeBase> => {
  const response = await fetch(KNOWLEDGE_BASES_API_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(newKnowledgeBase),
  });
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  const data: unknown = await response.json();
  return data as KnowledgeBase;
};

export const deleteKnowledgeBase = async (vectorDbName: string): Promise<void> => {
  const response = await fetch(KNOWLEDGE_BASES_API_ENDPOINT + vectorDbName, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  return;
};

export const fetchKnowledgeBasesWithStatus = async (): Promise<KnowledgeBaseWithStatus[]> => {
  // Fetch both DB and LlamaStack knowledge bases in parallel
  const [dbKnowledgeBases, llamaStackKnowledgeBases] = await Promise.all([
    fetchKnowledgeBases(),
    fetchLlamaStackKnowledgeBases(),
  ]);

  // Merge and determine status for each
  return mergeKnowledgeBasesWithStatus(dbKnowledgeBases, llamaStackKnowledgeBases);
};

export async function fetchLlamaStackKnowledgeBases() {
  const response = await fetch(LLAMA_STACK_KNOWLEDGE_BASES_API_ENDPOINT);
  if (!response.ok) {
    throw new Error('Failed to fetch LlamaStack knowledge bases');
  }
  const data: unknown = await response.json();
  return data as Array<LSKnowledgeBase>;
}
