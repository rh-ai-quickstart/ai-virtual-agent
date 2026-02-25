import { useState, useCallback, useEffect, useRef } from 'react';
import { CHAT_API_ENDPOINT } from '../config/api';
import { fetchChatSession, createChatSession } from '@/services/chat-sessions';
import { ChatMessage, UseLlamaChatOptions, SimpleContentItem, StreamEvent } from '@/types/chat';
import {
  handleReasoning,
  handleToolCall,
  handleResponse,
  handleError,
  handleNodeStarted,
  handleNodeCompleted,
} from './useChat.helpers';

// Re-export types for backward compatibility
export type { ChatMessage, UseLlamaChatOptions } from '@/types/chat';

/**
 * Simple chat hook that directly handles LlamaStack without the AI SDK overhead
 */
export function useChat(agentId: string, options?: UseLlamaChatOptions) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [attachedFiles, setAttachedFiles] = useState<File[]>([]);

  // Use a ref to track the current session ID for streaming responses
  const currentSessionIdRef = useRef<string | null>(sessionId);

  // Batching mechanism to reduce re-renders during streaming
  const pendingUpdatesRef = useRef<((prev: ChatMessage[]) => ChatMessage[])[]>([]);
  const rafIdRef = useRef<number | null>(null);

  // Use ref to store the scheduleUpdate function for stable reference
  const scheduleUpdateRef = useRef((updateFn: (prev: ChatMessage[]) => ChatMessage[]) => {
    pendingUpdatesRef.current.push(updateFn);

    if (rafIdRef.current === null) {
      rafIdRef.current = requestAnimationFrame(() => {
        const updates = pendingUpdatesRef.current;
        pendingUpdatesRef.current = [];
        rafIdRef.current = null;

        // Apply all pending updates in sequence
        setMessages((prev) => {
          let current = prev;
          for (const update of updates) {
            current = update(current);
          }
          return current;
        });
      });
    }
  });

  // Expose a stable function reference
  const scheduleUpdate = scheduleUpdateRef.current;

  // Use ref to store the flushPendingUpdates function for stable reference
  const flushPendingUpdatesRef = useRef(() => {
    if (rafIdRef.current !== null) {
      cancelAnimationFrame(rafIdRef.current);
      rafIdRef.current = null;

      // Apply all pending updates immediately
      const updates = pendingUpdatesRef.current;
      pendingUpdatesRef.current = [];

      if (updates.length > 0) {
        setMessages((prev) => {
          let current = prev;
          for (const update of updates) {
            current = update(current);
          }
          return current;
        });
      }
    }
  });

  // Expose a stable function reference
  const flushPendingUpdates = flushPendingUpdatesRef.current;

  // Update the ref whenever sessionId changes
  useEffect(() => {
    currentSessionIdRef.current = sessionId;
  }, [sessionId]);
  const handleInputChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, value?: string | number) => {
      const newValue = value !== undefined ? String(value) : event.target.value;
      setInput(newValue);
    },
    []
  );
  const loadSession = useCallback(
    async (sessionId: string) => {
      try {
        // Set the session ID immediately to prevent race conditions
        setSessionId(sessionId);

        setIsLoading(true);

        // Fetch session with messages from LlamaStack Conversations API
        const sessionDetail = await fetchChatSession(sessionId, agentId, true);
        if (!sessionDetail) {
          throw new Error(`Session ${sessionId} not found for agent ${agentId}`);
        }

        // Convert messages - parse timestamp string to Date
        const convertedMessages: ChatMessage[] = sessionDetail.messages.map((msg) => ({
          ...msg,
          timestamp: new Date(msg.timestamp as unknown as string),
        }));

        setMessages(convertedMessages);

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

      // Create assistant message immediately to show loading state
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: [],
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      try {
        // Create session if it doesn't exist
        let currentSessionId = sessionId;
        if (!currentSessionId) {
          const newSession = await createChatSession(agentId);
          currentSessionId = newSession.id;
          setSessionId(currentSessionId);
        }

        // Prepare request - send the new user message
        const requestBody = {
          virtualAgentId: agentId,
          message: {
            role: userMessage.role,
            content: userMessage.content,
          },
          stream: true,
          sessionId: currentSessionId,
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
                setIsLoading(false);
                continue;
              }

              try {
                const chunk = JSON.parse(data) as StreamEvent;

                // Extract and set session ID if present
                if (chunk.session_id && !sessionId) {
                  setSessionId(chunk.session_id);
                }

                // Only process chunks that belong to the current session
                if (chunk.session_id && chunk.session_id !== currentSessionIdRef.current) {
                  continue;
                }

                // Process simplified events from backend aggregation layer
                if (chunk.type === 'reasoning') {
                  setIsLoading(false);
                  scheduleUpdate((prev) => handleReasoning(prev, chunk));
                } else if (chunk.type === 'tool_call') {
                  setIsLoading(false);
                  scheduleUpdate((prev) => handleToolCall(prev, chunk));
                } else if (chunk.type === 'response') {
                  setIsLoading(false);
                  const responseEvent = chunk;
                  scheduleUpdate((prev) => handleResponse(prev, responseEvent));

                  // If response is completed, flush pending updates and call onFinish
                  if (responseEvent.status === 'completed') {
                    flushPendingUpdates();
                    setMessages((prev) => {
                      const lastMsg = prev[prev.length - 1];
                      if (lastMsg && lastMsg.role === 'assistant') {
                        options?.onFinish?.(lastMsg);
                      }
                      return prev;
                    });
                  }
                } else if (chunk.type === 'node_started') {
                  scheduleUpdate((prev) => handleNodeStarted(prev, chunk));
                } else if (chunk.type === 'node_completed') {
                  scheduleUpdate((prev) => handleNodeCompleted(prev, chunk));
                } else if (chunk.type === 'error') {
                  console.error('Stream error:', chunk.message);
                  setIsLoading(false);
                  scheduleUpdate((prev) => handleError(prev, chunk));
                }
              } catch (_error) {
                // Ignore parse errors
              }
            }
          }
        }
      } catch (error) {
        console.error('Chat error:', error);
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        options?.onError?.(new Error(errorMessage));
        setIsLoading(false);

        // Remove the loading assistant message on error
        setMessages((prev) =>
          prev.filter((msg) => {
            // Keep non-assistant messages and assistant messages with actual content
            if (msg.role !== 'assistant') return true;

            // Keep if it has any content items with non-empty text
            return msg.content.some((item) => {
              if (item.type === 'output_text' || item.type === 'reasoning') {
                return item.text.trim() !== '';
              }
              if (item.type === 'tool_call') {
                return true; // Keep tool calls
              }
              return false;
            });
          })
        );
      }
    },
    [agentId, sessionId, isLoading, options, scheduleUpdate, flushPendingUpdates]
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
    setSessionId,
    attachedFiles,
    clearAttachedFiles,
    setAttachedFiles,
    flushPendingUpdates,
  };
}
