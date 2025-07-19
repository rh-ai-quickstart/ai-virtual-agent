import { NewAgentCard } from '@/components/new-agent-card';
import { TemplateList } from '@/components/template-list';
import { templateService } from '@/services/templates';
import { fetchAgents } from '@/services/agents';
import { ToolAssociationInfo } from '@/types';
import { 
  Flex, 
  FlexItem, 
  PageSection, 
  Title, 
  Button, 
  Alert,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Tabs,
  Tab,
  TabTitleText,
  AlertActionCloseButton
} from '@patternfly/react-core';
// import { PlusIcon, BookOpenIcon, UsersIcon } from '@patternfly/react-icons';
import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { TemplateAgentList } from '@/components/template-agent-list';
import { personaStorage } from '@/services/persona-storage';
import { useSearch } from '@tanstack/react-router';

// Type def for fetching agents
export interface Agent {
  id: string;
  name: string;
  model_name: string;
  prompt: string;
  tools: ToolAssociationInfo[];
  knowledge_base_ids: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
  metadata?: {
    template_id?: string;
    template_name?: string;
    persona?: string;
    deployed_from_template?: boolean;
    deployment_timestamp?: string;
  };
}

// Type def for creating agents
export interface NewAgent {
  name: string;
  description?: string;
  model_name: string;
  prompt: string;
  tools: ToolAssociationInfo[];
  knowledge_base_ids: string[];
}

// Use existing FSI banking template instead of hard-coded agents
const DEMO_TEMPLATE_ID = 'fsi_banking';

export const Route = createFileRoute('/config/agents')({
  component: Agents,
});

