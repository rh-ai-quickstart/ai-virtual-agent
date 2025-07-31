import { KnowledgeBaseWithStatus, KnowledgeBaseStatus } from '@/types';

interface LlamaStackKnowledgeBase {
  kb_name: string;
  provider_resource_id: string;
  provider_id: string;
  type: string;
  embedding_model: string;
}

/**
 * Determines the status of a knowledge base by comparing DB and LlamaStack states.
 * If a knowledge base was found in our db, return its pipeline status.
 */
function determineStatus(
  dbKb: KnowledgeBaseWithStatus | undefined,
  llamaStackKb: LlamaStackKnowledgeBase | undefined
): KnowledgeBaseStatus {
  if (dbKb) {
    return dbKb.status;
  } else if (llamaStackKb) {
    return 'orphaned';
  }

  return 'unknown';
}

/**
 * Simple matching by knowledge base name only
 */
function findMatchingKnowledgeBase(
  dbKb: KnowledgeBaseWithStatus | undefined,
  llamaStackKb: LlamaStackKnowledgeBase | undefined
): {
  dbMatch: KnowledgeBaseWithStatus | undefined;
  llamaStackMatch: LlamaStackKnowledgeBase | undefined;
} {
  return { dbMatch: dbKb, llamaStackMatch: llamaStackKb };
}

/**
 * Merges knowledge bases from database and LlamaStack, determining status for each
 */
export function mergeKnowledgeBasesWithStatus(
  dbKnowledgeBases: KnowledgeBaseWithStatus[],
  llamaStackKnowledgeBases: LlamaStackKnowledgeBase[]
): KnowledgeBaseWithStatus[] {
  const result: KnowledgeBaseWithStatus[] = [];
  const processedLlamaStackKbs = new Set<string>();

  // Create map for efficient lookup by primary identifier (kb_name)
  const llamaStackKbMap = new Map(llamaStackKnowledgeBases.map((kb) => [kb.kb_name, kb]));

  // Process all DB knowledge bases first
  for (const dbKb of dbKnowledgeBases) {
    const llamaStackKb = llamaStackKbMap.get(dbKb.vector_db_name);
    const { dbMatch, llamaStackMatch } = findMatchingKnowledgeBase(dbKb, llamaStackKb);
    const status = determineStatus(dbMatch, llamaStackMatch);

    result.push({
      ...dbKb,
      status,
    });

    if (llamaStackMatch) {
      processedLlamaStackKbs.add(llamaStackMatch.kb_name);
    }
  }

  // Process remaining LlamaStack knowledge bases that don't have DB matches
  for (const llamaStackKb of llamaStackKnowledgeBases) {
    if (!processedLlamaStackKbs.has(llamaStackKb.kb_name)) {
      const { dbMatch, llamaStackMatch } = findMatchingKnowledgeBase(undefined, llamaStackKb);
      const status = determineStatus(dbMatch, llamaStackMatch);

      // Create a knowledge base object from LlamaStack data for orphaned items
      result.push({
        vector_db_name: llamaStackKb.kb_name,
        name: llamaStackKb.kb_name,
        version: 'unknown',
        embedding_model: llamaStackKb.embedding_model,
        provider_id: llamaStackKb.provider_id,
        is_external: true,
        source: 'unknown',
        source_configuration: {
          provider_resource_id: llamaStackKb.provider_resource_id,
          type: llamaStackKb.type,
        },
        status,
      });
    }
  }

  return result;
}

/**
 * Gets the status color for display
 */
export function getStatusColor(status: KnowledgeBaseStatus): 'green' | 'orange' | 'red' {
  switch (status) {
    case 'succeeded':
      return 'green';
    case 'running':
      return 'orange';
    case 'failed':
    case 'orphaned':
    case 'unknown':
      return 'red';
    default:
      return 'orange';
  }
}

/**
 * Gets the status label for display
 */
export function getStatusLabel(status: KnowledgeBaseStatus): string {
  switch (status) {
    case 'succeeded':
      return 'Succeeded';
    case 'running':
      return 'Running';
    case 'failed':
      return 'Failed';
    case 'orphaned':
      return 'Orphaned';
    default:
      return 'Unknown';
  }
}
