import { MCPServer } from '@/types';
import { Alert, Button, Flex, FlexItem, Spinner, Title } from '@patternfly/react-core';
import { SyncIcon } from '@patternfly/react-icons';
import { useMCPServers } from '@/hooks';
import React, { useState } from 'react';
import { NewMCPServerCard } from '@/components/NewMCPServerCard';
import { MCPServerCard } from '@/components/MCPServerCard';
import { useQueryClient } from '@tanstack/react-query';

export function MCPServerList() {
  const queryClient = useQueryClient();
  const [lastFetchTime, setLastFetchTime] = useState<string>('');
  const [editingServer, setEditingServer] = useState<MCPServer | null>(null);

  // Use custom MCP servers hook
  const {
    mcpServers,
    isLoading: isLoadingServers,
    error: serversError,
    deleteMCPServer,
    isDeleting,
    refreshMCPServers,
  } = useMCPServers();

  // Get dataUpdatedAt from the underlying query for timestamp tracking
  const { dataUpdatedAt } = queryClient.getQueryState(['mcpServers']) || {};

  // Update timestamp when data is fetched
  React.useEffect(() => {
    if (dataUpdatedAt) {
      setLastFetchTime(new Date(dataUpdatedAt).toLocaleString());
    }
  }, [dataUpdatedAt]);

  const handleDeleteServer = (toolgroup_id: string) => {
    void (async () => {
      try {
        await deleteMCPServer(toolgroup_id);
        console.log('MCP server deleted successfully');
      } catch (error) {
        console.error('Error deleting MCP server:', error);
      }
    })();
  };

  const handleEditServer = (server: MCPServer) => {
    setEditingServer(server);
  };

  const handleRefresh = () => {
    refreshMCPServers();
  };

  return (
    <div>
      {/* Header with title, refresh button, and timestamp */}
      <Flex
        justifyContent={{ default: 'justifyContentSpaceBetween' }}
        alignItems={{ default: 'alignItemsCenter' }}
        className="pf-v6-u-mb-md"
      >
        <FlexItem>
          <Title headingLevel="h2">MCP Servers</Title>
        </FlexItem>
        <FlexItem>
          <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
            {lastFetchTime && (
              <FlexItem>
                <span className="pf-v6-u-text-color-subtle pf-v6-u-font-size-sm">
                  Last updated: {lastFetchTime}
                </span>
              </FlexItem>
            )}
            <FlexItem>
              <Button
                variant="plain"
                icon={<SyncIcon />}
                onClick={handleRefresh}
                isLoading={isLoadingServers}
                aria-label="Refresh MCP servers"
              >
                Refresh
              </Button>
            </FlexItem>
          </Flex>
        </FlexItem>
      </Flex>

      {/* Content */}
      {isLoadingServers && <Spinner aria-label="Loading MCP servers" />}
      {serversError && (
        <Alert variant="danger" title="Error loading MCP servers">
          {serversError.message}
        </Alert>
      )}
      <Flex direction={{ default: 'column' }}>
        <FlexItem>
          <NewMCPServerCard
            editingServer={editingServer}
            onEditComplete={() => setEditingServer(null)}
          />
        </FlexItem>
        {!isLoadingServers &&
          !serversError &&
          mcpServers &&
          mcpServers.length > 0 &&
          mcpServers
            .sort((a, b) => Date.parse(b.created_at ?? '') - Date.parse(a.created_at ?? ''))
            .map((server) => (
              <MCPServerCard
                key={server.toolgroup_id}
                mcpServer={server}
                onDelete={handleDeleteServer}
                onEdit={handleEditServer}
                isDeleting={isDeleting}
              />
            ))}
        {!isLoadingServers && !serversError && mcpServers && mcpServers.length === 0 && (
          <p>No MCP servers configured yet.</p>
        )}
      </Flex>
    </div>
  );
}
