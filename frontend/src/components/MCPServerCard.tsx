import {
  Card,
  CardHeader,
  CardTitle,
  CardBody,
  CardExpandableContent,
  Dropdown,
  DropdownList,
  DropdownItem,
  MenuToggle,
  MenuToggleElement,
  Title,
  Flex,
  FlexItem,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Button,
  Icon,
} from '@patternfly/react-core';
import { EllipsisVIcon, TrashIcon, EditIcon } from '@patternfly/react-icons';
import { useState, Fragment } from 'react';
import { MCPServer } from '@/types';

interface MCPServerCardProps {
  mcpServer: MCPServer;
  onDelete?: (toolgroup_id: string) => void;
  onEdit?: (mcpServer: MCPServer) => void;
  isDeleting?: boolean;
}

export function MCPServerCard({
  mcpServer,
  onDelete,
  onEdit,
  isDeleting = false,
}: MCPServerCardProps) {
  const [dropdownOpen, setDropdownOpen] = useState<boolean>(false);
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [modalOpen, setModalOpen] = useState<boolean>(false);

  const onExpand = () => setIsExpanded(!isExpanded);

  const toggleModal = () => {
    setModalOpen(!modalOpen);
  };

  const handleDeleteServer = () => {
    onDelete?.(mcpServer.toolgroup_id);
  };

  const handleEditServer = () => {
    onEdit?.(mcpServer);
    setDropdownOpen(false);
  };

  const dropdownItems = (
    <>
      <DropdownItem
        icon={<EditIcon />}
        value={0}
        key="edit"
        onClick={handleEditServer}
      >
        Edit
      </DropdownItem>
      <DropdownItem
        isDanger
        icon={<TrashIcon />}
        value={1}
        key="delete"
        onClick={() => {
          toggleModal();
          setDropdownOpen(false);
        }}
      >
        Delete
      </DropdownItem>
    </>
  );

  const headerActions = (
    <Fragment>
      <Dropdown
        isOpen={dropdownOpen}
        onOpenChange={(isOpen: boolean) => setDropdownOpen(isOpen)}
        toggle={(toggleRef: React.Ref<MenuToggleElement>) => (
          <MenuToggle
            ref={toggleRef}
            aria-label="kebab dropdown toggle"
            variant="plain"
            onClick={(e) => {
              e.stopPropagation(); // Prevent header click
              setDropdownOpen(!dropdownOpen);
            }}
            isExpanded={dropdownOpen}
            icon={
              <Icon iconSize="lg">
                <EllipsisVIcon />
              </Icon>
            }
          />
        )}
        shouldFocusToggleOnSelect
        popperProps={{ position: 'right' }}
      >
        <DropdownList>{dropdownItems}</DropdownList>
      </Dropdown>
      <Modal
        isOpen={modalOpen}
        onClose={toggleModal}
        variant="small"
        aria-labelledby="delete-mcp-modal-title"
        aria-describedby="delete-mcp-modal-desc"
      >
        <ModalHeader title="Delete MCP Server" labelId="delete-mcp-modal-title" />
        <ModalBody id="delete-mcp-modal-desc">
          Are you sure you want to delete this MCP server? This action cannot be undone.
        </ModalBody>
        <ModalFooter>
          <Button isLoading={isDeleting} onClick={handleDeleteServer} variant="danger">
            Delete
          </Button>
          <Button variant="link" onClick={toggleModal}>
            Cancel
          </Button>
        </ModalFooter>
      </Modal>
    </Fragment>
  );

  return (
    <Card
      id={`expandable-mcp-card-${mcpServer.toolgroup_id}`}
      isExpanded={isExpanded}
      className="pf-v6-u-mb-md"
    >
      <CardHeader
        actions={{ actions: headerActions }}
        onExpand={onExpand}
        toggleButtonProps={{
          id: `toggle-mcp-button-${mcpServer.toolgroup_id}`,
          'aria-label': 'Details',
          'aria-labelledby': `expandable-mcp-title-${mcpServer.toolgroup_id} toggle-mcp-button-${mcpServer.toolgroup_id}`,
          'aria-expanded': isExpanded,
        }}
      >
        <CardTitle id={`expandable-mcp-title-${mcpServer.toolgroup_id}`}>
          <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
            <FlexItem>
              <Title className="pf-v6-u-mb-0" headingLevel="h2">
                {mcpServer.name}
              </Title>
            </FlexItem>
            {mcpServer.description && (
              <FlexItem>
                <Title className="pf-v6-u-text-color-subtle pf-v6-u-mb-0" headingLevel="h5">
                  {mcpServer.description}
                </Title>
              </FlexItem>
            )}
          </Flex>
        </CardTitle>
      </CardHeader>
      <CardExpandableContent>
        <CardBody>
          <Flex direction={{ default: 'column' }}>
            <FlexItem>
              <span className="pf-v6-u-text-color-subtle">Endpoint URL: </span>
              {mcpServer.endpoint_url}
            </FlexItem>
            <FlexItem>
              <span className="pf-v6-u-text-color-subtle">Tool Group ID: </span>
              {mcpServer.toolgroup_id}
            </FlexItem>
            {mcpServer.configuration && (
              <FlexItem>
                <span className="pf-v6-u-text-color-subtle">Configuration: </span>
                <pre className="pf-v6-u-font-size-sm pf-v6-u-mt-xs">
                  {JSON.stringify(mcpServer.configuration, null, 2)}
                </pre>
              </FlexItem>
            )}
            {mcpServer.created_at && (
              <FlexItem>
                <span className="pf-v6-u-text-color-subtle">Created: </span>
                {new Date(mcpServer.created_at).toLocaleString()}
              </FlexItem>
            )}
          </Flex>
        </CardBody>
      </CardExpandableContent>
    </Card>
  );
}