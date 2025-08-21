import { AgentCard } from '@/components/agent-card';
import {
  Alert,
  Flex,
  FlexItem,
  Spinner,
  Title,
  Icon,
  Card,
  CardHeader,
  CardTitle,
  CardBody,
} from '@patternfly/react-core';
import { UserIcon } from '@patternfly/react-icons';
import { useAgents } from '@/hooks';
import type { Agent } from '@/types/agent';
import { SUITE_ICONS } from '@/utils/icons';

// Suite icons are shared via '@/utils/icons'

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
        <Flex direction={{ default: 'column' }} gap={{ default: 'gapLg' }}>
          {groupAgentsBySuite(agents).map(({ suiteId, suiteName, agents: groupAgents }) => (
            <FlexItem key={suiteId ?? 'uncategorized'}>
              <Card>
                <CardHeader>
                  <CardTitle>
                    <Flex gap={{ default: 'gapSm' }} alignItems={{ default: 'alignItemsCenter' }}>
                      <Icon>
                        {SUITE_ICONS[suiteId ?? ''] ?? <UserIcon style={{ color: '#3E8635' }} />}
                      </Icon>
                      <Title headingLevel="h2" className="pf-v6-u-mb-0">
                        {suiteName ?? 'Custom'}
                      </Title>
                    </Flex>
                  </CardTitle>
                </CardHeader>
                <CardBody>
                  <Flex direction={{ default: 'column' }}>
                    {groupAgents
                      .sort(
                        (a, b) => Date.parse(b.created_at ?? '') - Date.parse(a.created_at ?? '')
                      )
                      .map((agent) => (
                        <AgentCard key={agent.id} agent={agent} />
                      ))}
                  </Flex>
                </CardBody>
              </Card>
            </FlexItem>
          ))}
        </Flex>
      )}
    </div>
  );
}

function groupAgentsBySuite(
  agents: Agent[]
): { suiteId: string | undefined; suiteName: string | undefined; agents: Agent[] }[] {
  const groups = new Map<
    string,
    { suiteId: string | undefined; suiteName: string | undefined; agents: Agent[] }
  >();
  for (const agent of agents) {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    const key: string = agent.suite_id ?? '__uncategorized__';
    const existing:
      | { suiteId: string | undefined; suiteName: string | undefined; agents: Agent[] }
      | undefined = groups.get(key);
    if (existing) {
      const updated: {
        suiteId: string | undefined;
        suiteName: string | undefined;
        agents: Agent[];
      } = {
        suiteId: existing.suiteId,
        suiteName: existing.suiteName,
        agents: [...existing.agents, agent],
      };
      groups.set(key, updated);
    } else {
      const created: {
        suiteId: string | undefined;
        suiteName: string | undefined;
        agents: Agent[];
      } = {
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
        suiteId: agent.suite_id ?? undefined,
        // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
        suiteName: agent.suite_name ?? undefined,
        agents: [agent],
      };
      groups.set(key, created);
    }
  }
  const result: {
    suiteId: string | undefined;
    suiteName: string | undefined;
    agents: Agent[];
  }[] = Array.from(groups.values());
  return result;
}
