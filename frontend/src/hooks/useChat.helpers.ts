import {
  ChatMessage,
  ErrorEvent,
  NodeCompletedEvent,
  NodeStartedEvent,
  ReasoningEvent,
  ResponseEvent,
  SimpleContentItem,
  ToolCallEvent,
} from '@/types/chat';

/**
 * Helper functions for processing simplified streaming events from backend
 */

interface ChunkHandler<T = unknown> {
  (messages: ChatMessage[], event: T): ChatMessage[];
}

/**
 * Handle reasoning events (in_progress and completed)
 */
export const handleReasoning: ChunkHandler<ReasoningEvent> = (messages, event) => {
  const lastMsg = messages[messages.length - 1];
  if (!lastMsg || lastMsg.role !== 'assistant') return messages;

  const newContent = [...lastMsg.content];
  const reasoningIndex = newContent.findIndex(
    (item) => item.type === 'reasoning' && item.id === event.id
  );

  if (reasoningIndex >= 0) {
    // Update existing reasoning item
    newContent[reasoningIndex] = {
      type: 'reasoning' as const,
      text: event.text,
      id: event.id,
      isComplete: event.status === 'completed',
    };
  } else {
    // Add new reasoning item
    newContent.push({
      type: 'reasoning' as const,
      text: event.text,
      id: event.id,
      isComplete: event.status === 'completed',
    });
  }

  const updated = [...messages];
  updated[updated.length - 1] = {
    ...lastMsg,
    content: newContent,
    timestamp: new Date(),
  };
  return updated;
};

/**
 * Handle tool call events (in_progress, completed, failed)
 */
export const handleToolCall: ChunkHandler<ToolCallEvent> = (messages, event) => {
  const lastMsg = messages[messages.length - 1];
  if (!lastMsg || lastMsg.role !== 'assistant') return messages;

  const newContent = [...lastMsg.content];
  const toolCallIndex = newContent.findIndex(
    (item) => item.type === 'tool_call' && item.id === event.id
  );

  if (toolCallIndex >= 0) {
    // Update existing tool call
    newContent[toolCallIndex] = {
      type: 'tool_call' as const,
      name: event.name,
      server_label: event.server_label,
      arguments: event.arguments,
      output: event.output,
      error: event.error,
      status: event.status,
      id: event.id,
    };
  } else {
    // Add new tool call
    newContent.push({
      type: 'tool_call' as const,
      name: event.name,
      server_label: event.server_label,
      arguments: event.arguments,
      output: event.output,
      error: event.error,
      status: event.status,
      id: event.id,
    });
  }

  const updated = [...messages];
  updated[updated.length - 1] = {
    ...lastMsg,
    content: newContent,
    timestamp: new Date(),
  };
  return updated;
};

/**
 * Handle response events (in_progress and completed)
 * Accumulates deltas from the backend into full text
 */
export const handleResponse: ChunkHandler<ResponseEvent> = (messages, event) => {
  const lastMsg = messages[messages.length - 1];
  if (!lastMsg || lastMsg.role !== 'assistant') return messages;

  const newContent = [...lastMsg.content];
  const responseIndex = newContent.findIndex(
    (item) => item.type === 'output_text' && item.id === event.id
  );

  if (responseIndex >= 0) {
    // Accumulate delta to existing response text
    const existingItem = newContent[responseIndex];
    if (existingItem.type === 'output_text') {
      newContent[responseIndex] = {
        type: 'output_text' as const,
        text: existingItem.text + event.delta,
        id: event.id,
      };
    }
  } else {
    // Add new response text with first delta
    newContent.push({
      type: 'output_text' as const,
      text: event.delta,
      id: event.id,
    });
  }

  const updated = [...messages];
  updated[updated.length - 1] = {
    ...lastMsg,
    content: newContent,
    timestamp: new Date(),
  };
  return updated;
};

/**
 * Handle error events
 */
export const handleError: ChunkHandler<ErrorEvent> = (messages, event) => {
  const lastMsg = messages[messages.length - 1];
  if (!lastMsg || lastMsg.role !== 'assistant') return messages;

  // Append error to existing content (don't replace reasoning/tool calls)
  const newContent: SimpleContentItem[] = [
    ...lastMsg.content,
    {
      type: 'output_text',
      text: `⚠️ ${event.message}`,
    },
  ];

  const updated = [...messages];
  updated[updated.length - 1] = {
    ...lastMsg,
    content: newContent,
    timestamp: new Date(),
  };
  return updated;
};

/**
 * Derive a human-readable label from a node/task ID.
 * e.g. "places_list_task" -> "Places List", "hotel_research_task" -> "Hotel Research"
 */
export function nodeIdToLabel(nodeId: string): string {
  return nodeId
    .replace(/_task$/, '')
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Handle node_started events from graph/crew runners.
 * Upserts a graph_node content item with status 'running'.
 */
export const handleNodeStarted: ChunkHandler<NodeStartedEvent> = (messages, event) => {
  const lastMsg = messages[messages.length - 1];
  if (!lastMsg || lastMsg.role !== 'assistant') return messages;

  const newContent = [...lastMsg.content];
  const nodeIndex = newContent.findIndex(
    (item) => item.type === 'graph_node' && item.node_id === event.node
  );

  if (nodeIndex >= 0) {
    newContent[nodeIndex] = {
      type: 'graph_node' as const,
      node_id: event.node,
      label: nodeIdToLabel(event.node),
      status: 'running',
    };
  } else {
    newContent.push({
      type: 'graph_node' as const,
      node_id: event.node,
      label: nodeIdToLabel(event.node),
      status: 'running',
    });
  }

  const updated = [...messages];
  updated[updated.length - 1] = {
    ...lastMsg,
    content: newContent,
    timestamp: new Date(),
  };
  return updated;
};

/**
 * Handle node_completed events from graph/crew runners.
 * Updates the matching graph_node content item to status 'completed'.
 */
export const handleNodeCompleted: ChunkHandler<NodeCompletedEvent> = (messages, event) => {
  const lastMsg = messages[messages.length - 1];
  if (!lastMsg || lastMsg.role !== 'assistant') return messages;

  const newContent = [...lastMsg.content];
  const nodeIndex = newContent.findIndex(
    (item) => item.type === 'graph_node' && item.node_id === event.node
  );

  if (nodeIndex >= 0) {
    const existing = newContent[nodeIndex];
    if (existing.type === 'graph_node') {
      newContent[nodeIndex] = {
        ...existing,
        status: 'completed',
      };
    }
  }

  const updated = [...messages];
  updated[updated.length - 1] = {
    ...lastMsg,
    content: newContent,
    timestamp: new Date(),
  };
  return updated;
};
