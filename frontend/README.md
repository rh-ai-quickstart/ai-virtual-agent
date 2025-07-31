# Frontend

Modern React application for the AI Virtual Agent Kickstart, providing an intuitive interface for managing AI agents, knowledge bases, and real-time chat interactions.

## Architecture Overview

The frontend is built with modern React patterns and follows a clean, hook-based architecture:

```
src/
├── components/           # Reusable UI components (now using custom hooks)
│   ├── chat.tsx         # Main chat interface with PatternFly Chatbot
│   ├── agent-*.tsx      # Agent management components
│   ├── knowledge-base-*.tsx # Knowledge base management
│   └── ...
├── hooks/               # Custom React hooks (data fetching & state management)
│   ├── index.ts         # Central export for all hooks
│   ├── useChat.ts       # Chat functionality with SSE streaming
│   ├── useAgents.ts     # Agent operations (CRUD + state)
│   ├── useKnowledgeBases.ts # Knowledge base operations
│   └── ...              # More specialized hooks
├── services/            # API service layer (pure functions)
│   ├── agents.ts        # Agent API calls
│   ├── knowledge-bases.ts # Knowledge base API calls
│   ├── chat-sessions.ts # Session API calls
│   └── ...              # More service modules
├── routes/              # TanStack Router configuration
│   ├── index.tsx        # Main chat page
│   └── config/          # Configuration pages
├── contexts/            # React contexts
│   └── UserContext.tsx  # User authentication context
└── types/               # TypeScript type definitions
```

## Technology Stack

- **React 18** - Core framework with modern hooks
- **TypeScript** - Type safety and development experience
- **PatternFly** - Enterprise-grade UI component library
- **TanStack Router** - Type-safe routing
- **TanStack Query** - Server state management with caching
- **Vite** - Build tool and development server

## Key Features

### 🤖 Agent Management

- **Visual Agent Creation**: Form-based agent configuration with real-time validation
- **Tool Integration**: Multi-select interface for tools (RAG, web search, MCP servers)
- **Model Selection**: Dynamic model dropdown with real-time availability
- **Advanced Parameters**: Collapsible accordion for sampling parameters

### 💬 Real-time Chat

- **Streaming Responses**: Server-Sent Events for real-time message streaming
- **Session Management**: Persistent chat sessions with history sidebar
- **Multiple Message Types**: Support for text, tool usage, and error messages
- **PatternFly Integration**: Enterprise-grade chat UI components

### 📚 Knowledge Base Management

- **Status Tracking**: Real-time status display (READY, PENDING, ORPHANED)
- **Drag & Drop Upload**: Intuitive file upload for document ingestion
- **S3 Integration**: Configure external document sources
- **Progress Monitoring**: Track ingestion pipeline progress

### 🔧 Configuration Management

- **User Profiles**: User authentication and role management
- **MCP Servers**: External tool server configuration
- **Model Servers**: LLM provider management
- **Guardrails**: Safety shield configuration

## Development Setup

### Prerequisites

- **Node.js 18+** - Runtime environment
- **npm** - Package manager

### Installation

1. **Navigate to frontend directory**:

   ```bash
   cd frontend
   ```

2. **Install dependencies**:

   ```bash
   npm install
   ```

3. **Start development server**:

   ```bash
   npm run dev
   ```

   The application will be available at `http://localhost:5173`

### Available Scripts

```bash
# Development
npm run dev          # Start development server with hot reload
npm run build        # Build for production
npm run preview      # Preview production build

# Code Quality
npm run lint         # ESLint code analysis
npm run lint:fix     # Auto-fix linting issues
npm run format       # Format code with Prettier
npm run format:check # Check code formatting

# Type Checking
npm run type-check   # TypeScript compilation check
```

## Custom Hooks Architecture

Our frontend uses a comprehensive set of custom hooks that encapsulate data fetching, state management, and business logic. This approach provides:

- **🔄 Consistent API**: All hooks follow the same pattern
- **🎯 No Prop Drilling**: Components access data directly
- **🧹 Clean Components**: UI logic separated from data logic
- **🔒 Type Safety**: Full TypeScript support
- **⚡ Performance**: Automatic caching and optimization

### Hook Pattern

All custom hooks follow a consistent interface:

```typescript
const {
  // Data
  data,
  isLoading,
  error,

  // Mutations
  createItem,
  deleteItem,
  updateItem,

  // Mutation states
  isCreating,
  isDeleting,
  createError,
  deleteError,

  // Utilities
  refreshData,
} = useCustomHook();
```

### Key Hooks

#### useAgents (`hooks/useAgents.ts`)

