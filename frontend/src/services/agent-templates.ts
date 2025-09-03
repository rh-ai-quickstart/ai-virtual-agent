/**
 * Service for interacting with agent templates API endpoints.
 *
 * This service provides functions to initialize agents from predefined templates,
 * including automatic knowledge base creation and data ingestion.
 */

import {
  AgentTemplate,
  TemplateInitializationRequest,
  TemplateInitializationResponse,
} from '@/types/agent';

// Re-export types for backward compatibility
export type {
  AgentTemplate,
  TemplateInitializationRequest,
  TemplateInitializationResponse,
} from '@/types/agent';

const API_BASE_URL = '/api';

/**
 * Get list of available agent templates.
 */
export async function getAvailableTemplates(): Promise<string[]> {
  const response = await fetch(`${API_BASE_URL}/agent_templates/`);
  if (!response.ok) {
    throw new Error(`Failed to fetch templates: ${response.statusText}`);
  }
  return response.json() as Promise<string[]>;
}

/**
 * Get detailed information about a specific template.
 */
export async function getTemplateDetails(templateName: string): Promise<AgentTemplate> {
  const response = await fetch(`${API_BASE_URL}/agent_templates/${templateName}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch template details: ${response.statusText}`);
  }
  return response.json() as Promise<AgentTemplate>;
}

/**
 * Initialize an agent from a template.
 */
export async function initializeAgentFromTemplate(
  request: TemplateInitializationRequest
): Promise<TemplateInitializationResponse> {
  const response = await fetch(`${API_BASE_URL}/agent_templates/initialize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const errorData = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(errorData.detail || `Failed to initialize agent: ${response.statusText}`);
  }

  return response.json() as Promise<TemplateInitializationResponse>;
}

/**
 * Initialize all agent templates at once.
 * This function initializes all available templates across all categories.
 */
export async function initializeAllTemplates(): Promise<TemplateInitializationResponse[]> {
  const response = await fetch(`${API_BASE_URL}/agent_templates/initialize-all`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new Error(
      errorData.detail || `Failed to initialize all templates: ${response.statusText}`
    );
  }

  return response.json() as Promise<TemplateInitializationResponse[]>;
}

/**
 * Initialize a specific suite.
 * This function initializes all agents within a specific suite.
 */
export async function initializeSuite(suiteId: string): Promise<TemplateInitializationResponse[]> {
  const response = await fetch(`/api/agent_templates/initialize-suite/${suiteId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = (await response.json()) as { detail?: string };
    throw new Error(errorData.detail || `Failed to initialize suite: ${response.statusText}`);
  }

  return response.json() as Promise<TemplateInitializationResponse[]>;
}

/**
 * Get suites grouped by category.
 */
export async function getSuitesByCategory(): Promise<Record<string, string[]>> {
  const response = await fetch(`/api/agent_templates/suites/categories`);
  if (!response.ok) {
    throw new Error(`Failed to fetch suites by category: ${response.statusText}`);
  }
  return response.json() as Promise<Record<string, string[]>>;
}

/**
 * Get detailed information about a specific suite.
 */
export async function getSuiteDetails(suiteId: string): Promise<{
  id: string;
  name: string;
  description: string;
  category: string;
  agent_count: number;
  agent_names: string[];
  template_ids?: string[];
}> {
  const response = await fetch(`/api/agent_templates/suites/${suiteId}/details`);
  if (!response.ok) {
    throw new Error(`Failed to fetch suite details: ${response.statusText}`);
  }
  return response.json() as Promise<{
    id: string;
    name: string;
    description: string;
    category: string;
    agent_count: number;
    agent_names: string[];
    template_ids?: string[];
  }>;
}

/**
 * Get detailed information about all categories.
 */
export async function getCategoriesInfo(): Promise<
  Record<
    string,
    {
      name: string;
      description: string;
      icon: string;
      suite_count: number;
    }
  >
> {
  const response = await fetch(`/api/agent_templates/categories/info`);
  if (!response.ok) {
    throw new Error(`Failed to fetch categories info: ${response.statusText}`);
  }
  return response.json() as Promise<
    Record<
      string,
      {
        name: string;
        description: string;
        icon: string;
        suite_count: number;
      }
    >
  >;
}

/**
 * Initialize a specific template with persona mapping.
 * This function combines template initialization with persona storage.
 */
export async function initializeTemplate(
  templateName: string,
  customName?: string,
  customPrompt?: string
): Promise<{ agent: TemplateInitializationResponse; persona: string }> {
  const request: TemplateInitializationRequest = {
    template_name: templateName,
    custom_name: customName,
    custom_prompt: customPrompt,
    include_knowledge_base: true,
  };

  const response = await initializeAgentFromTemplate(request);

  // Get the persona from the template details
  const templateDetails = await getTemplateDetails(templateName);

  return {
    agent: response,
    persona: templateDetails.persona,
  };
}
