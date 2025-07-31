import { AgentCard } from '@/components/agent-card';
import { Alert, Flex, Spinner } from '@patternfly/react-core';
import { useAgents } from '@/hooks';

export function AgentList() {
  // Use custom agents hook
  const { agents, isLoading: isLoadingAgents, error: agentsError } = useAgents();

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
        <Flex direction={{ default: 'column' }}>
          {agents
            .sort((a, b) => Date.parse(b.created_at ?? '') - Date.parse(a.created_at ?? ''))
            .map((agent) => (
              <AgentCard key={agent.id} agent={agent} />
            ))}
        </Flex>
      )}
    </div>
  );
}
