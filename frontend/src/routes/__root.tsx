import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createRootRoute, Outlet } from '@tanstack/react-router';
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools';
import { UserProvider } from '@/contexts/UserContext';

// Create QueryClient outside component to avoid recreating on every render
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 10, // 10 minutes
      retry: 3,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 1,
    },
  },
});

export const Route = createRootRoute({
  component: RootComponent,
  errorComponent: ({ error }) => (
    <div style={{ padding: '20px', textAlign: 'center' }}>
      <h2>Something went wrong!</h2>
      <pre
        style={{
          color: 'red',
          textAlign: 'left',
          background: '#f5f5f5',
          padding: '10px',
          borderRadius: '4px',
        }}
      >
        {error.message}
      </pre>
      <button
        onClick={() => window.location.reload()}
        style={{
          padding: '10px 20px',
          backgroundColor: '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
        }}
      >
        Reload Page
      </button>
    </div>
  ),
});

function RootComponent() {
  return (
    <QueryClientProvider client={queryClient}>
      <UserProvider>
        <Outlet />
        <TanStackRouterDevtools />
      </UserProvider>
    </QueryClientProvider>
  );
}
