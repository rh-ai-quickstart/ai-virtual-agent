import { processStreamingReActResponse } from '../hooks/useChat';

// Define our custom parser type
type LlamaStackParser = {
  parse(text: string, agentType?: 'Regular' | 'ReAct'): string | null;
};

interface LlamaStackResponse {
  type: string;
  content: string;
  sessionId?: string;
  tool?: {
    name: string;
    params?: Record<string, unknown>;
  };
  thought?: string;
  answer?: string;
}

/**
 * LlamaStackParser - Transforms the Llama Stack API response format into
 * displayable content for the chat interface.
 *
 * Handles different response types (text, tool, reasoning, error) and properly
 * processes the session ID from the stream.
 */
export const LlamaStackParser: LlamaStackParser = {
  parse(line: string, agentType: 'Regular' | 'ReAct' = 'Regular'): string | null {
    // Skip [DONE] events (empty lines)
    if (!line || line === '[DONE]') {
      return null;
    }

    // Try to parse the response
    try {
      const json = JSON.parse(line) as LlamaStackResponse;
      
      // Debug: Log what we're receiving
      console.log('🔧 ADAPTER: Received type:', json.type, 'content length:', json.content?.length);

      // Store session ID if present (to be handled by the adapter)
      if (json.type === 'session' && json.sessionId) {
        // This will be handled separately by the adapter
        return null;
      }

      // Handle text content which should be shown to the user
      if (json.type === 'text' && json.content) {
        console.log('🔧 ADAPTER: Processing text content for agentType:', agentType);
        if (agentType === 'ReAct') {
          const result = processStreamingReActResponse(json.content);
          console.log('🔧 ADAPTER: ReAct processing result:', result);
          return result;
        }
        // For regular agents, use the same logic as refresh page (no special processing)
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

      // Handle react_unified type from our backend
      if (json.type === 'react_unified' && agentType === 'ReAct') {
        console.log('🔧 ADAPTER: Processing react_unified response');
        // The react_unified type contains thought and answer directly
        if (json.thought) {
          const thought = String(json.thought);
          const answer = json.answer ? String(json.answer) : "";
          if (answer) {
            return `🤔 **Thinking:** ${thought}\n\n${answer}`;
          } else {
            return `🤔 **Thinking:** ${thought}`;
          }
        }
      }

      // Handle errors
      if (json.type === 'error') {
        console.error('LlamaStack API error:', json.content);
        return `[Error: ${json.content}]`;
      }

      console.log('🔧 ADAPTER: No handler for type:', json.type);
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
    const json = JSON.parse(line) as LlamaStackResponse;
    if (json.type === 'session' && json.sessionId) {
      return json.sessionId;
    }
  } catch {
    // Ignore parse errors for non-session messages
  }
  return null;
};