export function Agents() {
  const search = useSearch({ from: '/config/agents' });
  const [activeTab, setActiveTab] = useState(0);
  const [showDemoModal, setShowDemoModal] = useState(false);
  const [demoProgress, setDemoProgress] = useState<string[]>([]);
  const [isDeploying, setIsDeploying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const queryClient = useQueryClient();

  // Use React Query with better error handling
  const { 
    data: templates = [], 
    isLoading: isLoadingTemplates, 
    error: templatesError,
    refetch: refetchTemplates 
  } = useQuery({
    queryKey: ['templates'],
    queryFn: async () => {
      console.log('Fetching templates...');
      const response = await templateService.getTemplates();
      console.log('Templates response:', response);
      return response;
    },
    staleTime: 600000, // 10 minutes
    gcTime: 1800000, // 30 minutes
    retry: (failureCount, error) => {
      // Don't retry on network interruption errors
      if (error.message?.includes('message channel closed')) {
        return false;
      }
      return failureCount < 2;
    },
    retryDelay: 2000,
  });

  // Use React Query for categories - commented out as not used
  // const { 
  //   data: categories = [], 
  //   isLoading: isLoadingCategories 
  // } = useQuery({
  //   queryKey: ['template-categories'],
  //   queryFn: async () => {
  //     const response = await templateService.getCategories();
  //     return response;
  //   },
  //   staleTime: 30000, // 30 seconds
  // });

  // Use React Query for agents
  const { 
    data: agents = [], 
    isLoading: isLoadingAgents 
  } = useQuery({
    queryKey: ['agents'],
    queryFn: fetchAgents,
    staleTime: 10000, // 10 seconds
  });

  // Initialize personas from agent metadata when agents are loaded
  useEffect(() => {
    if (agents && agents.length > 0) {
      personaStorage.initializeFromAgents(agents);
    }
  }, [agents]);

  // Handle tab selection from URL search params
  useEffect(() => {
    if ('tab' in search && search.tab === 'my-agents') {
      setActiveTab(2); // Switch to "My Agents" tab
    } else if ('tab' in search && search.tab === 'templates') {
      setActiveTab(0); // Switch to "Templates" tab
    } else if ('tab' in search && search.tab === 'new-agent') {
      setActiveTab(1); // Switch to "New Agent" tab
    }
  }, ['tab' in search ? search.tab : undefined]);

  const handleDeploy = async (templateId: string, selectedAgents?: string[]) => {
    try {
      setIsDeploying(true);
      setError(null);
      
      const result = await templateService.deployTemplate(templateId, selectedAgents);
      console.log('Deployment result:', result);
      
      if (result.success) {
        // const agentCount = selectedAgents ? selectedAgents.length : 'all';
        setSuccess(`Template deployed successfully! Created ${result.agent_ids?.length || 0} agents.`);
        
        // Auto-dismiss success message after 5 seconds
        setTimeout(() => {
          setSuccess(null);
        }, 5000);
        
        // Save persona mappings for deployed agents
        if (result.deployed_agents) {
          console.log('Deployed agents with metadata:', result.deployed_agents);
          result.deployed_agents.forEach((agent: any) => {
            console.log(`Agent ${agent.name} metadata:`, agent.metadata);
            if (agent.metadata?.persona) {
              console.log(`Saving persona "${agent.metadata.persona}" for agent ${agent.id} from template ${templateId}`);
              personaStorage.setPersona(agent.id, agent.metadata.persona, templateId);
            } else {
              console.log(`No persona found in metadata for agent ${agent.id}`);
            }
          });
        } else {
          console.log('No deployed_agents in result:', result);
        }
        
        // Refresh both templates and agents
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['templates'] }),
          queryClient.invalidateQueries({ queryKey: ['agents'] })
        ]);
        // Automatically switch to Agents tab
        setActiveTab(2); // Changed from 0 to 2 for "My Agents" tab
      } else {
        setError(result.error || 'Deployment failed');
      }
    } catch (err: any) {
      setError('Deployment failed: ' + (err.message || 'Unknown error'));
    } finally {
      setIsDeploying(false);
    }
  };

  // Mutation for creating demo agents using template
  const createDemoMutation = useMutation({
    mutationFn: async () => {
      setDemoProgress([]);
      
      try {
        // Deploy the demo template instead of creating individual agents
        const result = await templateService.deployTemplate(DEMO_TEMPLATE_ID);
        
        if (result.success) {
          setDemoProgress(prev => [...prev, ` Deployed ${result.agent_ids?.length || 0} demo agents`]);
          
          // Save persona mappings for deployed agents
          if (result.deployed_agents) {
            result.deployed_agents.forEach((agent: any) => {
              if (agent.metadata?.persona) {
                personaStorage.setPersona(agent.id, agent.metadata.persona, DEMO_TEMPLATE_ID);
              }
            });
          }
          
          return result.deployed_agents || [];
        } else {
          throw new Error(result.error || 'Demo deployment failed');
        }
              } catch (error: any) {
          console.error('Demo deployment failed:', error);
          setDemoProgress(prev => [...prev, `❌ Demo deployment failed: ${error.message || 'Unknown error'}`]);
          throw error;
        }
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['agents'] });
              setDemoProgress(prev => [...prev, ' Demo agents deployed successfully!']);
      setTimeout(() => {
        setShowDemoModal(false);
        setDemoProgress([]);
      }, 2000);
    },
    onError: (error) => {
      console.error('Demo creation failed:', error);
      setDemoProgress(prev => [...prev, '❌ Demo creation failed']);
    }
  });

  // const handleCreateDemo = () => {
  //   setShowDemoModal(true);
  //   createDemoMutation.mutate();
  // };

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  return (
    <PageSection>
      <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
        <FlexItem>
          <Title headingLevel="h1">AI Agents</Title>
          <p>Create, deploy, and manage intelligent AI agents for your organization.</p>
        </FlexItem>

        <FlexItem>
          <Tabs 
            activeKey={activeTab} 
            onSelect={(_, tabIndex) => setActiveTab(tabIndex as number)}
          >
            <Tab 
              eventKey={0} 
              title={<TabTitleText>Templates</TabTitleText>}
            >
              <div style={{ padding: '1rem 0' }}>
                {error && (
                  <Alert
                    variant="danger"
                    title="Error"
                    actionClose={<AlertActionCloseButton onClose={clearMessages} />}
                    style={{ marginBottom: '1rem' }}
                  >
                    {error}
                  </Alert>
                )}

                {success && (
                  <Alert
                    variant="success"
                    title="Success"
                    actionClose={<AlertActionCloseButton onClose={clearMessages} />}
                    style={{ marginBottom: '1rem' }}
                  >
                    {success}
                  </Alert>
                )}

                {templatesError && (
                  <Alert
                    variant="warning"
                    title="Warning"
                    style={{ marginBottom: '1rem' }}
                  >
                    Failed to load templates. <Button variant="link" onClick={() => refetchTemplates()}>Retry</Button>
                  </Alert>
                )}

                <TemplateList
                  templates={templates}
                  agents={agents || []} // Add agents prop
                  onDeploy={handleDeploy}
                  isDeploying={isDeploying}
                  isLoading={isLoadingTemplates}
                  selectedCategory=""
                />
              </div>
            </Tab>
            
            <Tab 
              eventKey={1} 
              title={<TabTitleText>New Agent</TabTitleText>}
            >
              <div style={{ padding: '1rem 0' }}>
                <NewAgentCard />
              </div>
            </Tab>
            
            <Tab 
              eventKey={2} 
              title={<TabTitleText>My Agents</TabTitleText>}
            >
              <div style={{ padding: '1rem 0' }}>
                <TemplateAgentList 
                  agents={agents || []} 
                  templates={templates || []} // Add templates prop
                  isLoading={isLoadingAgents} 
                  onSwitchToTemplates={() => setActiveTab(0)} // Add this prop
                />
              </div>
            </Tab>
          </Tabs>
        </FlexItem>
      </Flex>

      {/* NEW: Banking Templates Modal */}
      <Modal
        variant="small"
        title="Deploy Template"
        isOpen={showDemoModal}
        onClose={() => !createDemoMutation.isPending && setShowDemoModal(false)}
      >
        <ModalHeader title="Setting Up Agent Templates" />
        <ModalBody>
          <Flex direction={{ default: 'column' }} gap={{ default: 'gapSm' }}>
            <FlexItem>
              <p>Creating specialized agents from templates...</p>
            </FlexItem>
            {demoProgress.map((progress, index) => (
              <FlexItem key={index}>
                <div style={{ fontFamily: 'monospace', fontSize: '14px' }}>
                  {progress}
                </div>
              </FlexItem>
            ))}
            {createDemoMutation.isPending && demoProgress.length === 0 && (
              <FlexItem>
                <div>🚀 Deploying templates...</div>
              </FlexItem>
            )}
          </Flex>
        </ModalBody>
        <ModalFooter>
          <Button
            variant="link"
            onClick={() => setShowDemoModal(false)}
            isDisabled={createDemoMutation.isPending}
          >
            {createDemoMutation.isPending ? 'Creating...' : 'Close'}
          </Button>
        </ModalFooter>
      </Modal>
    </PageSection>
  );
}