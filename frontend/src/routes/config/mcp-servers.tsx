import { 
  PageSection, 
  Title, 
  Card, 
  CardBody, 
  CardHeader, 
  CardTitle,
  DescriptionList,
  DescriptionListDescription,
  DescriptionListGroup,
  DescriptionListTerm,
  Badge,
  Alert,
  Spinner,
  EmptyState,
  EmptyStateBody
} from '@patternfly/react-core';
import { ServerIcon } from '@patternfly/react-icons';
import { createFileRoute } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { fetchTools } from '@/services/tools';
import { ToolGroup } from '@/types';

export const Route = createFileRoute('/config/mcp-servers')({
  component: MCPServers,
});

function MCPServers() {
  const {
    data: tools,
    isLoading,
    error,
  } = useQuery<ToolGroup[], Error>({
    queryKey: ['mcp-servers'],
    queryFn: fetchTools,
  });

  // Filter for MCP servers only
  const mcpServers = tools?.filter((tool) => tool.provider_id === 'model-context-protocol') || [];

  if (isLoading) {
    return (
      <PageSection hasBodyWrapper={false}>
        <Title headingLevel="h1">MCP Servers</Title>
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <Spinner size="lg" />
          <p>Loading MCP servers...</p>
        </div>
      </PageSection>
    );
  }

  if (error) {
    return (
      <PageSection hasBodyWrapper={false}>
        <Title headingLevel="h1">MCP Servers</Title>
        <Alert variant="danger" title="Error loading MCP servers">
          {error.message}
        </Alert>
      </PageSection>
    );
  }

  return (
    <PageSection hasBodyWrapper={false}>
      <Title headingLevel="h1">MCP Servers</Title>
      
      {mcpServers.length === 0 ? (
        <EmptyState>
          <div style={{ textAlign: 'center', padding: '2rem' }}>
            <ServerIcon style={{ marginBottom: '1rem', fontSize: '2rem' }} />
            <Title headingLevel="h2">No MCP Servers Found</Title>
            <EmptyStateBody>
              No Model Context Protocol (MCP) servers are currently registered with LlamaStack.
            </EmptyStateBody>
          </div>
        </EmptyState>
      ) : (
        <div style={{ display: 'grid', gap: '1rem', marginTop: '1rem' }}>
          {mcpServers.map((server) => (
            <Card key={server.identifier}>
              <CardHeader>
                <CardTitle>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <ServerIcon />
                    {server.provider_resource_id}
                    <Badge isRead>{server.type}</Badge>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardBody>
                <DescriptionList>
                  <DescriptionListGroup>
                    <DescriptionListTerm>Identifier</DescriptionListTerm>
                    <DescriptionListDescription>
                      <code>{server.identifier}</code>
                    </DescriptionListDescription>
                  </DescriptionListGroup>
                  
                  <DescriptionListGroup>
                    <DescriptionListTerm>Provider ID</DescriptionListTerm>
                    <DescriptionListDescription>
                      {server.provider_id}
                    </DescriptionListDescription>
                  </DescriptionListGroup>
                  
                  {server.mcp_endpoint && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>MCP Endpoint</DescriptionListTerm>
                      <DescriptionListDescription>
                        <code>
                          {typeof server.mcp_endpoint === 'string' 
                            ? server.mcp_endpoint 
                            : JSON.stringify(server.mcp_endpoint)
                          }
                        </code>
                      </DescriptionListDescription>
                    </DescriptionListGroup>
                  )}
                  
                  {server.args && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>Arguments</DescriptionListTerm>
                      <DescriptionListDescription>
                        <code>{JSON.stringify(server.args, null, 2)}</code>
                      </DescriptionListDescription>
                    </DescriptionListGroup>
                  )}
                </DescriptionList>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </PageSection>
  );
}
