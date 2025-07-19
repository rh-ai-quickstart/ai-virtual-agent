import { NewAgentCard } from '@/components/new-agent-card';
import { TemplateList } from '@/components/template-list';
import { templateService } from '@/services/templates';
import { createAgent, fetchAgents } from '@/services/agents';
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
  Card,
  CardBody,
  Label,
  Tabs,
  Tab,
  TabTitleText,
  AlertActionCloseButton
} from '@patternfly/react-core';
import { MagicIcon, RocketIcon, PlusIcon, BookOpenIcon, UsersIcon } from '@patternfly/react-icons';
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
  model_name: string;
  prompt: string;
  tools: ToolAssociationInfo[];
  knowledge_base_ids: string[];
}

// NEW: Banking demo agents configuration
const BANKING_DEMO_AGENTS: NewAgent[] = [
  {
    name: "Compliance Policy Assistant",
    description: "Ensures adherence to US banking regulations",
    prompt: "You are a Compliance Policy Agent for a US bank. You help ensure adherence to US banking regulations including BSA/AML, OFAC, CFPB, OCC, and FDIC guidance. You provide accurate information about compliance procedures, reporting requirements, and regulatory updates.",
    model_name: "meta-llama/Llama-3.1-8B-Instruct",
    tools: [{ toolgroup_id: "builtin::websearch" }],
    knowledge_base_ids: [],
  },
  {
    name: 'Lending Policy Assistant',
    prompt: 'You are a Lending Policy Assistant for relationship managers and loan officers. You help with credit assessment, lending requests, documentation requirements, and regulatory compliance for loans. You know FHA guidelines, conventional loan requirements, and small business lending procedures.',
    model_name: 'meta-llama/Llama-3.1-8B-Instruct',
    tools: [{ toolgroup_id: 'builtin::websearch' }],
    knowledge_base_ids: []
  },
  {
    name: 'Customer Service Assistant',
    prompt: 'You are a Customer Service Assistant for branch tellers and customer service representatives. You help with day-to-day customer queries about product fees, account policies, transaction processing, and regulatory timelines. You provide accurate information about bank products and services.',
    model_name: 'meta-llama/Llama-3.1-8B-Instruct',
    tools: [{ toolgroup_id: 'builtin::websearch' }],
    knowledge_base_ids: []
  },
  {
    name: 'Fraud Detection Assistant',
    prompt: 'You are a Fraud Detection Assistant for fraud analysts and AML specialists. You help review alerts for suspicious transactions, investigate AML/BSA/OFAC red flags, and ensure reporting compliance. You provide guidance on escalation procedures and regulatory requirements.',
    model_name: 'meta-llama/Llama-3.1-8B-Instruct',
    tools: [{ toolgroup_id: 'builtin::websearch' }],
    knowledge_base_ids: []
  },
  {
    name: 'Training & Market Intelligence Assistant',
    prompt: 'You are a Training & Market Intelligence Assistant for training leads and analysts. You help keep staff current on new US regulations, industry certifications, and market developments. You provide information about regulatory updates, certification requirements, and industry best practices.',
    model_name: 'meta-llama/Llama-3.1-8B-Instruct',
    tools: [{ toolgroup_id: 'builtin::websearch' }],
    knowledge_base_ids: []
  },
  {
    name: 'IT Support Assistant',
    prompt: 'You are an IT Support Assistant for banking operations. You help support banking employees with system/process issues and ensure adherence to IT policies. You provide guidance on password resets, system access, security protocols, and technical procedures.',
    model_name: 'meta-llama/Llama-3.1-8B-Instruct',
    tools: [{ toolgroup_id: 'builtin::websearch' }],
    knowledge_base_ids: []
  }
];

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

  // Use React Query for categories
  const { 
    data: categories = [], 
    isLoading: isLoadingCategories 
  } = useQuery({
    queryKey: ['template-categories'],
    queryFn: async () => {
      const response = await templateService.getCategories();
      return response;
    },
    staleTime: 30000, // 30 seconds
  });

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
    if (search.tab === 'my-agents') {
      setActiveTab(2); // Switch to "My Agents" tab
    } else if (search.tab === 'templates') {
      setActiveTab(0); // Switch to "Templates" tab
    } else if (search.tab === 'new-agent') {
      setActiveTab(1); // Switch to "New Agent" tab
    }
  }, [search.tab]);

  const handleDeploy = async (templateId: string, selectedAgents?: string[]) => {
    try {
      setIsDeploying(true);
      setError(null);
      
      const result = await templateService.deployTemplate(templateId, selectedAgents);
      console.log('Deployment result:', result);
      
      if (result.success) {
        const agentCount = selectedAgents ? selectedAgents.length : 'all';
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

  // Mutation for creating demo agents
  const createDemoMutation = useMutation({
    mutationFn: async () => {
      const results = [];
      setDemoProgress([]);
      
      for (const demoAgent of BANKING_DEMO_AGENTS) {
        try {
          // Create the agent without persona field
          const createdAgent = await createAgent(demoAgent as NewAgent);
          
          results.push(createdAgent);
          setDemoProgress(prev => [...prev, `✅ Created ${demoAgent.name}`]);
          
          // Small delay to show progress
          await new Promise(resolve => setTimeout(resolve, 500));
        } catch (error) {
          console.error(`Failed to create ${demoAgent.name}:`, error);
          setDemoProgress(prev => [...prev, `❌ Failed to create ${demoAgent.name}`]);
        }
      }
      
      return results;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['agents'] });
      setDemoProgress(prev => [...prev, '🏦 Banking templates deployed successfully!']);
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

  const handleCreateDemo = () => {
    setShowDemoModal(true);
    createDemoMutation.mutate();
  };

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  return (
    <PageSection>
      <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
        <FlexItem>
          <Title headingLevel="h1">AI Agent Management</Title>
          <p>Create, deploy, and manage intelligent AI agents for your organization.</p>
        </FlexItem>

        <FlexItem>
          <Tabs 
            activeKey={activeTab} 
            onSelect={(_, tabIndex) => setActiveTab(tabIndex as number)}
          >
            <Tab 
              eventKey={0} 
              title={<TabTitleText icon={<BookOpenIcon />}>Templates</TabTitleText>}
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
              title={<TabTitleText icon={<PlusIcon />}>New Agent</TabTitleText>}
            >
              <div style={{ padding: '1rem 0' }}>
                <NewAgentCard />
              </div>
            </Tab>
            
            <Tab 
              eventKey={2} 
              title={<TabTitleText icon={<UsersIcon />}>My Agents</TabTitleText>}
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
        title="Banking Templates"
        isOpen={showDemoModal}
        onClose={() => !createDemoMutation.isPending && setShowDemoModal(false)}
        hasNoBodyWrapper
      >
        <ModalHeader title="Setting Up Banking Agent Templates" />
        <ModalBody>
          <Flex direction={{ default: 'column' }} gap={{ default: 'gapSm' }}>
            <FlexItem>
              <p>Creating specialized banking agents from templates...</p>
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
                <div>🏦 Deploying banking templates...</div>
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