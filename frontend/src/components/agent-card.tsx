import { Agent } from '@/types/agent';
import {
  Button,
  Card,
  CardBody,
  CardExpandableContent,
  CardHeader,
  CardTitle,
  Tooltip,
  Dropdown,
  DropdownItem,
  DropdownList,
  Flex,
  FlexItem,
  Icon,
  Label,
  MenuToggle,
  MenuToggleElement,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  Title,
} from '@patternfly/react-core';
import { EllipsisVIcon, TrashIcon } from '@patternfly/react-icons';
import { useAgents, useTools } from '@/hooks';
import { Fragment, useState } from 'react';
import { useNavigate } from '@tanstack/react-router';

interface AgentCardProps {
  agent: Agent;
  isAssigned?: boolean;
}

export function AgentCard({ agent, isAssigned }: AgentCardProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);

  // Use custom hooks
  const { tools } = useTools();
  const { deleteAgent, isDeleting } = useAgents();
  const navigate = useNavigate();
  const isAssignedToUser: boolean = !!isAssigned;

  const handleDeleteAgent = () => {
    void (async () => {
      try {
        await deleteAgent(agent.id);
        setModalOpen(false);
        console.log('Agent deleted successfully');
      } catch (error) {
        console.error('Error deleting agent:', error);
      }
    })();
  };

  const toggleModal = () => {
    setModalOpen(!modalOpen);
  };
  const toggleDropdown = () => {
    setDropdownOpen(!dropdownOpen);
  };

  const toggleExpanded = () => {
    setExpanded(!expanded);
  };

  const handleChatClick = () => {
    if (!isAssignedToUser) return;
    void navigate({ to: '/', search: { agentId: agent.id } });
  };

  const headerActions = (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      {!isAssignedToUser ? (
        <Tooltip content="This agent isn't assigned to you. Assign it to chat.">
          <span style={{ display: 'inline-block' }}>
            <Button
              variant="primary"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                handleChatClick();
              }}
              aria-label="Chat with agent"
              isDisabled
            >
              Chat
            </Button>
          </span>
        </Tooltip>
      ) : (
        <Button
          variant="primary"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            handleChatClick();
          }}
          aria-label="Chat with agent"
        >
          Chat
        </Button>
      )}
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
              toggleDropdown();
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
        <DropdownList>
          <DropdownItem
            isDanger
            onClick={() => {
              toggleModal();
              toggleDropdown();
            }}
            icon={<TrashIcon />}
            value={1}
            key="delete"
          >
            Delete
          </DropdownItem>
        </DropdownList>
      </Dropdown>
    </div>
  );
  return (
    <Card id={`expandable-agent-card-${agent.id}`} isExpanded={expanded} className="pf-v6-u-mb-md">
      <Fragment>
        <CardHeader
          actions={{ actions: headerActions, hasNoOffset: true }}
          onExpand={toggleExpanded}
          toggleButtonProps={{
            id: `toggle-agent-button-${agent.id}`,
            'aria-label': 'Details',
            'aria-labelledby': `expandable-agent-title-${agent.id} toggle-agent-button-${agent.id}`,
            'aria-expanded': expanded,
          }}
        >
          <CardTitle id={`expandable-agent-title-${agent.id}`}>
            <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
              <FlexItem>
                <Title className="pf-v6-u-mb-0" headingLevel="h2">
                  {agent.name}
                </Title>
              </FlexItem>
              <FlexItem>
                <Title className="pf-v6-u-text-color-subtle pf-v6-u-mb-0" headingLevel="h5">
                  {agent.model_name}
                </Title>
              </FlexItem>
            </Flex>
          </CardTitle>
        </CardHeader>
        <Modal
          isOpen={modalOpen}
          onClose={toggleModal}
          variant="small"
          aria-labelledby="delete-agent-modal-title"
          aria-describedby="delete-agent-modal-desc"
        >
          <ModalHeader title="Delete Agent" labelId="delete-agent-modal-title" />
          <ModalBody id="delete-agent-modal-desc">
            Are you sure you want to delete this AI agent? This action cannot be undone.
          </ModalBody>
          <ModalFooter className="pf-v6-u-justify-content-flex-end">
            <Button variant="link" onClick={toggleModal}>
              Cancel
            </Button>
            <Button isLoading={isDeleting} onClick={handleDeleteAgent} variant="danger">
              Delete
            </Button>
          </ModalFooter>
        </Modal>
        <CardExpandableContent>
          <CardBody>
            <Flex direction={{ default: 'column' }}>
              <FlexItem>
                <span className="pf-v6-u-text-color-subtle">Prompt: </span>
                {agent.prompt}
              </FlexItem>
              <FlexItem>
                <Flex gap={{ default: 'gapSm' }}>
                  <FlexItem>
                    <span className="pf-v6-u-text-color-subtle">Knowledge Bases: </span>
                  </FlexItem>

                  {agent.knowledge_base_ids.length > 0
                    ? agent.knowledge_base_ids.map((kb, index) => (
                        <FlexItem key={index}>
                          <Label color="blue">{kb}</Label>
                        </FlexItem>
                      ))
                    : 'None'}
                </Flex>
              </FlexItem>
              <FlexItem>
                <Flex gap={{ default: 'gapSm' }}>
                  <FlexItem>
                    <span className="pf-v6-u-text-color-subtle">Tool Groups: </span>
                  </FlexItem>
                  {agent.tools.length > 0
                    ? agent.tools.map((tool, index) => {
                        // Find the tool group name from the tools data
                        const toolGroup = tools?.find((t) => t.toolgroup_id === tool.toolgroup_id);
                        const displayName = toolGroup?.name || tool.toolgroup_id;
                        return (
                          <FlexItem key={index}>
                            <Label color="orange">{displayName}</Label>
                          </FlexItem>
                        );
                      })
                    : 'None'}
                </Flex>
              </FlexItem>
              <FlexItem>
                <Flex gap={{ default: 'gapSm' }}>
                  <FlexItem>
                    <span className="pf-v6-u-text-color-subtle">Input Shields: </span>
                  </FlexItem>
                  {agent.input_shields.length > 0
                    ? agent.input_shields.map((shield, index) => (
                        <FlexItem key={index}>
                          <Label color="green">{shield}</Label>
                        </FlexItem>
                      ))
                    : 'None'}
                </Flex>
              </FlexItem>
              <FlexItem>
                <Flex gap={{ default: 'gapSm' }}>
                  <FlexItem>
                    <span className="pf-v6-u-text-color-subtle">Output Shields: </span>
                  </FlexItem>
                  {agent.output_shields.length > 0
                    ? agent.output_shields.map((shield, index) => (
                        <FlexItem key={index}>
                          <Label color="purple">{shield}</Label>
                        </FlexItem>
                      ))
                    : 'None'}
                </Flex>
              </FlexItem>
            </Flex>
          </CardBody>
        </CardExpandableContent>
      </Fragment>
    </Card>
  );
}
