import { useState, useCallback, useEffect } from 'react';
import { LlamaStackParser, extractSessionId } from '../adapters/llamaStackAdapter';
import { CHAT_API_ENDPOINT } from '../config/api';
import { fetchChatSession } from '@/services/chat-sessions';
import { ChatMessage, UseLlamaChatOptions, SimpleContentItem } from '@/types/chat';

// Re-export types for backward compatibility
export type { ChatMessage, UseLlamaChatOptions } from '@/types/chat';

// Interface for ReAct response structure
interface ReActResponse {
  thought?: string;
  answer?: string;
}

// Type guard to check if an object has ReAct properties
function isReActResponse(obj: unknown): obj is ReActResponse {
  return typeof obj === 'object' && obj !== null && 'thought' in obj;
}

// Function for processing streaming ReAct responses (when user types question)
export const processStreamingReActResponse = (content: string): string => {
  if (content.trim().startsWith('{')) {
    try {
      const jsonData: unknown = JSON.parse(content.trim());
      if (isReActResponse(jsonData) && jsonData.thought) {
        const thought = String(jsonData.thought);
        const answer = jsonData.answer ? String(jsonData.answer) : '';
        if (answer) {
          return `🤔 **Thinking:** ${thought}\n\n${answer}`;
        } else {
          return `🤔 **Thinking:** ${thought}`;
        }
      }
    } catch (e) {
      console.warn('Failed to parse streaming ReAct JSON:', content, e);
    }
  }
  return content;
};

// Function for processing stored ReAct responses (page refresh) - IDENTICAL to streaming
const processStoredReActResponse = (content: string): string => {
  if (content.trim().startsWith('{')) {
    try {
      const jsonData: unknown = JSON.parse(content.trim());
      if (isReActResponse(jsonData) && jsonData.thought) {
        const thought = String(jsonData.thought);
        const answer = jsonData.answer ? String(jsonData.answer) : '';
        if (answer) {
          return `🤔 **Thinking:** ${thought}\n\n${answer}`;
        } else {
          return `🤔 **Thinking:** ${thought}`;
        }
      }
    } catch (e) {
      console.warn('Failed to parse stored ReAct JSON:', content, e);
    }
  }
  return content;
};

/**
 * Simple chat hook that directly handles LlamaStack without the AI SDK overhead
 */
