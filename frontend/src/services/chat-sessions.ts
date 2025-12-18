import { CHAT_SESSIONS_API_ENDPOINT } from '@/config/api';
import { ChatSessionSummary, ChatSessionDetail, ChatMessage } from '@/types/chat';
import { ErrorResponse } from '@/types';

// Re-export types for backward compatibility
export type { ChatSessionSummary, ChatSessionDetail } from '@/types/chat';

interface ConversationMessagesResponse {
  messages: ChatMessage[];
}

export async function fetchChatSessions(agentId?: string): Promise<ChatSessionSummary[]> {
  const url = agentId
    ? `${CHAT_SESSIONS_API_ENDPOINT}?agent_id=${agentId}`
    : CHAT_SESSIONS_API_ENDPOINT;

  const response = await fetch(url, { credentials: 'include' });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to fetch chat sessions' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to fetch chat sessions');
  }
  return response.json() as Promise<ChatSessionSummary[]>;
}

export async function fetchSessionMessages(sessionId: string): Promise<ChatMessage[]> {
  const response = await fetch(`${CHAT_SESSIONS_API_ENDPOINT}${sessionId}/messages`, {
    credentials: 'include',
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to fetch conversation messages' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to fetch conversation messages');
  }
  const data = (await response.json()) as ConversationMessagesResponse;
  return data.messages;
}

export async function fetchChatSession(
  sessionId: string,
  agentId: string,
  loadMessages: boolean = true
): Promise<ChatSessionDetail> {
  const params = new URLSearchParams({
    agent_id: agentId,
  });

  const response = await fetch(`${CHAT_SESSIONS_API_ENDPOINT}${sessionId}?${params}`, {
    credentials: 'include',
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to fetch chat session' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to fetch chat session');
  }

  const sessionData = (await response.json()) as Omit<ChatSessionDetail, 'messages'>;

  // Fetch messages separately if requested
  const messages = loadMessages ? await fetchSessionMessages(sessionId) : [];

  return {
    ...sessionData,
    messages,
  } as ChatSessionDetail;
}

export async function deleteChatSession(sessionId: string, agentId: string): Promise<void> {
  const response = await fetch(`${CHAT_SESSIONS_API_ENDPOINT}${sessionId}?agent_id=${agentId}`, {
    credentials: 'include',
    method: 'DELETE',
  });
  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to delete chat session' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to delete chat session');
  }
}

export async function createChatSession(
  agentId: string,
  sessionName?: string
): Promise<ChatSessionDetail> {
  const response = await fetch(CHAT_SESSIONS_API_ENDPOINT, {
    credentials: 'include',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      agent_id: agentId,
      session_name: sessionName,
    }),
  });

  if (!response.ok) {
    const errorData = (await response
      .json()
      .catch(() => ({ detail: 'Failed to create chat session' }))) as ErrorResponse;
    throw new Error(errorData.detail ?? 'Failed to create chat session');
  }
  return response.json() as Promise<ChatSessionDetail>;
}
