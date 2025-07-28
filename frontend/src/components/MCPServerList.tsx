import { fetchMCPServers, deleteMCPServer } from '@/services/mcp-servers';
import { MCPServer } from '@/types';
import { Alert, Button, Flex, FlexItem, Spinner, Title } from '@patternfly/react-core';
import { SyncIcon } from '@patternfly/react-icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import React, { useState } from 'react';
import { NewMCPServerCard } from '@/components/NewMCPServerCard';
import { MCPServerCard } from '@/components/MCPServerCard';

export function MCPServerList() {
  const queryClient = useQueryClient();
  const [lastFetchTime, setLastFetchTime] = useState<string>('');
  const [editingServer, setEditingServer] = useState<MCPServer | null>(null);

  // Query for MCP Servers
  const {
    data: mcpServers,
    isLoading: isLoadingServers,
    error: serversError,
    dataUpdatedAt,
  } = useQuery<MCPServer[], Error>({
    queryKey: ['mcpServers'],
    queryFn: fetchMCPServers,
  });

  // Update timestamp when data is fetched
  React.useEffect(() => {
    if (dataUpdatedAt) {
      setLastFetchTime(new Date(dataUpdatedAt).toLocaleString());
    }
  }, [dataUpdatedAt]);

  // Delete MCP server mutation
  const deleteMCPServerMutation = useMutation({
    mutationFn: deleteMCPServer,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['mcpServers'] });
      console.log('MCP server deleted successfully');
    },
    onError: (error) => {
      console.error('Error deleting MCP server:', error);
    },
  });

  const handleDeleteServer = (toolgroup_id: string) => {
    deleteMCPServerMutation.mutate(toolgroup_id);
  };

  const handleEditServer = (server: MCPServer) => {
    setEditingServer(server);
  };

  const handleRefresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['mcpServers'] });
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
                isDeleting={deleteMCPServerMutation.isPending}
              />
            ))}
        {!isLoadingServers &&
          !serversError &&
          mcpServers &&
          mcpServers.length === 0 && <p>No MCP servers configured yet.</p>}
      </Flex>
    </div>
  );
}