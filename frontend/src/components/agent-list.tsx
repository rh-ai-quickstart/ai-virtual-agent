import { AgentCard } from '@/components/agent-card';
import { Agent } from '@/routes/config/agents';
import { fetchAgents } from '@/services/agents';
import { Alert, Spinner } from '@patternfly/react-core';
import { useQuery } from '@tanstack/react-query';

export function AgentList() {
  // Query for Agents
  const {
    data: agents,
    isLoading: isLoadingAgents,
    error: agentsError,
  } = useQuery<Agent[], Error>({
    queryKey: ['agents'],
    queryFn: fetchAgents,
  });

  return (
    <div>
      {isLoadingAgents && <Spinner aria-label="Loading agents" />}
      {agentsError && (
        <Alert variant="danger" title="Error loading agents">
          {agentsError.message}
        </Alert>
      )}
      {!isLoadingAgents && !agentsError && agents && agents.length === 0 && (
        <p>No agents configured yet.</p>
      )}
      {!isLoadingAgents && !agentsError && agents && agents.length > 0 && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: '1rem',
          padding: '1rem 0'
        }}>
          {agents
            .sort((a, b) => {
              // Safe sorting with fallback for missing dates
              const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
              const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
              return dateB - dateA;
            })
            .map((agent) => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
        </div>
      )}
    </div>
  );
}