Complete agent management:

```typescript
export function AgentManagement() {
  const {
    agents,           // Agent[]
    isLoading,        // boolean
    error,            // Error | null
    createAgent,      // (data: NewAgent) => Promise<Agent>
    deleteAgent,      // (id: string) => Promise<void>
    isCreating,       // boolean
    isDeleting,       // boolean
    refreshAgents     // () => void
  } = useAgents();

  return (
    <div>
      {isLoading && <Spinner />}
      {agents?.map(agent => (
        <AgentCard
          key={agent.id}
          agent={agent}
          onDelete={() => deleteAgent(agent.id)}
        />
      ))}
    </div>
  );
}
```

#### useKnowledgeBases (`hooks/useKnowledgeBases.ts`)

Knowledge base operations with status tracking:

```typescript
export function KnowledgeBaseList() {
  const {
    knowledgeBases, // KnowledgeBaseWithStatus[]
    isLoading, // boolean
    createKnowledgeBase, // (data) => Promise<KnowledgeBase>
    deleteKnowledgeBase, // (id) => Promise<void>
    llamaStackKnowledgeBases, // LSKnowledgeBase[]
  } = useKnowledgeBases();

  // Component uses data directly, no prop drilling
}
```

#### useChat (`hooks/useChat.ts`)

Real-time chat with streaming:

```typescript
export function Chat() {
  const {
    messages, // ChatMessage[]
    input, // string
    isLoading, // boolean
    sendMessage, // (content: string) => void
    handleInputChange, // (event) => void
    handleSubmit, // (event) => void
    loadSession, // (sessionId: string) => Promise<void>
    sessionId, // string | null
  } = useChat(agentId);

  // Real-time streaming, session management, all handled
}
```

## Component Structure

### Modern Component Pattern

Components are now clean and focused on UI logic:

```typescript
// ✅ Clean component using custom hooks
export function AgentList() {
  // Single hook call provides everything needed
  const { agents, isLoading, error } = useAgents();

  if (isLoading) return <Spinner />;
  if (error) return <Alert variant="danger">{error.message}</Alert>;

  return (
    <Flex direction={{ default: 'column' }}>
      {agents?.map(agent => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </Flex>
  );
}
```

### Form Components

Forms use hooks directly instead of complex prop passing:

```typescript
// ✅ AgentForm manages its own data dependencies
export function AgentForm({ onSubmit, isSubmitting, onCancel }: AgentFormProps) {
  // All data fetched internally
  const { models, isLoadingModels, modelsError } = useModels();
  const { llamaStackKnowledgeBases, isLoadingLlamaStack } = useKnowledgeBases();
  const { tools, isLoading: isLoadingTools } = useTools();
  const { shields, isLoading: isLoadingShields } = useShields();

  // No more complex prop interfaces needed
  return <Form>...</Form>;
}
```

## State Management

### TanStack Query Integration

Our custom hooks wrap TanStack Query for optimal caching:

```typescript
// Inside useAgents.ts
export const useAgents = () => {
  const queryClient = useQueryClient();

  // Automatic caching and background updates
  const agentsQuery = useQuery<Agent[], Error>({
    queryKey: ['agents'],
    queryFn: fetchAgents,
  });

  // Optimistic updates with proper error handling
  const createAgentMutation = useMutation<Agent, Error, NewAgent>({
    mutationFn: createAgent,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
  });

  return {
    agents: agentsQuery.data,
    isLoading: agentsQuery.isLoading,
    error: agentsQuery.error,
    createAgent: createAgentMutation.mutateAsync,
    isCreating: createAgentMutation.isPending,
  };
};
```

### Service Layer

Pure API functions with no React dependencies:

```typescript
// services/agents.ts - Pure functions
export const fetchAgents = async (): Promise<Agent[]> => {
  const response = await fetch(AGENTS_API_ENDPOINT);
  if (!response.ok) throw new Error('Network response was not ok');
  return response.json() as Agent[];
};

export const createAgent = async (newAgent: NewAgent): Promise<Agent> => {
  const response = await fetch(AGENTS_API_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(newAgent),
  });
  if (!response.ok) throw new Error('Network response was not ok');
  return response.json() as Agent[];
};
```

## Key Components

### Chat Component (`components/chat.tsx`)

The main chat interface using PatternFly's Chatbot component:

