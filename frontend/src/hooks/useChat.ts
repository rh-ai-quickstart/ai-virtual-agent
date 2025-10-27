import { useState, useCallback, useEffect, useRef } from 'react';
import { LlamaStackParser, extractSessionId } from '../adapters/llamaStackAdapter';
import { CHAT_API_ENDPOINT } from '../config/api';
import { fetchChatSession } from '@/services/chat-sessions';
import { ChatMessage, UseLlamaChatOptions, SimpleContentItem } from '@/types/chat';

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
  const [currentPage, setCurrentPage] = useState(1);
  const [hasMoreMessages, setHasMoreMessages] = useState(false);
  const [totalMessages, setTotalMessages] = useState(0);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  // Use a ref to track the current session ID for streaming responses
  const currentSessionIdRef = useRef<string | null>(sessionId);

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

        // Reset pagination state
        setCurrentPage(1);
        setHasMoreMessages(false);
        setTotalMessages(0);

        // Fetch session with most recent messages (page 1)
        const sessionDetail = await fetchChatSession(sessionId, agentId, 1, 50, true);
        if (!sessionDetail) {
          throw new Error(`Session ${sessionId} not found for agent ${agentId}`);
        }

        // Convert messages - parse timestamp string to Date
        const convertedMessages: ChatMessage[] = sessionDetail.messages.map((msg) => ({
          ...msg,
          timestamp: new Date(msg.timestamp as unknown as string),
        }));

        setMessages(convertedMessages);

        // Update pagination state
        if (sessionDetail.pagination) {
          setHasMoreMessages(sessionDetail.pagination.has_more);
          setTotalMessages(sessionDetail.pagination.total_messages);
          setCurrentPage(sessionDetail.pagination.page);
        }

        console.log(
          'Loaded messages:',
          convertedMessages.length,
          'Total:',
          sessionDetail.pagination?.total_messages
        );

        // Response chaining is now handled by the backend automatically

        // Update agent if different
        if (sessionDetail.agent_id && sessionDetail.agent_id !== agentId) {
          console.warn(`Loaded session for different agent: ${sessionDetail.agent_id}`);
          // Optionally handle this case, e.g., notify user or reset state
        }

        console.log('Session and initial messages loaded');
      } catch (error) {
        console.error('Error loading session:', error);
        options?.onError?.(error as Error);
      } finally {
        setIsLoading(false);
      }
    },
    [agentId, options]
  );

  const loadMoreMessages = useCallback(async () => {
    if (!sessionId || !hasMoreMessages || isLoadingMore) return;

    try {
      setIsLoadingMore(true);
      console.log(`Loading more messages for session ${sessionId}, page ${currentPage + 1}`);

      // Fetch next page of messages
      const sessionDetail = await fetchChatSession(sessionId, agentId, currentPage + 1, 50, true);
      if (!sessionDetail) {
        throw new Error(`Session ${sessionId} not found for agent ${agentId}`);
      }

      // Convert messages - parse timestamp string to Date
      const convertedMessages: ChatMessage[] = sessionDetail.messages.map((msg) => ({
        ...msg,
        timestamp: new Date(msg.timestamp as unknown as string),
      }));

      // Prepend older messages to the beginning of the array
      setMessages((prevMessages) => [...convertedMessages, ...prevMessages]);

      // Update pagination state
      if (sessionDetail.pagination) {
        setHasMoreMessages(sessionDetail.pagination.has_more);
        setCurrentPage(sessionDetail.pagination.page);
      }

      console.log('Loaded more messages:', convertedMessages.length);
    } catch (error) {
      console.error('Error loading more messages:', error);
      options?.onError?.(error as Error);
    } finally {
      setIsLoadingMore(false);
    }
  }, [sessionId, agentId, hasMoreMessages, isLoadingMore, currentPage, options]);

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
        content: [
          {
            text: '',
            type: 'output_text',
          },
        ],
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      try {
        // Prepare request - send the new user message
        // The backend will automatically look up the previous response ID for chaining
        const requestBody = {
          virtualAgentId: agentId,
          message: {
            role: userMessage.role,
            content: userMessage.content,
          },
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
              const parsed = LlamaStackParser.parse(data);
              if (parsed) {
                // Check if this message belongs to the current session
                try {
                  const messageData = JSON.parse(data) as { session_id?: string };
                  const messageSessionId = messageData.session_id;

                  // Only process messages that belong to the current session
                  if (messageSessionId && messageSessionId !== currentSessionIdRef.current) {
                    continue;
                  }
                } catch (_e) {
                  // If we can't parse the message data, continue processing (fallback behavior)
                }

                setMessages((prev) => {
                  const updated = [...prev];
                  const lastMsg = updated[updated.length - 1];
                  if (lastMsg && lastMsg.role === 'assistant') {
                    const c: SimpleContentItem[] = [...lastMsg.content];
                    if (c[0].type === 'output_text') {
                      // Replace content (backend sends complete response, not chunks)
                      c[0].text = parsed;
                      lastMsg.content = c;
                    }
                  }
                  return updated;
                });
              }

              // Response ID is now managed by the backend
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
            return (
              msg.role !== 'assistant' ||
              (msg.content.length > 0 &&
                msg.content[0].type === 'output_text' &&
                msg.content[0].text.trim() !== '')
            );
          })
        );
      }
    },
    [agentId, sessionId, isLoading, options]
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
    setCurrentPage(1);
    setHasMoreMessages(false);
    setTotalMessages(0);
    setIsLoadingMore(false);
  }, [agentId]);

  return {
    messages,
    input,
    handleInputChange,
    handleAttach,
    append,
    isLoading,
    loadSession,
    loadMoreMessages,
    sessionId,
    setSessionId,
    attachedFiles,
    clearAttachedFiles,
    setAttachedFiles,
    hasMoreMessages,
    isLoadingMore,
    totalMessages,
    currentPage,
  };
}
