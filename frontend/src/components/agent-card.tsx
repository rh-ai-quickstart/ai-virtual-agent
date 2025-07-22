import { Agent } from '@/routes/config/agents';
import { deleteAgent } from '@/services/agents';
import { personaStorage } from '@/services/persona-storage';
import { personaService, PersonaConfig } from '@/services/personas';
import {
  Button,
  Card,
  CardBody,
  CardTitle,
  Dropdown,
  DropdownItem,
  DropdownList,
  Flex,
  FlexItem,
  Icon,
  MenuToggle,
  MenuToggleElement,
  Modal,
  ModalBody,
  ModalFooter,
  ModalHeader,
  Title,
  CardHeader,
} from '@patternfly/react-core';
import { EllipsisVIcon, TrashIcon, PlayIcon } from '@patternfly/react-icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import React, { Fragment, useState, useEffect } from 'react';
import { Link } from '@tanstack/react-router';

interface AgentCardProps {
  agent: Agent;
}

export function AgentCard({ agent }: AgentCardProps) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [personaConfig, setPersonaConfig] = useState<PersonaConfig | null>(null);
  // const [showPersonaModal, setShowPersonaModal] = useState(false);
  // const [selectedPersona, setSelectedPersona] = useState('');

  const queryClient = useQueryClient();

  // Query for tools
  // const { data: tools } = useQuery<ToolGroup[], Error>({
  //   queryKey: ['tools'],
  //   queryFn: fetchTools,
  // });

  // Get persona from localStorage and load config
  const agentPersona = personaStorage.getPersona(agent.id);

  useEffect(() => {
    if (agentPersona) {
      const config = personaService.getPersona(agentPersona);
      setPersonaConfig(config);
    }
  }, [agentPersona]);

  // Calculate agent stats with safe date handling
  const toolCount = agent.tools?.length || 0;
  const knowledgeBaseCount = agent.knowledge_base_ids?.length || 0;

  // Safe date parsing with fallback
  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return isNaN(date.getTime()) ? 'N/A' : date.toLocaleDateString();
    } catch {
      return 'N/A';
    }
  };

  const createdDate = formatDate(agent.created_at);
  // const updatedDate = formatDate(agent.updated_at);
  const isActive = true; // You can add actual status logic here

  // Mutation for deleting an Agent
  const deleteAgentMutation = useMutation<void, Error, string>({
    mutationFn: deleteAgent,
    onSuccess: () => {
      personaStorage.removePersona(agent.id);
      void queryClient.invalidateQueries({ queryKey: ['agents'] });
      setModalOpen(false);
    },
    onError: (error) => {
      console.error('Error deleting agent:', error);
    },
  });

  const handleDeleteAgent = () => {
    deleteAgentMutation.mutate(agent.id);
  };

  const toggleModal = () => setModalOpen(!modalOpen);
  const toggleDropdown = () => setDropdownOpen(!dropdownOpen);

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
              e.stopPropagation();
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
    <Card
      className={`agent-card ${personaConfig?.className || 'persona-default'}`}
      style={{
        marginBottom: '0.5rem',
        border: personaConfig ? `2px solid ${personaConfig.borderColor}` : undefined,
        width: '280px', // Better size for catalog view
        height: '200px', // Good height for content
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <CardHeader actions={{ actions: headerActions }} style={{ padding: '0.75rem' }}>
        <CardTitle>
          <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapMd' }}>
            {/* Agent Avatar */}
            <div
              className="agent-avatar"
              style={{
                backgroundColor: personaConfig?.avatarBg || '#6b7280',
                width: '32px',
                height: '32px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '14px',
                flexShrink: 0,
              }}
            >
              {personaConfig?.avatarIcon || '🤖'}
            </div>

            {/* Agent Info */}
            <FlexItem flex={{ default: 'flex_1' }}>
              <Flex direction={{ default: 'column' }} gap={{ default: 'gapSm' }}>
                <FlexItem>
                  <Title
                    headingLevel="h3"
                    size="lg"
                    style={{ margin: 0, fontSize: '0.9rem', lineHeight: '1.3' }}
                  >
                    {agent.name.length > 25 ? `${agent.name.substring(0, 25)}...` : agent.name}
                  </Title>
                </FlexItem>

                <FlexItem>
                  <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
                    <span
                      className={`status-indicator ${isActive ? 'status-active' : 'status-inactive'}`}
                      style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        backgroundColor: isActive ? '#52c41a' : '#d9d9d9',
                        display: 'inline-block',
                      }}
                    />
                    <small style={{ color: 'var(--pf-v6-global--Color--200)', fontSize: '0.7rem' }}>
                      {isActive ? 'Active' : 'Inactive'}
                    </small>
                    {personaConfig && (
                      <>
                        <span style={{ color: 'var(--pf-v6-global--Color--200)' }}>•</span>
                        <span
                          style={{
                            color: personaConfig.color,
                            fontSize: '0.6rem',
                            border: `1px solid ${personaConfig.color}`,
                            borderRadius: '4px',
                            padding: '2px 6px',
                            backgroundColor: 'transparent',
                          }}
                        >
                          {personaConfig.label}
                        </span>
                      </>
                    )}
                  </Flex>
                </FlexItem>
              </Flex>
            </FlexItem>
          </Flex>
        </CardTitle>
      </CardHeader>

      <CardBody style={{ flex: 1, padding: '0.75rem', overflow: 'hidden' }}>
        <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
          {/* Agent Description */}
          <FlexItem>
            <p
              style={{
                color: 'var(--pf-v6-global--Color--200)',
                margin: 0,
                lineHeight: '1.4',
                fontSize: '0.7rem',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
                overflow: 'hidden',
              }}
            >
              {agent.prompt.length > 100 ? `${agent.prompt.substring(0, 100)}...` : agent.prompt}
            </p>
          </FlexItem>

          {/* Agent Stats */}
          <FlexItem>
            <div
              className="agent-stats"
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(2, 1fr)',
                gap: '0.5rem',
                marginTop: '0.5rem',
              }}
            >
              <div className="agent-stat" style={{ textAlign: 'center' }}>
                <div
                  className="agent-stat-value"
                  style={{
                    fontSize: '0.9rem',
                    fontWeight: 'bold',
                    color: 'var(--pf-v6-global--Color--100)',
                  }}
                >
                  {toolCount}
                </div>
                <div
                  className="agent-stat-label"
                  style={{
                    fontSize: '0.6rem',
                    color: 'var(--pf-v6-global--Color--200)',
                  }}
                >
                  Tools
                </div>
              </div>
              <div className="agent-stat" style={{ textAlign: 'center' }}>
                <div
                  className="agent-stat-value"
                  style={{
                    fontSize: '0.9rem',
                    fontWeight: 'bold',
                    color: 'var(--pf-v6-global--Color--100)',
                  }}
                >
                  {knowledgeBaseCount}
                </div>
                <div
                  className="agent-stat-label"
                  style={{
                    fontSize: '0.6rem',
                    color: 'var(--pf-v6-global--Color--200)',
                  }}
                >
                  KB
                </div>
              </div>
              <div className="agent-stat" style={{ textAlign: 'center' }}>
                <div
                  className="agent-stat-value"
                  style={{
                    fontSize: '0.7rem',
                    fontWeight: 'bold',
                    color: 'var(--pf-v6-global--Color--100)',
                  }}
                >
                  {agent.model_name.split('/').pop()}
                </div>
                <div
                  className="agent-stat-label"
                  style={{
                    fontSize: '0.6rem',
                    color: 'var(--pf-v6-global--Color--200)',
                  }}
                >
                  Model
                </div>
              </div>
              <div className="agent-stat" style={{ textAlign: 'center' }}>
                <div
                  className="agent-stat-value"
                  style={{
                    fontSize: '0.7rem',
                    fontWeight: 'bold',
                    color: 'var(--pf-v6-global--Color--100)',
                  }}
                >
                  {createdDate}
                </div>
                <div
                  className="agent-stat-label"
                  style={{
                    fontSize: '0.6rem',
                    color: 'var(--pf-v6-global--Color--200)',
                  }}
                >
                  Created
                </div>
              </div>
            </div>
          </FlexItem>
        </Flex>
      </CardBody>

      {/* Card Footer with Actions */}
      <div
        className="agent-card-footer"
        style={{
          padding: '0.75rem',
          borderTop: '1px solid var(--pf-v6-global--BorderColor--100)',
          marginTop: 'auto',
        }}
      >
        <Flex
          justifyContent={{ default: 'justifyContentSpaceBetween' }}
          alignItems={{ default: 'alignItemsCenter' }}
        >
          <FlexItem>
            <small
              style={{
                color: 'var(--pf-v6-global--Color--200)',
                fontSize: '0.6rem',
              }}
            >
              {agent.created_by || 'System'}
            </small>
          </FlexItem>
          <FlexItem>
            <Button
              variant="primary"
              size="sm"
              icon={<PlayIcon />}
              component={(props) => (
                <Link to="/" search={{ agentId: agent.id }} {...props}>
                  Chat
                </Link>
              )}
              style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}
            >
              Chat
            </Button>
          </FlexItem>
        </Flex>
      </div>
    </Card>
  );
}
