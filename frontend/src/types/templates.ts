export interface Industry {
  id: string;
  name: string;
  description: string;
  icon?: string;
  color?: string;
  template_count: number;
  total_agents: number;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  category: string;
  metadata: Record<string, any>;
  persona_count: number;
  agent_count: number;
  industry_id: string;
}

export interface TemplateSuite {
  id: string;
  name: string;
  description: string;
  category: string;
  metadata: Record<string, any>;
  personas: Record<string, TemplatePersona>;
  industry_id?: string | null;  // Make it optional and allow null
  agents?: AgentConfig[];  // Add agents array
}

export interface TemplatePersona {
  label: string;
  description: string;
  icon?: string;
  color?: string;
  className?: string;
  avatarBg?: string;
  avatarIcon?: string;
  gradient?: string;
  borderColor?: string;
  demo_questions: string[];
  agents: AgentConfig[];
}

export interface AgentConfig {
  name: string;
  description: string;
  prompt: string;
  model_name: string;
  tools: Array<{ toolgroup_id: string }>;
  knowledge_base_ids: string[];
  temperature?: number;
  repetition_penalty?: number;
  max_tokens?: number;
  top_p?: number;
  max_infer_iters?: number;
  input_shields?: string[];
  output_shields?: string[];
  demo_questions?: string[];
  persona?: string;
}

export interface TemplateDeployment {
  id: string;
  template_id: string;
  deployed_at: string;
  status: 'success' | 'failed' | 'in_progress';
  deployed_agents: string[];
  error_message?: string;
}

// Template deployment request
export interface TemplateDeployRequest {
  selected_agents?: string[];
  override_settings?: Record<string, any>;
}

// Template deployment response
export interface TemplateDeployResponse {
  deployed_agents: Array<{
    id: string;
    name: string;
    prompt: string;
    model_name: string;
    input_shields: string[];
    output_shields: string[];
    temperature: number;
    repetition_penalty: number;
    max_tokens: number;
    top_p: number;
    knowledge_base_ids: string[];
    tools: string[];
    max_infer_iters: number;
    enable_session_persistence: boolean;
  }>;
  failed_agents: Array<{
    name: string;
    error: string;
  }>;
  template_id: string;
  deployment_summary: {
    template_id: string;
    template_name: string;
    total_agents: number;
    successful_deployments: number;
    failed_deployments: number;
    deployment_time: string;
    success_rate: number;
  };
}

// Template category
export interface TemplateCategory {
  name: string;
  count: number;
  description?: string;
}

export interface ToolAssociationInfo {
  tool_id: string;
  tool_name: string;
  enabled: boolean;
} 