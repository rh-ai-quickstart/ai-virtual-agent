import { MCPServer, MCPServerCreate } from '@/types';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  CardBody,
  CardExpandableContent,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  Title,
  Alert,
} from '@patternfly/react-core';
import { PlusIcon } from '@patternfly/react-icons';
import { useState, useEffect } from 'react';
import { MCPServerForm } from './MCPServerForm';
import { createMCPServer, updateMCPServer } from '@/services/mcp-servers';

interface NewMCPServerCardProps {
  editingServer?: MCPServer | null;
  onEditComplete?: () => void;
}

export function NewMCPServerCard({ 
  editingServer, 
  onEditComplete 
}: NewMCPServerCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const queryClient = useQueryClient();

  // Open card when editing server is set
  useEffect(() => {
    if (editingServer) {
      setIsOpen(true);
    }
  }, [editingServer]);

  // Create MCP server mutation
  const createMutation = useMutation<MCPServer, Error, MCPServerCreate>({
    mutationFn: createMCPServer,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['mcpServers'] });
      setIsOpen(false);
      console.log('MCP server created successfully');
    },
    onError: (error) => {
      console.error('Error creating MCP server:', error);
    },
  });

  // Update MCP server mutation
  const updateMutation = useMutation<
    MCPServer, 
    Error, 
    { toolgroup_id: string; serverUpdate: MCPServerCreate }
  >({
    mutationFn: ({ toolgroup_id, serverUpdate }) => 
      updateMCPServer(toolgroup_id, serverUpdate),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['mcpServers'] });
      setIsOpen(false);
      onEditComplete?.();
      console.log('MCP server updated successfully');
    },
    onError: (error) => {
      console.error('Error updating MCP server:', error);
    },
  });

  const handleSubmit = (values: MCPServerCreate) => {
    if (editingServer) {
      // Update existing server
      updateMutation.mutate({
        toolgroup_id: editingServer.toolgroup_id,
        serverUpdate: values,
      });
    } else {
      // Create new server
      createMutation.mutate(values);
    }
  };

  const handleCancel = () => {
    setIsOpen(false);
    onEditComplete?.();
    // Reset mutations
    createMutation.reset();
    updateMutation.reset();
  };

  const isSubmitting = createMutation.isPending || updateMutation.isPending;
  const error = createMutation.error || updateMutation.error;
  const isSuccess = createMutation.isSuccess || updateMutation.isSuccess;

  return (
    <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
      {isSuccess && (
        <FlexItem>
          <Alert
            timeout={5000}
            variant="success"
            title={
              editingServer 
                ? "MCP server updated successfully!" 
                : "MCP server created successfully!"
            }
            className="pf-v6-u-mb-sm"
          />
        </FlexItem>
      )}
      <FlexItem>
        <Card isExpanded={isOpen} isClickable={!isOpen}>
          <CardHeader
            selectableActions={{
              onClickAction: () => setIsOpen(!isOpen),
              selectableActionAriaLabelledby: 'clickable-mcp-card-title-1',
            }}
          >
            <CardTitle>
              {!isOpen ? (
                <Flex>
                  <FlexItem>
                    <PlusIcon />
                  </FlexItem>
                  <FlexItem>
                    <Title headingLevel="h3">
                      {editingServer ? `Edit ${editingServer.name}` : 'New MCP Server'}
                    </Title>
                  </FlexItem>
                </Flex>
              ) : (
                <Title headingLevel="h3">
                  {editingServer ? `Edit ${editingServer.name}` : 'New MCP Server'}
                </Title>
              )}
            </CardTitle>
          </CardHeader>
          <CardExpandableContent>
            <CardBody>
              <Flex direction={{ default: 'column' }} gap={{ default: 'gapLg' }}>
                <FlexItem>
                  <MCPServerForm
                    defaultServer={editingServer || undefined}
                    isSubmitting={isSubmitting}
                    onSubmit={handleSubmit}
                    onCancel={handleCancel}
                    error={error}
                  />
                </FlexItem>
                {error && (
                  <FlexItem>
                    <Alert
                      variant="danger"
                      title={
                        editingServer 
                          ? "Failed to update MCP server" 
                          : "Failed to create MCP server"
                      }
                      className="pf-v6-u-mt-md"
                    >
                      {error?.message || 'An unexpected error occurred.'}
                    </Alert>
                  </FlexItem>
                )}
              </Flex>
            </CardBody>
          </CardExpandableContent>
        </Card>
      </FlexItem>
    </Flex>
  );
}