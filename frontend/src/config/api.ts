const baseUrl = (import.meta.env.VITE_API_BASE_URL as string) || ''; // fallback to '' for relative paths in prod

export default baseUrl;

export const LLMS_API_ENDPOINT = '/api/llama_stack/llms';
export const EMBEDDING_MODELS_API_ENDPOINT = '/api/llama_stack/embedding_models';
export const PROVIDERS_API_ENDPOINT = '/api/llama_stack/providers';
export const KNOWLEDGE_BASES_API_ENDPOINT = '/api/knowledge_bases/';
export const LLAMA_STACK_KNOWLEDGE_BASES_API_ENDPOINT = '/api/llama_stack/knowledge_bases';
export const LLAMA_STACK_TOOLS_API_ENDPOINT = '/api/llama_stack/tools';
export const TOOLS_API_ENDPOINT = '/api/tools/';
export const MCP_SERVERS_API_ENDPOINT = '/api/mcp_servers/';  // Added this line
export const AGENTS_API_ENDPOINT = '/api/virtual_assistants/';
export const CHAT_API_ENDPOINT = '/api/llama_stack/chat';
export const CHAT_SESSIONS_API_ENDPOINT = '/api/chat_sessions/';
export const SHIELDS_API_ENDPOINT = '/api/llama_stack/shields';
export const USERS_API_ENDPOINT = '/api/users/';
