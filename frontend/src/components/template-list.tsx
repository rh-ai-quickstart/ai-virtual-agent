import { TemplateSuite } from '@/types/templates';
import { Agent } from '@/routes/config/agents';
import { 
  Card, 
  CardBody, 
  CardHeader,
  CardTitle,
  Button, 
  Badge,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Checkbox,
  Title
} from '@patternfly/react-core';
import { useState, useRef, useEffect } from 'react';

interface TemplateListProps {
  templates: TemplateSuite[];
  agents: Agent[]; // Add agents prop
  onDeploy: (templateId: string, selectedAgents?: string[]) => void;
  isDeploying: boolean;
  isLoading: boolean;
  selectedCategory: string;
  onRefresh?: () => void;
}

export function TemplateList({ 
  templates, 
  agents, // Add agents to destructuring
  onDeploy, 
  isDeploying, 
  isLoading, 
  selectedCategory,
  onRefresh 
}: TemplateListProps) {
  const [hoveredTemplate, setHoveredTemplate] = useState<string | null>(null);
  const [overlayPosition, setOverlayPosition] = useState({ x: 0, y: 0 });
  const [overlayVisible, setOverlayVisible] = useState(false);
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateSuite | null>(null);
  const [selectedAgents, setSelectedAgents] = useState<Set<string>>(new Set());
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (hoveredTemplate && overlayRef.current) {
      setOverlayVisible(true);
    } else {
      setOverlayVisible(false);
    }
  }, [hoveredTemplate]);

  // Add function to check if template is already deployed
  const isTemplateDeployed = (template: TemplateSuite) => {
    const existingAgents = agents.filter(agent => {
      // Check if agent has metadata indicating it was deployed from this template
      if (agent.metadata?.template_id === template.id) {
        return true;
      }
      
      // Fallback: Check if agent name matches any agent in this template
      if (template.agents) {
        return template.agents.some(templateAgent => templateAgent.name === agent.name);
      }
      
      return false;
    });
    
    // Check if ALL agents from the template exist
    return existingAgents.length === (template.agents?.length || 0);
  };

  // Add function to check if template is partially deployed
  const isTemplatePartiallyDeployed = (template: TemplateSuite) => {
    const existingAgents = agents.filter(agent => {
      // Check if agent has metadata indicating it was deployed from this template
      if (agent.metadata?.template_id === template.id) {
        return true;
      }
      
      // Fallback: Check if agent name matches any agent in this template
      if (template.agents) {
        return template.agents.some(templateAgent => templateAgent.name === agent.name);
      }
      
      return false;
    });
    
    // Check if SOME but not ALL agents from the template exist
    const templateAgentCount = template.agents?.length || 0;
    return existingAgents.length > 0 && existingAgents.length < templateAgentCount;
  };

  const handleDeployClick = (template: TemplateSuite) => {
    // Check if template is already deployed
    if (isTemplateDeployed(template)) {
      // You could show a warning here or just return
      console.log(`Template ${template.name} is already deployed`);
      return;
    }
    
    setSelectedTemplate(template);
    setSelectedAgents(new Set(template.agents.map(agent => agent.name)));
    setShowDeployModal(true);
  };

  const handleDeployAll = () => {
    if (selectedTemplate) {
      onDeploy(selectedTemplate.id);
      setShowDeployModal(false);
    }
  };

  const handleDeploySelected = () => {
    if (selectedTemplate) {
      onDeploy(selectedTemplate.id, Array.from(selectedAgents));
      setShowDeployModal(false);
    }
  };

  const handleSelectAgent = (agentName: string, checked: boolean) => {
    const newSelected = new Set(selectedAgents);
    if (checked) {
      newSelected.add(agentName);
    } else {
      newSelected.delete(agentName);
    }
    setSelectedAgents(newSelected);
  };

  const handleSelectAll = (checked: boolean) => {
    if (selectedTemplate) {
      if (checked) {
        setSelectedAgents(new Set(selectedTemplate.agents.map(agent => agent.name)));
      } else {
        setSelectedAgents(new Set());
      }
    }
  };

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <div>Loading templates...</div>
      </div>
    );
  }

  if (templates.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--pf-v6-global--Color--200)' }}>
        <div style={{ marginBottom: '1rem' }}>
          {selectedCategory
            ? `No templates available for the "${selectedCategory}" category.`
            : 'No templates are currently available. Please check back later.'}
        </div>
        {onRefresh && (
          <Button variant="secondary" onClick={onRefresh}>
            Refresh Templates
          </Button>
        )}
      </div>
    );
  }

  const getTemplateDetails = (template: TemplateSuite) => {
    const details = [];
    
    if (template.description) {
      details.push({ label: 'Description', value: template.description });
    }
    
    if (template.metadata?.persona_count) {
      details.push({ label: 'Personas', value: `${template.metadata.persona_count} specialized roles` });
    }
    
    if (template.metadata?.agent_count) {
      details.push({ label: 'Agents', value: `${template.metadata.agent_count} AI assistants` });
    }
    
    if (template.metadata?.industry) {
      details.push({ label: 'Industry', value: template.metadata.industry });
    }
    
    if (template.metadata?.use_cases) {
      details.push({ label: 'Use Cases', value: template.metadata.use_cases.join(', ') });
    }
    
    if (template.metadata?.compliance) {
      details.push({ label: 'Compliance', value: template.metadata.compliance.join(', ') });
    }

    return details;
  };

  const handleCardMouseEnter = (templateId: string, event: React.MouseEvent) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setOverlayPosition({
      x: rect.right + 20,
      y: rect.top
    });
    setHoveredTemplate(templateId);
  };

  const handleCardMouseLeave = () => {
    setHoveredTemplate(null);
  };

  const selectedTemplateData = templates.find(t => t.id === hoveredTemplate);
  const templateDetails = selectedTemplateData ? getTemplateDetails(selectedTemplateData) : [];

  return (
    <div style={{ position: 'relative' }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
        gap: '1rem'
      }}>
        {templates.map((template) => {
          const isDeployed = isTemplateDeployed(template);
          
          return (
            <Card 
              key={template.id} 
              style={{ 
                backgroundColor: 'transparent', 
                border: '1px solid var(--border-secondary)',
                transition: 'all 0.2s ease-in-out',
                cursor: 'pointer'
              }}
              onMouseEnter={(e) => handleCardMouseEnter(template.id, e)}
              onMouseLeave={handleCardMouseLeave}
            >
              <CardHeader>
                <CardTitle style={{ color: 'var(--text-primary)' }}>
                  {template.name}
                </CardTitle>
              </CardHeader>
              <CardBody>
                <div style={{ marginBottom: '1rem' }}>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                    {template.description}
                  </p>
                </div>
                
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  marginBottom: '1rem'
                }}>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <Badge isRead style={{ 
                      backgroundColor: 'transparent', 
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border-secondary)'
                    }}>
                      {template.metadata.persona_count || 0} personas
                    </Badge>
                    <Badge isRead style={{ 
                      backgroundColor: 'transparent', 
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border-secondary)'
                    }}>
                      {template.metadata.agent_count || 0} agents
                    </Badge>
                    {isDeployed && (
                      <Badge style={{ 
                        backgroundColor: 'var(--success-color)',
                        color: 'white'
                      }}>
                        Deployed
                      </Badge>
                    )}
                  </div>
                </div>

                <Button
                  variant="primary"
                  onClick={() => handleDeployClick(template)}
                  isDisabled={isDeploying || isTemplateDeployed(template)}
                  style={{ 
                    backgroundColor: isTemplateDeployed(template) 
                      ? 'var(--pf-v6-global--Color--200)' 
                      : '#0066cc', // Bright blue for better visibility
                    color: isTemplateDeployed(template) 
                      ? 'var(--pf-v6-global--Color--300)' 
                      : 'white',
                    cursor: isTemplateDeployed(template) 
                      ? 'not-allowed' 
                      : 'pointer',
                    fontWeight: 'bold',
                    fontSize: '1rem',
                    padding: '0.75rem 1.5rem',
                    border: isTemplateDeployed(template) 
                      ? '1px solid var(--border-secondary)' 
                      : '1px solid #0066cc',
                    boxShadow: isTemplateDeployed(template) 
                      ? 'none' 
                      : '0 2px 4px rgba(0, 102, 204, 0.3)',
                    transition: 'all 0.2s ease-in-out',
                    width: '100%',
                    borderRadius: '6px',
                    textTransform: 'none',
                    letterSpacing: '0.025em'
                  }}
                  onMouseEnter={(e) => {
                    if (!isTemplateDeployed(template) && !isDeploying) {
                      e.currentTarget.style.backgroundColor = '#0052a3';
                      e.currentTarget.style.transform = 'translateY(-1px)';
                      e.currentTarget.style.boxShadow = '0 4px 8px rgba(0, 102, 204, 0.4)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isTemplateDeployed(template) && !isDeploying) {
                      e.currentTarget.style.backgroundColor = '#0066cc';
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = '0 2px 4px rgba(0, 102, 204, 0.3)';
                    }
                  }}
                >
                  {isTemplateDeployed(template) 
                    ? 'Already Deployed' 
                    : isTemplatePartiallyDeployed(template)
                    ? 'Deploy Remaining'
                    : 'Deploy Template'
                  }
                </Button>
              </CardBody>
            </Card>
          );
        })}
      </div>

      {/* Floating Overlay */}
      {overlayVisible && selectedTemplateData && (
        <div
          ref={overlayRef}
          style={{
            position: 'fixed',
            left: overlayPosition.x,
            top: overlayPosition.y,
            width: '300px',
            backgroundColor: 'var(--background-primary)',
            border: '1px solid var(--border-secondary)',
            borderRadius: '8px',
            padding: '1rem',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            zIndex: 1000,
            fontSize: '0.875rem'
          }}
        >
          <Title headingLevel="h6" style={{ marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
            {selectedTemplateData.name}
          </Title>
          {templateDetails.map((detail, index) => (
            <div key={index} style={{ marginBottom: '0.25rem' }}>
              <span style={{ fontWeight: 'bold', color: 'var(--text-primary)' }}>{detail.label}:</span>
              <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem' }}>{detail.value}</span>
            </div>
          ))}
        </div>
      )}

      {/* Deploy Modal */}
      <Modal
        variant="medium"
        title="Deploy Template"
        isOpen={showDeployModal}
        onClose={() => setShowDeployModal(false)}
      >
        <ModalHeader title={`Deploy ${selectedTemplate?.name || 'Template'}`} />
        <ModalBody>
          <div style={{ marginBottom: '1rem' }}>
            <p style={{ color: 'var(--text-muted)' }}>
              Select which agents you want to deploy from this template:
            </p>
          </div>
          
          {selectedTemplate && (
            <div>
              <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Checkbox
                  id="select-all-agents"
                  isChecked={selectedAgents.size === selectedTemplate.agents.length}
                  onChange={(_, checked) => handleSelectAll(checked)}
                  aria-label="Select all agents"
                />
                <span>Select All ({selectedTemplate.agents.length} agents)</span>
              </div>
              
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
                gap: '0.5rem'
              }}>
                {selectedTemplate.agents.map((agent) => (
                  <div
                    key={agent.name}
                    style={{
                      padding: '0.75rem',
                      border: '1px solid var(--border-secondary)',
                      borderRadius: '6px',
                      backgroundColor: 'transparent',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '0.5rem'
                    }}
                  >
                    <Checkbox
                      id={`select-agent-${agent.name}`}
                      isChecked={selectedAgents.has(agent.name)}
                      onChange={(_, checked) => handleSelectAgent(agent.name, checked)}
                      aria-label={`Select ${agent.name}`}
                    />
                    <div>
                      <div style={{ fontWeight: 'bold', color: 'var(--text-primary)' }}>
                        {agent.name}
                      </div>
                      {agent.description && (
                        <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                          {agent.description}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </ModalBody>
        <ModalFooter>
          <Button
            variant="secondary"
            onClick={() => setShowDeployModal(false)}
            isDisabled={isDeploying}
          >
            Cancel
          </Button>
          <Button
            variant="secondary"
            onClick={handleDeploySelected}
            isLoading={isDeploying}
            isDisabled={isDeploying || selectedAgents.size === 0}
          >
            Deploy Selected ({selectedAgents.size})
          </Button>
          <Button
            variant="primary"
            onClick={handleDeployAll}
            isLoading={isDeploying}
            isDisabled={isDeploying}
          >
            Deploy All
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
} 