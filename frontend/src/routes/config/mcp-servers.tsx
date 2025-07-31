import { PageSection } from '@patternfly/react-core';
import { createFileRoute } from '@tanstack/react-router';
import { MCPServerList } from '@/components/MCPServerList';

export const Route = createFileRoute('/config/mcp-servers')({
  component: MCPServers,
});

function MCPServers() {
  return (
    <PageSection hasBodyWrapper={false}>
      <MCPServerList />
    </PageSection>
  );
}
