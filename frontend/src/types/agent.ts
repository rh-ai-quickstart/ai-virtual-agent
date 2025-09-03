import { ToolAssociationInfo } from './tools';

export type SamplingStrategy = 'greedy' | 'top-p' | 'top-k';

export type ParameterFieldName =
  | 'temperature'
  | 'top_p'
  | 'top_k'
  | 'max_tokens'
  | 'repetition_penalty';

export interface SamplingParameters {
  sampling_strategy?: SamplingStrategy;
  temperature?: number;
  top_p?: number;
  top_k?: number;
  max_tokens?: number;
  repetition_penalty?: number;
}

export interface AgentBase {
  name: string;
  agent_type?: string;
  model_name: string;
  prompt: string;
  knowledge_base_ids: string[];
  input_shields: string[];
  output_shields: string[];
}

export interface Agent extends AgentBase, SamplingParameters {
  id: string;
  tools: ToolAssociationInfo[];
  created_by: string;
  created_at: string;
  updated_at: string;
  // Optional metadata for grouping and display
  template_id?: string;
  template_name?: string;
  suite_id?: string;
  suite_name?: string;
  category?: string;
}

export interface NewAgent extends AgentBase, SamplingParameters {
  tools: ToolAssociationInfo[];
}

export interface AgentTemplate {
  name: string;
  persona: string;
  prompt: string;
  model_name: string;
  tools: Array<{ toolgroup_id: string }>;
  knowledge_base_ids: string[];
  knowledge_base_config?: {
    name: string;
    version: string;
    embedding_model: string;
    provider_id: string;
    vector_db_name: string;
    is_external: boolean;
    source: string;
    source_configuration: string[];
  };
  demo_questions?: string[];
}

export interface TemplateInitializationRequest {
  template_name: string;
  custom_name?: string;
  custom_prompt?: string;
  include_knowledge_base?: boolean;
}

export interface TemplateInitializationResponse {
  agent_id: string;
  agent_name: string;
  persona: string;
  knowledge_base_created: boolean;
  knowledge_base_name?: string;
  status: string;
  message: string;
}

export interface SuiteDetails {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: React.ReactNode;
  title: string;
  agents: string[];
  agentCount: number;
  templateIds?: string[];
}
