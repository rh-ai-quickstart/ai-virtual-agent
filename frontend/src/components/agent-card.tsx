import { Agent } from '@/routes/config/agents';
import { deleteAgent } from '@/services/agents';
import {
  Button,
  Card,
  CardBody,
  CardExpandableContent,
  CardHeader,
  CardTitle,
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
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Fragment, useState } from 'react';
import { fetchTools } from '@/services/tools';
import { ToolGroup } from '@/types';

interface AgentCardProps {
  agent: Agent;
}

export function AgentCard({ agent }: AgentCardProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const queryClient = useQueryClient();

  // Query for tools
  const { data: tools } = useQuery<ToolGroup[], Error>({
    queryKey: ['tools'],
    queryFn: fetchTools,
  });

  // Mutation for deleting an Agent
  const deleteAgentMutation = useMutation<void, Error, string>({
    mutationFn: deleteAgent,
    onSuccess: () => {
      // Invalidate and refetch the agents list to show the new agent
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
      setModalOpen(false);
      console.log('Agent deleted successfully');
    },
    onError: (error) => {
      console.error('Error deleting agent:', error);
      // Optionally show an error message
    },
  });

  const handleDeleteAgent = () => {
    deleteAgentMutation.mutate(agent.id);
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
        <ModalFooter>
          <Button variant="link" onClick={toggleModal}>
            Cancel
          </Button>
          <Button
            isLoading={deleteAgentMutation.isPending}
            onClick={handleDeleteAgent}
            variant="danger"
          >
            Delete
          </Button>
        </ModalFooter>
      </Modal>
    </Fragment>
  );
  return (
    <Card id={`expandable-agent-card-${agent.id}`} isExpanded={expanded} className="pf-v6-u-mb-md">
      <Fragment>
        <CardHeader
          actions={{ actions: headerActions }}
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
            </Flex>
          </CardBody>
        </CardExpandableContent>
      </Fragment>
    </Card>
  );
}
