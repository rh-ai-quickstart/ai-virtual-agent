export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
}

export interface UseLlamaChatOptions {
  onError?: (error: Error) => void;
  onFinish?: (message: ChatMessage) => void;
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  agent_name: string;
  updated_at: string;
  created_at: string;
}

export interface ChatSessionDetail {
  id: string;
  title: string;
  agent_name: string;
  agent_id: string;
  messages: Array<{
    role: 'user' | 'assistant';
    content: string;
  }>;
  created_at: string;
  updated_at: string;
}