export function useChat(
  agentId: string,
  agentType: 'Regular' | 'ReAct' = 'Regular',
  options?: UseLlamaChatOptions
) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);

  const handleInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, value?: string | number) => {
      const newValue = value !== undefined ? String(value) : event.target.value;
      setInput(newValue);
    },
    []
  );
  interface SessionMessage {
    role: 'user' | 'assistant' | 'system';
    content: SimpleContentItem[];
  }
  const loadSession = useCallback(
    async (sessionId: string) => {
      try {
        setIsLoading(true);
        console.log(`Loading session ${sessionId} for agent ${agentId}`);
        const sessionDetail = await fetchChatSession(sessionId, agentId);
        if (!sessionDetail) {
          throw new Error(`Session ${sessionId} not found for agent ${agentId}`);
        }
        console.log('Session detail:', sessionDetail);
        // Set the session ID
        setSessionId(sessionId);

        // Convert messages to our format
        const convertedMessages: ChatMessage[] = sessionDetail.messages.map(
          (msg: SessionMessage, index: number) => {
            let processedContent = msg.content;
            let textContent = '';

            for (const item of msg.content) {
              if (item.type === 'text') {
                textContent += item.text || '';
              }
            }

            // Process assistant messages that might contain raw JSON
            if (msg.role === 'assistant') {
              processedContent = [{ type: 'text', text: processStoredReActResponse(textContent) }];
            }

            return {
              id: `${msg.role}-${sessionId}-${index}`,
              role: msg.role,
              content: processedContent,
              timestamp: new Date(),
            };
          }
        );

        setMessages(convertedMessages);
        console.log('Loaded messages:', convertedMessages);
        // Update agent if different
        if (sessionDetail.agent_id && sessionDetail.agent_id !== agentId) {
          console.warn(`Loaded session for different agent: ${sessionDetail.agent_id}`);
          // Optionally handle this case, e.g., notify user or reset state
        }
      } catch (error) {
        console.error('Error loading session:', error);
        options?.onError?.(error as Error);
      } finally {
        setIsLoading(false);
      }
    },
    [agentId, options]
  );

  const clearAttachedFiles = useCallback(() => {
    setAttachedFiles([]);
  }, []);

  const sendMessage = useCallback(
    async (content: SimpleContentItem[]) => {
      if (isLoading) return;

      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: content,
        timestamp: new Date(),
      };

      // Add user message immediately
      setMessages((prev) => [...prev, userMessage]);
      setInput('');
      setIsLoading(true);

      try {
        // Prepare request
        const requestBody = {
          virtualAssistantId: agentId,
          messages: [...messages, userMessage].map((msg) => ({
            role: msg.role,
            content: msg.content,
          })),
          stream: true,
          ...(sessionId ? { sessionId } : {}),
        };

        const response = await fetch(CHAT_API_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
          throw new Error(`API error: ${response.statusText}`);
        }

        if (!response.body) {
          throw new Error('No response body');
        }

        // Create assistant message
        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: [
            {
              text: '',
              type: 'text',
            },
          ],
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);

        // Process stream
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();

              if (data === '[DONE]') {
                // Stream finished
                setMessages((prev) => {
                  const updated = [...prev];
                  const lastMsg = updated[updated.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant') {
                    options?.onFinish?.(lastMsg);
                  }
                  return updated;
                });
                continue;
              }

              // Check for session ID
              const newSessionId = extractSessionId(data);
              if (newSessionId) {
                setSessionId(newSessionId);
                continue;
              }

              // Parse content
              const parsed = LlamaStackParser.parse(data, agentType);
              if (parsed) {
                setMessages((prev) => {
                  const updated = [...prev];
                  const lastMsg = updated[updated.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant') {
                    const c: SimpleContentItem[] = [...lastMsg.content];
                    if (c[0].type === 'text') {
                      // For regular agents, accumulate content (same as ReAct but without special handling)
                      if (agentType === 'Regular') {
                        c[0].text += parsed;
                        lastMsg.content = c;
                      } else if (parsed.includes('🤔 **Thinking:**')) {
                        // For ReAct agents, replace content for complete responses
                        c[0].text = parsed;
                        lastMsg.content = c;
                      } else {
                        // For ReAct agents, append for streaming responses
                        c[0].text += parsed;
                        lastMsg.content = c;
                      }
                    }
                  }
                  return updated;
                });
              }
            }
          }
        }
      } catch (error) {
        console.error('Chat error:', error);
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        options?.onError?.(new Error(errorMessage));

        // Remove the loading assistant message on error
        setMessages((prev) =>
          prev.filter((msg) => {
            return msg.role !== 'assistant' || msg.content.length > 0;
          })
        );
      } finally {
        setIsLoading(false);
      }
    },
    [agentId, messages, sessionId, isLoading, options, agentType]
  );

  const handleAttach = useCallback((data: File[]) => {
    setAttachedFiles((prev: File[]) => [...prev, ...data]);
  }, []);

  const append = useCallback(
    (message: { role: 'user' | 'assistant'; content: SimpleContentItem[] }) => {
      void sendMessage(message.content);
    },
    [sendMessage]
  );

  // Reset state when agentId changes
  useEffect(() => {
    setMessages([]);
    setInput('');
    setAttachedFiles([]);
    setIsLoading(false);
    setSessionId(null);
  }, [agentId]);

  return {
    messages,
    input,
    handleInputChange,
    handleAttach,
    append,
    isLoading,
    loadSession,
    sessionId,
    attachedFiles,
    clearAttachedFiles,
    setAttachedFiles,
  };
}
