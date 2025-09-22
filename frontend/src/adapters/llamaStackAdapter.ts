import type { LlamaStackParser as LlamaStackParserType, LlamaStackResponse } from '@/types/api';

/**
 * LlamaStackParser - Transforms the Llama Stack API response format into
 * displayable content for the chat interface.
 *
 * Handles different response types (text, tool, reasoning, error) and properly
 * processes the session ID from the stream.
 */
export const LlamaStackParser: LlamaStackParserType = {
  parse(line: string): string | null {
    // Skip [DONE] events (empty lines)
    if (!line || line === '[DONE]') {
      return null;
    }

    // Try to parse the response
    try {
      const json = JSON.parse(line) as LlamaStackResponse;

      // Store session ID if present (to be handled by the adapter)
      if (json.type === 'session' && json.sessionId) {
        // This will be handled separately by the adapter
        return null;
      }

      // Handle done events from the backend
      if (json.type === 'done') {
        return null;
      }

      // Handle text content which should be shown to the user
      if ((json.type === 'text' || json.type === 'content') && json.content) {
        return json.content;
      }

      // Handle tool use - convert to visual indication that tool is being used
      if (json.type === 'tool' && json.content) {
        return `[Tool: ${json.tool?.name || 'unknown'}] ${json.content}\n`;
      }

      // Handle reasoning (thought process)
      if (json.type === 'reasoning' && json.content) {
        return `[Thinking: ${json.content}]\n`;
      }

      // Handle errors
      if (json.type === 'error') {
        console.error('LlamaStack API error:', json.content);
        return `[Error: ${json.content}]`;
      }

      return null;
    } catch (e) {
      // If we can't parse as JSON, return the raw line
      console.warn('Failed to parse LlamaStack response:', e);
      return null;
    }
  },
};

/**
 * Extracts session ID from the Llama Stack API response
 * This is used by the adapter to maintain conversation context
 */
export const extractSessionId = (line: string): string | null => {
  try {
    const json = JSON.parse(line) as LlamaStackResponse & { session_id?: string };
    if (json.type === 'session' && json.sessionId) {
      return json.sessionId;
    }
    // Also check for session_id in done events
    if (json.type === 'done' && json.session_id) {
      return json.session_id;
    }
  } catch {
    // Ignore parse errors for non-session messages
  }
  return null;
};