```typescript
// Real-time streaming chat with session management
export function Chat() {
  const {
    messages,
    sendMessage,
    isLoading,
    loadSession
  } = useChat(selectedAgent);

  // PatternFly Chatbot integration
  return (
    <Chatbot displayMode={ChatbotDisplayMode.embedded}>
      <ChatbotContent>
        <MessageBox messages={patternflyMessages} />
      </ChatbotContent>
      <ChatbotFooter>
        <MessageBar onSendMessage={sendMessage} />
      </ChatbotFooter>
    </Chatbot>
  );
}
```

### Agent Form (`components/agent-form.tsx`)

Self-contained form with internal data management:

```typescript
export function AgentForm({ onSubmit, isSubmitting, onCancel }: AgentFormProps) {
  // All dependencies managed internally
  const { models, isLoadingModels, modelsError } = useModels();
  const { llamaStackKnowledgeBases, isLoadingLlamaStack } = useKnowledgeBases();
  const { tools, isLoading: isLoadingTools } = useTools();
  const { shields, isLoading: isLoadingShields } = useShields();

  // Form logic...
  return <Form>...</Form>;
}
```

## Type Safety

### Key Types (`types/index.d.ts`)

```typescript
interface Agent {
  id: string;
  name: string;
  model_name: string;
  prompt: string;
  knowledge_base_ids: string[];
  tools: ToolAssociationInfo[];
  sampling_strategy: 'greedy' | 'top-p' | 'top-k';
  // ... other properties
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}
```

## Error Handling & Performance

### Graceful Error Handling

```typescript
// Built into every hook
const { data, isLoading, error } = useAgents();

if (error) {
  return <Alert variant="danger">{error.message}</Alert>;
}
```

### Performance Optimizations

- **Automatic Caching**: TanStack Query handles intelligent caching
- **Background Updates**: Stale data updates in background
- **Optimistic Updates**: Immediate UI feedback
- **Code Splitting**: Route-based and component-based splitting

## Development Guidelines

### Hook Usage Best Practices

```typescript
// ✅ Use hooks at component level
export function Component() {
  const { data, isLoading, createItem } = useCustomHook();

  // Avoid prop drilling
  return <ChildComponent onAction={createItem} />;
}

// ✅ Handle loading and error states
export function Component() {
  const { data, isLoading, error } = useCustomHook();

  if (isLoading) return <Spinner />;
  if (error) return <Alert variant="danger">{error.message}</Alert>;
  if (!data) return <EmptyState />;

  return <DataComponent data={data} />;
}
```

### Component Structure

```typescript
interface ComponentProps {
  // Minimal props - data comes from hooks
  onAction?: () => void;
  variant?: 'primary' | 'secondary';
}

export function Component({ onAction, variant = 'primary' }: ComponentProps) {
  // 1. Hooks at the top
  const { data, isLoading, error, performAction } = useCustomHook();
  const [localState, setLocalState] = useState();

  // 2. Event handlers
  const handleAction = useCallback(() => {
    void performAction();
    onAction?.();
  }, [performAction, onAction]);

  // 3. Early returns for loading/error states
  if (isLoading) return <Spinner />;
  if (error) return <Alert variant="danger">{error.message}</Alert>;

  // 4. Main render
  return (
    <PatternFlyComponent variant={variant}>
      {data?.map(item => (
        <ItemComponent key={item.id} item={item} onAction={handleAction} />
      ))}
    </PatternFlyComponent>
  );
}
```

### Code Style

- **TypeScript Strict Mode**: Full type checking enabled
- **ESLint Rules**: React, TypeScript, and accessibility rules
- **Prettier Formatting**: Consistent code formatting
- **Promise Handling**: All promises properly handled with `void` or `.catch()`

### Testing (Future)

- **Hook Testing**: `@testing-library/react-hooks`
- **Component Testing**: React Testing Library
- **E2E Testing**: Playwright or Cypress
- **API Mocking**: MSW for service layer testing

## Troubleshooting

### Common Issues

**Hook dependency warnings:**

```bash
# Check for missing dependencies in useCallback/useEffect
npm run lint
```

**Type errors:**

```bash
# Run type checking
npm run type-check

# Check for TypeScript configuration issues
npx tsc --noEmit
```

**Promise handling errors:**

```bash
# All async operations should use void or proper error handling
void asyncOperation(); // For fire-and-forget
await asyncOperation().catch(handleError); // With error handling
```

### Development Tools

**Browser Extensions:**

- **React Developer Tools**: Component and hook debugging
- **TanStack Query DevTools**: Server state inspection
- **Vite DevTools**: Build analysis

**VSCode Extensions:**

- **TypeScript Importer**: Automatic import organization
- **ESLint**: Real-time code analysis
- **Prettier**: Automatic formatting
- **Error Lens**: Inline error display
