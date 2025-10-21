const baseUrl = (import.meta.env.VITE_API_BASE_URL as string) || ''; // fallback to '' for relative paths in prod

export default baseUrl;

export const LLMS_API_ENDPOINT = '/api/v1/llama_stack/models/llms';
export const EMBEDDING_MODELS_API_ENDPOINT = '/api/v1/llama_stack/models/embedding';
export const MODELS_REGISTER_API_ENDPOINT = '/api/v1/llama_stack/models/register';
export const PROVIDER_MODELS_API_ENDPOINT = '/api/v1/llama_stack/providers/models';
export const PROVIDERS_API_ENDPOINT = '/api/v1/llama_stack/providers/';
export const KNOWLEDGE_BASES_API_ENDPOINT = '/api/v1/knowledge_bases/';
export const LLAMA_STACK_TOOLS_API_ENDPOINT = '/api/v1/llama_stack/tools/';
export const TOOLS_API_ENDPOINT = '/api/v1/tools/';
export const MCP_SERVERS_API_ENDPOINT = '/api/v1/llama_stack/mcp_servers/';
export const AGENTS_API_ENDPOINT = '/api/v1/virtual_agents/';
export const CHAT_API_ENDPOINT = '/api/v1/chat';
export const CHAT_SESSIONS_API_ENDPOINT = '/api/v1/chat_sessions/';
export const SHIELDS_API_ENDPOINT = '/api/v1/llama_stack/shields/';
export const USERS_API_ENDPOINT = '/api/v1/users/';
export const ATTACHMENTS_API_ENDPOINT = '/api/v1/attachments/';
