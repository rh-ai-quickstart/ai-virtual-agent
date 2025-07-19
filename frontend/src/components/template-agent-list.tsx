import React, { useState, useMemo } from 'react';
import { Agent } from '@/routes/config/agents';
import { deleteAgent } from '@/services/agents';
import { personaStorage } from '@/services/persona-storage';
import { useNavigate } from '@tanstack/react-router';
import { TemplateSuite } from '@/types/templates';
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Checkbox,
  Button,
  Flex,
  FlexItem,
  Title,
  Alert,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Badge,
  Breadcrumb,
  BreadcrumbItem
} from '@patternfly/react-core';
import { 
  TrashIcon, 
  UsersIcon,
  ArrowLeftIcon,
  BuildingIcon
} from '@patternfly/react-icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';

interface TemplateAgentListProps {
  agents: Agent[];
  templates: TemplateSuite[]; // Add templates prop
  isLoading: boolean;
  onSwitchToTemplates: () => void;
}

interface AgentGroup {
  templateName: string;
  personaName: string;
  agents: Agent[];
}

interface TemplateGroup {
  templateName: string;
  templateId: string;
  agentCount: number;
  personas: string[];
}

export function TemplateAgentList({ 
  agents, 
  templates, // Add templates parameter
  isLoading, 
  onSwitchToTemplates 
}: TemplateAgentListProps) {
  const [selectedAgents, setSelectedAgents] = useState<Set<string>>(new Set());
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [hasInitializedPersonas, setHasInitializedPersonas] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  // Get selected template info
  const selectedTemplateInfo = useMemo(() => {
    if (!selectedTemplate) return null;
    if (selectedTemplate === 'other') {
      return { templateName: 'Other', templateId: 'other' };
    }
    return templates.find(t => t.id === selectedTemplate) || null;
  }, [selectedTemplate, templates]);

  // One-time initialization of personas for existing agents
  React.useEffect(() => {
    if (!hasInitializedPersonas && agents.length > 0) {
      console.log('Initializing personas for existing agents...');
      agents.forEach(agent => {
        // Try to find matching template agent by name
        for (const template of templates) {
          if (template.agents) {
            for (const templateAgent of template.agents) {
              if (templateAgent.name === agent.name) {
                console.log(`Found match: Agent ${agent.name} matches template ${template.id} agent ${templateAgent.name}`);
                if (templateAgent.persona) {
                  console.log(`Setting persona "${templateAgent.persona}" for agent ${agent.id}`);
                  personaStorage.setPersona(agent.id, templateAgent.persona, template.id);
                }
                break;
              }
            }
          }
        }
      });
      setHasInitializedPersonas(true);
    }
  }, [agents, templates, hasInitializedPersonas]);

  // Group agents by template
  const templateGroups = useMemo(() => {
    const groups: TemplateGroup[] = [];
    const ungrouped: Agent[] = [];

    console.log('Debug: Grouping agents:', agents);
    console.log('Debug: Available templates:', templates);

    // Group agents by template using metadata
    const templateAgentMap: Record<string, { agents: Agent[]; personas: Set<string> }> = {};
    
    agents.forEach(agent => {
      const templateId = agent.metadata?.template_id;
      const persona = agent.metadata?.persona;
      
      console.log(`Debug: Agent ${agent.name} (${agent.id}):`, {
        templateId,
        persona,
        hasTemplateId: !!templateId,
        hasPersona: !!persona
      });
      
      if (templateId) {
        if (!templateAgentMap[templateId]) {
          templateAgentMap[templateId] = { agents: [], personas: new Set() };
        }
        
        templateAgentMap[templateId].agents.push(agent);
        if (persona) {
          templateAgentMap[templateId].personas.add(persona);
        }
      } else {
        // Fallback: Try to match agent name to template agents
        let matchedTemplateId: string | null = null;
        let matchedPersona: string | null = null;
        
        for (const template of templates) {
          if (template.agents) {
            for (const templateAgent of template.agents) {
              if (templateAgent.name === agent.name) {
                matchedTemplateId = template.id;
                matchedPersona = templateAgent.persona || null;
                break;
              }
            }
            if (matchedTemplateId) break;
          }
        }
        
        if (matchedTemplateId) {
          console.log(`Debug: Matched agent ${agent.name} to template ${matchedTemplateId} by name`);
          if (!templateAgentMap[matchedTemplateId]) {
            templateAgentMap[matchedTemplateId] = { agents: [], personas: new Set() };
          }
          
          templateAgentMap[matchedTemplateId].agents.push(agent);
          if (matchedPersona) {
            templateAgentMap[matchedTemplateId].personas.add(matchedPersona);
          }
        } else {
          ungrouped.push(agent);
        }
      }
    });

    console.log('Debug: Template agent map:', templateAgentMap);
    console.log('Debug: Ungrouped agents:', ungrouped);

    // Convert to array format
    Object.entries(templateAgentMap).forEach(([templateId, data]) => {
      const template = templates.find(t => t.id === templateId);
      console.log(`Debug: Looking for template ${templateId}:`, template);
      if (template) {
        groups.push({
          templateName: template.name,
          templateId: templateId,
          agentCount: data.agents.length,
          personas: Array.from(data.personas)
        });
      }
    });

    // Add ungrouped if any
    if (ungrouped.length > 0) {
      groups.push({
        templateName: 'Other',
        templateId: 'other',
        agentCount: ungrouped.length,
        personas: []
      });
    }

    console.log('Debug: Final template groups:', groups);
    return groups;
  }, [agents, templates]);

  // Get agents for selected template
  const selectedTemplateAgents = useMemo(() => {
    if (!selectedTemplate) return [];
    
    if (selectedTemplate === 'other') {
      // Return agents that don't match any template
      return agents.filter(agent => {
        // Check if agent has metadata
        if (agent.metadata?.template_id) {
          return false; // Has metadata, so not "other"
        }
        
        // Check if agent name matches any template
        for (const template of templates) {
          if (template.agents) {
            for (const templateAgent of template.agents) {
              if (templateAgent.name === agent.name) {
                return false; // Matches a template, so not "other"
              }
            }
          }
        }
        
        return true; // No match found, so it's "other"
      });
    }

    return agents.filter(agent => {
      // Check if agent has metadata indicating it was deployed from this template
      if (agent.metadata?.template_id === selectedTemplate) {
        return true;
      }
      
      // Fallback: Check if agent name matches any agent in this template
      const template = templates.find(t => t.id === selectedTemplate);
      if (template && template.agents) {
        return template.agents.some(templateAgent => templateAgent.name === agent.name);
      }
      
      return false;
    });
  }, [agents, selectedTemplate, templates]);

  // Group agents by persona within selected template
  const selectedTemplateAgentGroups = useMemo(() => {
    if (!selectedTemplate) return [];

    const groups: AgentGroup[] = [];
    
    // Special handling for "Other" template
    if (selectedTemplate === 'other') {
      // Create a single group for ungrouped agents
      if (selectedTemplateAgents.length > 0) {
        groups.push({
          templateName: 'Other',
          personaName: 'Ungrouped Agents',
          agents: selectedTemplateAgents
        });
      }
      return groups;
    }

    const personaToTemplate: Record<string, { templateName: string; personaName: string }> = {};
    
    templates.forEach(template => {
      if (template.personas) {
        Object.keys(template.personas).forEach(personaKey => {
          personaToTemplate[personaKey] = {
            templateName: template.name,
            personaName: template.personas[personaKey]?.label || personaKey
          };
        });
      }
    });

    const personaGroups: Record<string, Agent[]> = {};
    
    selectedTemplateAgents.forEach(agent => {
      let persona: string | null = null;
      
      // First try to get persona from metadata
      if (agent.metadata?.persona) {
        persona = agent.metadata.persona;
      } else {
        // Fallback: Try to match agent name to template agents to get persona
        const template = templates.find(t => t.id === selectedTemplate);
        if (template && template.agents) {
          const templateAgent = template.agents.find(ta => ta.name === agent.name);
          if (templateAgent && templateAgent.persona) {
            persona = templateAgent.persona;
          }
        }
      }
      
      if (persona) {
        if (!personaGroups[persona]) {
          personaGroups[persona] = [];
        }
        personaGroups[persona].push(agent);
      } else {
        // If no persona found, put in a default group
        const defaultPersona = 'Other';
        if (!personaGroups[defaultPersona]) {
          personaGroups[defaultPersona] = [];
        }
        personaGroups[defaultPersona].push(agent);
      }
    });

    Object.entries(personaGroups).forEach(([persona, agents]) => {
      const templateInfo = personaToTemplate[persona];
      if (templateInfo) {
        groups.push({
          templateName: templateInfo.templateName,
          personaName: templateInfo.personaName,
          agents: agents
        });
      } else {
        // For agents without a matching persona, create a default group
        const template = templates.find(t => t.id === selectedTemplate);
        groups.push({
          templateName: template?.name || 'Template',
          personaName: persona,
          agents: agents
        });
      }
    });

    return groups;
  }, [selectedTemplateAgents, templates, selectedTemplate]);

  // Selection handlers
  const handleSelectAgent = (agentId: string, checked: boolean) => {
    const newSelected = new Set(selectedAgents);
    if (checked) {
      newSelected.add(agentId);
    } else {
      newSelected.delete(agentId);
    }
    setSelectedAgents(newSelected);
  };

  const handleSelectGroup = (group: AgentGroup, checked: boolean) => {
    const newSelected = new Set(selectedAgents);
    group.agents.forEach(agent => {
      if (checked) {
        newSelected.add(agent.id);
      } else {
        newSelected.delete(agent.id);
      }
    });
    setSelectedAgents(newSelected);
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      const allAgentIds = selectedTemplateAgents.map(agent => agent.id);
      setSelectedAgents(new Set(allAgentIds));
    } else {
      setSelectedAgents(new Set());
    }
  };

  // Chat handler
  const handleChatWithAgent = (agentId: string) => {
    navigate({ to: '/', search: { agentId } });
  };

  // Delete mutation
  const deleteAgentsMutation = useMutation({
    mutationFn: async (agentIds: string[]) => {
      const promises = agentIds.map(agentId => deleteAgent(agentId));
      await Promise.all(promises);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['agents'] });
      setSelectedAgents(new Set());
      setShowDeleteModal(false);
    },
    onError: (error) => {
      console.error('Error deleting agents:', error);
    }
  });

  const handleBulkDelete = () => {
    deleteAgentsMutation.mutate(Array.from(selectedAgents));
  };

  const isGroupSelected = (group: AgentGroup) => {
    return group.agents.every(agent => selectedAgents.has(agent.id));
  };

  if (isLoading) {
    return <div>Loading agents...</div>;
  }

  // Show template selection view
  if (!selectedTemplate) {
    return (
      <div>
        {/* Header */}
        <Card style={{ marginBottom: '1rem', backgroundColor: 'transparent', border: '1px solid var(--border-secondary)' }}>
          <CardBody>
            <Title headingLevel="h4" size="md" style={{ color: 'var(--text-primary)' }}>
              {agents.length === 0 
                ? 'No agents created yet'
                : templateGroups.length === 0
                ? `${agents.length} agents available`
                : `${agents.length} total agent${agents.length > 1 ? 's' : ''} across ${templateGroups.length} template${templateGroups.length > 1 ? 's' : ''}`
              }
            </Title>
          </CardBody>
        </Card>

        {/* Show message when no agents exist */}
        {agents.length === 0 && (
          <Card style={{ backgroundColor: 'transparent', border: '1px solid var(--border-secondary)' }}>
            <CardBody>
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                <UsersIcon style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.5 }} />
                <Title headingLevel="h3" size="lg" style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>
                  No Agents Created
                </Title>
                <p style={{ marginBottom: '1rem' }}>
                  Deploy templates from the Templates tab to create your first agents.
                </p>
                <Button 
                  variant="primary" 
                  onClick={onSwitchToTemplates || (() => console.log('No template switch function provided'))}
                  style={{ marginRight: '0.5rem' }}
                >
                  Go to Templates
                </Button>
              </div>
            </CardBody>
          </Card>
        )}

        {/* Show ungrouped agents when no template groups exist */}
        {agents.length > 0 && templateGroups.length === 0 && (
          <Card style={{ backgroundColor: 'transparent', border: '1px solid var(--border-secondary)' }}>
            <CardHeader>
              <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapMd' }}>
                <FlexItem>
                  <Checkbox
                    id="select-all-ungrouped"
                    isChecked={selectedAgents.size === agents.length && agents.length > 0}
                    onChange={(_, checked) => {
                      if (checked) {
                        setSelectedAgents(new Set(agents.map(agent => agent.id)));
                      } else {
                        setSelectedAgents(new Set());
                      }
                    }}
                    aria-label="Select all ungrouped agents"
                  />
                </FlexItem>
                <FlexItem>
                  <Title headingLevel="h4" size="md" style={{ color: 'var(--text-primary)' }}>
                    Ungrouped Agents ({agents.length})
                  </Title>
                </FlexItem>
                {selectedAgents.size > 0 && (
                  <FlexItem>
                    <Button
                      variant="danger"
                      icon={<TrashIcon />}
                      onClick={() => setShowDeleteModal(true)}
                    >
                      Delete Selected
                    </Button>
                  </FlexItem>
                )}
              </Flex>
            </CardHeader>
            <CardBody>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                gap: '0.5rem'
              }}>
                {agents.map((agent) => (
                  <div
                    key={agent.id}
                    style={{
                      padding: '0.75rem',
                      border: '1px solid var(--border-secondary)',
                      borderRadius: '6px',
                      backgroundColor: 'transparent',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.5rem'
                    }}
                  >
                    <Checkbox
                      id={`select-ungrouped-${agent.id}`}
                      isChecked={selectedAgents.has(agent.id)}
                      onChange={(_, checked) => {
                        const newSelected = new Set(selectedAgents);
                        if (checked) {
                          newSelected.add(agent.id);
                        } else {
                          newSelected.delete(agent.id);
                        }
                        setSelectedAgents(newSelected);
                      }}
                      aria-label={`Select ${agent.name}`}
                    />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 'bold', color: 'var(--text-primary)' }}>
                        {agent.name}
                      </div>
                      <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                        {agent.model_name}
                      </div>
                    </div>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleChatWithAgent(agent.id)}
                    >
                      Chat
                    </Button>
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        )}

        {/* Template Cards - only show if there are template groups */}
        {templateGroups.length > 0 && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
            gap: '1rem'
          }}>
            {templateGroups.map((template) => (
              <Card 
                key={template.templateId}
                style={{ 
                  backgroundColor: 'transparent', 
                  border: '1px solid var(--border-secondary)',
                  transition: 'all 0.2s ease-in-out',
                  cursor: 'pointer'
                }}
                onClick={() => setSelectedTemplate(template.templateId)}
              >
                <CardHeader>
                  <CardTitle style={{ color: 'var(--text-primary)' }}>
                    <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
                      <BuildingIcon style={{ color: 'var(--text-primary)' }} />
                      {template.templateName}
                    </Flex>
                  </CardTitle>
                </CardHeader>
                <CardBody>
                  <div style={{ marginBottom: '1rem' }}>
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                      {template.agentCount} agent{template.agentCount > 1 ? 's' : ''}
                      {template.personas.length > 0 && (
                        <span> • {template.personas.length} persona{template.personas.length > 1 ? 's' : ''}</span>
                      )}
                    </div>
                    {template.personas.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                        {template.personas.slice(0, 3).map((persona, index) => (
                          <Badge 
                            key={index} 
                            isRead 
                            style={{ 
                              backgroundColor: 'transparent', 
                              color: 'var(--text-muted)', 
                              border: '1px solid var(--border-secondary)',
                              fontSize: '0.75rem'
                            }}
                          >
                            {persona}
                          </Badge>
                        ))}
                        {template.personas.length > 3 && (
                          <Badge 
                            isRead 
                            style={{ 
                              backgroundColor: 'transparent', 
                              color: 'var(--text-muted)', 
                              border: '1px solid var(--border-secondary)',
                              fontSize: '0.75rem'
                            }}
                          >
                            +{template.personas.length - 3} more
                          </Badge>
                        )}
                      </div>
                    )}
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedTemplate(template.templateId);
                    }}
                  >
                    View Agents
                  </Button>
                </CardBody>
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div>
      {/* Breadcrumb */}
      <Card style={{ marginBottom: '1rem', backgroundColor: 'transparent', border: '1px solid var(--border-secondary)' }}>
        <CardBody>
          <Breadcrumb>
            <BreadcrumbItem>
              <Button 
                variant="link" 
                onClick={() => setSelectedTemplate(null)}
                style={{ padding: 0, color: 'var(--text-primary)' }}
              >
                <ArrowLeftIcon style={{ marginRight: '0.5rem' }} />
                All Templates
              </Button>
            </BreadcrumbItem>
            <BreadcrumbItem isActive>
              {selectedTemplateInfo && ('templateName' in selectedTemplateInfo ? selectedTemplateInfo.templateName : selectedTemplateInfo.name) || 'Template'}
            </BreadcrumbItem>
          </Breadcrumb>
        </CardBody>
      </Card>

      {/* Header with bulk actions */}
      <Card style={{ marginBottom: '1rem', backgroundColor: 'transparent', border: '1px solid var(--border-secondary)' }}>
        <CardBody>
          <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapMd' }}>
            <FlexItem>
              <Checkbox
                id="select-all-agents"
                isChecked={selectedAgents.size === selectedTemplateAgents.length && selectedTemplateAgents.length > 0}
                onChange={(_, checked) => handleSelectAll(checked)}
                aria-label="Select all agents"
              />
            </FlexItem>
            <FlexItem>
              <Title headingLevel="h4" size="md" style={{ color: 'var(--text-primary)' }}>
                {selectedAgents.size > 0 
                  ? `${selectedAgents.size} agent${selectedAgents.size > 1 ? 's' : ''} selected`
                  : `${selectedTemplateAgents.length} agents in ${selectedTemplateInfo && ('templateName' in selectedTemplateInfo ? selectedTemplateInfo.templateName : selectedTemplateInfo.name) || 'template'}`
                }
              </Title>
            </FlexItem>
            {selectedAgents.size > 0 && (
              <FlexItem>
                <Button
                  variant="danger"
                  icon={<TrashIcon />}
                  onClick={() => setShowDeleteModal(true)}
                >
                  Delete Selected
                </Button>
              </FlexItem>
            )}
          </Flex>
        </CardBody>
      </Card>

      {/* Agent Groups */}
      {selectedTemplateAgentGroups.map((group, groupIndex) => (
        <Card key={`${group.templateName}-${group.personaName}`} style={{ marginBottom: '1rem', backgroundColor: 'transparent', border: '1px solid var(--border-secondary)' }}>
          <CardHeader>
            <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapMd' }}>
              <Checkbox
                id={`select-group-${groupIndex}`}
                isChecked={isGroupSelected(group)}
                onChange={(_, checked) => handleSelectGroup(group, checked)}
                aria-label={`Select ${group.personaName} group`}
              />
              <FlexItem>
                <CardTitle>
                  <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
                    <UsersIcon style={{ color: 'var(--text-primary)' }} />
                    <span style={{ color: 'var(--text-primary)' }}>{group.personaName}</span>
                    <Badge isRead style={{ backgroundColor: 'transparent', color: 'var(--text-primary)', border: '1px solid var(--border-secondary)' }}>
                      {group.agents.length}
                    </Badge>
                  </Flex>
                </CardTitle>
              </FlexItem>
            </Flex>
          </CardHeader>
          <CardBody>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: '0.5rem'
            }}>
              {group.agents.map((agent) => (
                <div
                  key={agent.id}
                  style={{
                    padding: '0.75rem',
                    border: '1px solid var(--border-secondary)',
                    borderRadius: '6px',
                    backgroundColor: 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                  }}
                >
                  <Checkbox
                    id={`select-agent-${agent.id}`}
                    isChecked={selectedAgents.has(agent.id)}
                    onChange={(_, checked) => handleSelectAgent(agent.id, checked)}
                    aria-label={`Select ${agent.name}`}
                  />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 'bold', color: 'var(--text-primary)' }}>
                      {agent.name}
                    </div>
                    <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                      {agent.model_name}
                    </div>
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleChatWithAgent(agent.id)}
                  >
                    Chat
                  </Button>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      ))}

      {/* Delete Confirmation Modal */}
      <Modal
        variant="small"
        title="Delete Agents"
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
      >
        <ModalHeader title="Confirm Deletion" />
        <ModalBody>
          <Alert
            variant="warning"
            isInline
            title="Warning"
          >
            Are you sure you want to delete {selectedAgents.size} selected agent{selectedAgents.size > 1 ? 's' : ''}? This action cannot be undone.
          </Alert>
        </ModalBody>
        <ModalFooter>
          <Button
            variant="secondary"
            onClick={() => setShowDeleteModal(false)}
            isDisabled={deleteAgentsMutation.isPending}
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            onClick={handleBulkDelete}
            isLoading={deleteAgentsMutation.isPending}
          >
            {deleteAgentsMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}