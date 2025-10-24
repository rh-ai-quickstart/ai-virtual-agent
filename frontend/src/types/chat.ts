export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: SimpleContentItem[];
  timestamp: Date;
}

export interface TextContentItem {
  type: 'input_text';
  text: string;
}

export interface OutputTextContentItem {
  type: 'output_text';
  text: string;
}

export interface ImageContentItem {
  type: 'input_image';
  image_url: string;
}

export type SimpleContentItem = TextContentItem | OutputTextContentItem | ImageContentItem;

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
  last_response_id?: string | null;
}

export interface PaginationInfo {
  page: number;
  page_size: number;
  total_messages: number;
  has_more: boolean;
  messages_loaded: number;
}

export interface ChatSessionDetail {
  id: string;
  title: string;
  agent_name: string;
  agent_id: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
  last_response_id?: string | null;
  pagination?: PaginationInfo;
}
