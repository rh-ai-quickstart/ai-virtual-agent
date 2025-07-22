// Always use relative URLs - works in both local and production
const baseUrl = '';

export default baseUrl;

// API Endpoints - ALL of them
export const LLMS_API_ENDPOINT = '/api/llama_stack/llms';
export const EMBEDDING_MODELS_API_ENDPOINT = '/api/llama_stack/embedding_models';
export const PROVIDERS_API_ENDPOINT = '/api/llama_stack/providers';
export const KNOWLEDGE_BASES_API_ENDPOINT = '/api/knowledge_bases/';
export const VIRTUAL_ASSISTANTS_API_ENDPOINT = '/api/virtual_assistants/';
export const TEMPLATES_API_ENDPOINT = '/api/templates/';
export const LLAMA_STACK_KNOWLEDGE_BASES_API_ENDPOINT = '/api/llama_stack/knowledge_bases';
export const AGENTS_API_ENDPOINT = '/api/virtual_assistants/';
export const LLAMA_STACK_TOOLS_API_ENDPOINT = '/api/llama_stack/toolgroups';
export const CHAT_SESSIONS_API_ENDPOINT = '/api/chat_sessions/';
export const CHAT_API_ENDPOINT = '/api/chat/';

// API client for making HTTP requests
export const apiClient = {
  async get(url: string, options: RequestInit = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

    try {
      const response = await fetch(`${baseUrl}${url}`, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers as Record<string, string>),
        },
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      return (await response.json()) as unknown;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout');
      }
      throw error;
    }
  },

  async post(url: string, data?: unknown): Promise<unknown> {
    const response = await fetch(baseUrl + url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  async put(url: string, data?: unknown): Promise<unknown> {
    const response = await fetch(baseUrl + url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },

  async delete(url: string): Promise<unknown> {
    const response = await fetch(baseUrl + url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  },
};
