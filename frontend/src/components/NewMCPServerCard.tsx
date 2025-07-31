import { MCPServer, MCPServerCreate } from '@/types';
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
import { useMCPServers } from '@/hooks';

interface NewMCPServerCardProps {
  editingServer?: MCPServer | null;
  onEditComplete?: () => void;
}

export function NewMCPServerCard({ editingServer, onEditComplete }: NewMCPServerCardProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Use custom hook
  const { createMCPServer, updateMCPServer, isCreating, isUpdating, createError, updateError } =
    useMCPServers();

  // Open card when editing server is set
  useEffect(() => {
    if (editingServer) {
      setIsOpen(true);
    }
  }, [editingServer]);

  const handleSubmit = (values: MCPServerCreate) => {
    void (async () => {
      try {
        if (editingServer) {
          // Update existing server
          await updateMCPServer(editingServer.toolgroup_id, values);
          console.log('MCP server updated successfully');
          onEditComplete?.();
        } else {
          // Create new server
          await createMCPServer(values);
          console.log('MCP server created successfully');
        }
        setIsOpen(false);
      } catch (error) {
        console.error('Error with MCP server operation:', error);
      }
    })();
  };

  const handleCancel = () => {
    setIsOpen(false);
    onEditComplete?.();
  };

  const isSubmitting = isCreating || isUpdating;
  const error = createError || updateError;

  return (
    <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
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
                          ? 'Failed to update MCP server'
                          : 'Failed to create MCP server'
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
