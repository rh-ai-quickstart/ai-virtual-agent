import { TemplateSuite, TemplateDeployRequest } from '@/types/templates';
import { 
  Modal, 
  ModalHeader, 
  ModalBody, 
  ModalFooter, 
  Button, 
  Form, 
  FormGroup, 
  FormSection,
  Checkbox,
  TextInput,
  TextArea,
  Flex,
  FlexItem,
  Label,
  Alert,
  Spinner
} from '@patternfly/react-core';
import { RocketIcon, UsersIcon } from '@patternfly/react-icons';
import { useState } from 'react';

interface TemplateDeploymentModalProps {
  template: TemplateSuite | null;
  isOpen: boolean;
  onClose: () => void;
  onDeploy: (templateId: string, deployRequest: TemplateDeployRequest) => void;
  isDeploying: boolean;
}

export function TemplateDeploymentModal({
  template,
  isOpen,
  onClose,
  onDeploy,
  isDeploying
}: TemplateDeploymentModalProps) {
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [customName, setCustomName] = useState('');
  const [customDescription, setCustomDescription] = useState('');
  const [deployAll, setDeployAll] = useState(true);

  if (!template) return null;

  const handleAgentToggle = (agentName: string, checked: boolean) => {
    if (checked) {
      setSelectedAgents([...selectedAgents, agentName]);
    } else {
      setSelectedAgents(selectedAgents.filter(name => name !== agentName));
    }
  };

  const handleDeployAllToggle = (checked: boolean) => {
    setDeployAll(checked);
    if (checked) {
      setSelectedAgents(template.agents.map(agent => agent.name));
    } else {
      setSelectedAgents([]);
    }
  };

  const handleDeploy = () => {
    const deployRequest: TemplateDeployRequest = {
      selected_agents: deployAll ? undefined : selectedAgents,
      override_settings: {
        ...(customName && { name: customName }),
        ...(customDescription && { description: customDescription })
      }
    };

    onDeploy(template.id, deployRequest);
  };

  const handleClose = () => {
    setSelectedAgents([]);
    setCustomName('');
    setCustomDescription('');
    setDeployAll(true);
    onClose();
  };

  const canDeploy = deployAll || selectedAgents.length > 0;

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      variant="large"
      aria-labelledby="template-deployment-modal-title"
      aria-describedby="template-deployment-modal-description"
    >
      <ModalHeader>
        <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
          <RocketIcon />
          <span>Deploy Template: {template.name}</span>
        </Flex>
      </ModalHeader>
      
      <ModalBody>
        <Form>
          <FormSection title="Template Information">
            <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
              <FlexItem>
                <Label color="blue" variant="outline">
                  {template.category.replace('_', ' ').toUpperCase()}
                </Label>
              </FlexItem>
              <FlexItem>
                <TextArea
                  value={template.description}
                  isReadOnly
                  aria-label="Template description"
                  style={{ minHeight: '60px' }}
                />
              </FlexItem>
            </Flex>
          </FormSection>

          <FormSection title="Deployment Configuration">
            <FormGroup label="Custom Name (Optional)">
              <TextInput
                value={customName}
                onChange={setCustomName}
                placeholder="Enter custom name for deployed agents"
                aria-label="Custom agent name"
              />
            </FormGroup>

            <FormGroup label="Custom Description (Optional)">
              <TextArea
                value={customDescription}
                onChange={setCustomDescription}
                placeholder="Enter custom description for deployed agents"
                aria-label="Custom agent description"
              />
            </FormGroup>
          </FormSection>

          <FormSection title="Agent Selection">
            <FormGroup>
              <Checkbox
                label="Deploy all agents"
                isChecked={deployAll}
                onChange={handleDeployAllToggle}
                id="deploy-all-checkbox"
              />
            </FormGroup>

            {!deployAll && (
              <FormGroup label="Select agents to deploy:">
                <Flex direction={{ default: 'column' }} gap={{ default: 'gapSm' }}>
                  {template.agents.map((agent, index) => (
                    <FlexItem key={index}>
                      <Checkbox
                        label={
                          <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
                            <UsersIcon />
                            <span>{agent.name}</span>
                            {agent.description && (
                              <span style={{ color: 'var(--pf-v6-global--Color--200)', fontSize: '0.875rem' }}>
                                - {agent.description}
                              </span>
                            )}
                          </Flex>
                        }
                        isChecked={selectedAgents.includes(agent.name)}
                        onChange={(checked) => handleAgentToggle(agent.name, checked)}
                        id={`agent-${index}-checkbox`}
                      />
                    </FlexItem>
                  ))}
                </Flex>
              </FormGroup>
            )}
          </FormSection>

          {template.metadata?.features && (
            <FormSection title="Template Features">
              <Flex gap={{ default: 'gapXs' }}>
                {template.metadata.features.map((feature: string, index: number) => (
                  <FlexItem key={index}>
                    <Label color="green" variant="outline">
                      {feature}
                    </Label>
                  </FlexItem>
                ))}
              </Flex>
            </FormSection>
          )}
        </Form>
      </ModalBody>

      <ModalFooter>
        <Button variant="secondary" onClick={handleClose} isDisabled={isDeploying}>
          Cancel
        </Button>
        <Button
          variant="primary"
          icon={<RocketIcon />}
          onClick={handleDeploy}
          isDisabled={!canDeploy || isDeploying}
          isLoading={isDeploying}
        >
          {isDeploying ? 'Deploying...' : 'Deploy Template'}
        </Button>
      </ModalFooter>
    </Modal>
  );
} 