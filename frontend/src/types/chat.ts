// Type for trace entries
export interface ReasoningEntry {
  type: 'reasoning';
  text: string;
}

export interface ToolCallEntry {
  type: 'tool_call';
  id?: string;
  name: string;
  server_label?: string;
  arguments?: string;
  output?: string;
  error?: string;
  status: 'in_progress' | 'completed' | 'failed';
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: SimpleContentItem[];
  timestamp: Date;
  tool_calls?: ToolCallEntry[];
}

export interface TextContentItem {
  type: 'input_text';
  text: string;
}

export interface OutputTextContentItem {
  type: 'output_text';
  text: string;
  id?: string; // Internal: item_id from LlamaStack
  contentIndex?: number; // Internal: content_index from LlamaStack
}

export interface ReasoningContentItem {
  type: 'reasoning';
  text: string;
  id?: string; // Internal: item_id from LlamaStack
  contentIndex?: number; // Internal: content_index from LlamaStack
  isComplete?: boolean;
}

export interface ToolCallContentItem {
  type: 'tool_call';
  name: string;
  server_label?: string;
  arguments?: string;
  output?: string;
  error?: string;
  status?: 'in_progress' | 'completed' | 'failed';
  id?: string; // Internal: item.id from LlamaStack
}

export interface ImageContentItem {
  type: 'input_image';
  image_url: string;
}

export type GraphNodeStatus = 'pending' | 'running' | 'completed';

export interface GraphNodeContentItem {
  type: 'graph_node';
  node_id: string;
  label: string;
  status: GraphNodeStatus;
}

export type SimpleContentItem =
  | TextContentItem
  | OutputTextContentItem
  | ReasoningContentItem
  | ToolCallContentItem
  | ImageContentItem
  | GraphNodeContentItem;

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
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

/**
 * Simplified streaming event types from backend aggregation layer
 * The backend consumes raw LlamaStack events and sends these simplified events
 */
export interface BaseStreamEvent {
  type: string;
  session_id: string;
}

export interface ReasoningEvent extends BaseStreamEvent {
  type: 'reasoning';
  text: string;
  status: 'in_progress' | 'completed';
  id: string;
}

export interface ToolCallEvent extends BaseStreamEvent {
  type: 'tool_call';
  name: string;
  server_label?: string;
  arguments?: string;
  output?: string;
  error?: string;
  status: 'in_progress' | 'completed' | 'failed';
  id: string;
}

export interface ResponseEvent extends BaseStreamEvent {
  type: 'response';
  delta: string;
  status: 'in_progress' | 'completed';
  id: string;
}

export interface ErrorEvent extends BaseStreamEvent {
  type: 'error';
  message: string;
}

export interface NodeStartedEvent extends BaseStreamEvent {
  type: 'node_started';
  node: string;
}

export interface NodeCompletedEvent extends BaseStreamEvent {
  type: 'node_completed';
  node: string;
}

export type StreamEvent =
  | ReasoningEvent
  | ToolCallEvent
  | ResponseEvent
  | ErrorEvent
  | NodeStartedEvent
  | NodeCompletedEvent;
