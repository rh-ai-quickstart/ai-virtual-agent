import { AgentList } from '@/components/agent-list';
import { NewAgentCard } from '@/components/new-agent-card';
import { ToolAssociationInfo, samplingStrategy } from '@/types';
import { Flex, FlexItem, PageSection, Title, Tabs, Tab, TabTitleText, Card, CardBody, Button, Label, Spinner } from '@patternfly/react-core';
import { HomeIcon, BriefcaseIcon, BuildingIcon, PlaneIcon } from '@patternfly/react-icons';
import { createFileRoute } from '@tanstack/react-router';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getSuitesByCategory, getSuiteDetails as getSuiteDetailsApi, initializeSuite, getCategoriesInfo } from '@/services/agent-templates';

// Type def for fetching agents
export interface Agent {
  id: string;
  name: string;
  agent_type?: string;
  model_name: string;
  prompt: string;
  tools: ToolAssociationInfo[];
  knowledge_base_ids: string[];
  input_shields: string[];
  output_shields: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
  sampling_strategy?: samplingStrategy;
  temperature?: number;
  top_p?: number;
  top_k?: number;
  max_tokens?: number;
  repetition_penalty?: number;
}

// Type def for creating agents
export interface NewAgent {
  name: string;
  agent_type?: string;
  model_name: string;
  prompt: string;
  tools: ToolAssociationInfo[];
  knowledge_base_ids: string[];
  sampling_strategy?: samplingStrategy;
  temperature?: number;
  top_p?: number;
  top_k?: number;
  max_tokens?: number;
  repetition_penalty?: number;
  input_shields: string[];
  output_shields: string[];
}

export const Route = createFileRoute('/config/agents')({
  component: Agents,
});

// --- 5. Main AgentsPage Component ---
export function Agents() {
  const [activeTabKey, setActiveTabKey] = useState<string | number>(0);

  const handleTabClick = (_event: any, tabIndex: string | number) => {
    setActiveTabKey(tabIndex);
  };

  return (
    <PageSection>
      <Flex direction={{ default: 'column' }} gap={{ default: 'gapLg' }}>
        {/* Header */}
        <FlexItem>
          <Title headingLevel="h1">AI Agent Management</Title>
          <p style={{ marginTop: '8px', color: '#6A6E73' }}>
            Create, deploy, and manage intelligent AI agents for your organization.
          </p>
        </FlexItem>

        {/* Tabs */}
        <FlexItem>
          <Tabs
            activeKey={activeTabKey}
            onSelect={handleTabClick}
            aria-label="Agent management tabs"
          >
            <Tab eventKey={0} title={<TabTitleText>Template Catalog</TabTitleText>}>
              <div style={{ padding: '24px 0' }}>
                <TemplateCatalog />
              </div>
            </Tab>
            <Tab eventKey={1} title={<TabTitleText>Create Custom</TabTitleText>}>
              <div style={{ padding: '24px 0' }}>
                <CreateCustomAgent />
              </div>
            </Tab>
            <Tab eventKey={2} title={<TabTitleText>Your Agents</TabTitleText>}>
              <div style={{ padding: '24px 0' }}>
                <YourAgents />
              </div>
            </Tab>
          </Tabs>
        </FlexItem>
      </Flex>
    </PageSection>
  );
}

// Icon mapping for different suite types
const SUITE_ICONS: Record<string, React.ReactNode> = {
  core_banking: <HomeIcon style={{ color: '#8A2BE2' }} />,
  wealth_management: <BriefcaseIcon style={{ color: '#8B4513' }} />,
  business_banking: <BuildingIcon style={{ color: '#4169E1' }} />,
  travel_hospitality: <PlaneIcon style={{ color: '#FF6B35' }} />
};

// Icon mapping for different category types
const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  banking: <HomeIcon style={{ color: '#8A2BE2', fontSize: '24px' }} />,
  travel: <PlaneIcon style={{ color: '#FF6B35', fontSize: '24px' }} />,
  default: <HomeIcon style={{ color: '#6A6E73', fontSize: '24px' }} />
};

// Template Catalog Component
function TemplateCatalog() {
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [selectedSuite, setSelectedSuite] = useState<string | null>(null);
  const [deployProgress, setDeployProgress] = useState<string[]>([]);
  const queryClient = useQueryClient();

  // Query for suites by category
  const { data: suitesByCategory, isLoading: suitesLoading } = useQuery({
    queryKey: ['suites-by-category'],
    queryFn: getSuitesByCategory,
  });

  // Query for categories info
  const { data: categoriesInfo, isLoading: categoriesLoading } = useQuery({
    queryKey: ['categories-info'],
    queryFn: getCategoriesInfo,
  });

  // Query for suite details
  const { data: suiteDetailsMap } = useQuery({
    queryKey: ['suite-details', suitesByCategory],
    queryFn: async () => {
      if (!suitesByCategory) return {};
      
      const detailsMap: Record<string, any> = {};
      for (const [category, suiteIds] of Object.entries(suitesByCategory)) {
        for (const suiteId of suiteIds) {
          try {
            const details = await getSuiteDetailsApi(suiteId);
            detailsMap[suiteId] = {
              ...details,
              title: details.name,
              icon: SUITE_ICONS[suiteId] || <HomeIcon style={{ color: '#8A2BE2' }} />,
              agents: details.agent_names,
              agentCount: details.agent_count,
              category
            };
          } catch (error) {
            console.error(`Failed to fetch details for suite ${suiteId}:`, error);
            detailsMap[suiteId] = {
              id: suiteId,
              title: suiteId.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
              description: `Specialized agents for ${category} services.`,
              icon: SUITE_ICONS[suiteId] || <HomeIcon style={{ color: '#8A2BE2' }} />,
              agents: ['Agent 1', 'Agent 2', 'Agent 3'],
              agentCount: 3,
              category
            };
          }
        }
      }
      return detailsMap;
    },
    enabled: !!suitesByCategory
  });

  // Mutation for deploying suites
  const deployMutation = useMutation({
    mutationFn: async (suiteId: string) => {
      setDeployProgress([]);
      const results = await initializeSuite(suiteId);
      return results;
    },
    onSuccess: async (results) => {
      for (const result of results) {
        if (result.status === 'success') {
          setDeployProgress(prev => [...prev, `✅ Deployed ${result.agent_name}`]);
        } else {
          setDeployProgress(prev => [...prev, `❌ Failed to deploy ${result.agent_name}: ${result.message}`]);
        }
      }
      await queryClient.invalidateQueries({ queryKey: ['agents'] });
      setTimeout(() => {
        setShowDeployModal(false);
        setDeployProgress([]);
        setSelectedSuite(null);
      }, 2000);
    },
    onError: (error) => {
      setDeployProgress(prev => [...prev, `❌ Deployment failed: ${error instanceof Error ? error.message : 'Unknown error'}`]);
    }
  });

  const handleDeploySuite = (suiteId: string) => {
    setSelectedSuite(suiteId);
    setShowDeployModal(true);
    deployMutation.mutate(suiteId);
  };

  const getSuiteDetails = (suiteId: string) => {
    return suiteDetailsMap?.[suiteId] || null;
  };

  if (suitesLoading || categoriesLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <Spinner size="lg" />
        <p style={{ marginTop: '16px' }}>Loading templates...</p>
      </div>
    );
  }

  const totalTemplates = suitesByCategory ? Object.values(suitesByCategory).flat().length : 0;

  return (
    <div>
      <Title headingLevel="h2">AI Agent Templates</Title>
      <p style={{ marginBottom: '24px', color: '#6A6E73' }}>
        Professional, pre-configured AI agent suites ready for immediate deployment. 
        Each template includes multiple specialized agents working together seamlessly.
      </p>
      <div style={{ marginBottom: '16px' }}>
        <span style={{ 
          border: '1px solid #0066CC', 
          borderRadius: '4px', 
          padding: '4px 8px', 
          fontSize: '12px', 
          color: '#0066CC',
          marginRight: '8px'
        }}>
          {totalTemplates} Templates Available
        </span>
        <span style={{ 
          border: '1px solid #0066CC', 
          borderRadius: '4px', 
          padding: '4px 8px', 
          fontSize: '12px', 
          color: '#0066CC',
          marginRight: '8px'
        }}>
          Enterprise Ready
        </span>
        <span style={{ 
          border: '1px solid #0066CC', 
          borderRadius: '4px', 
          padding: '4px 8px', 
          fontSize: '12px', 
          color: '#0066CC'
        }}>
          Instant Deploy
        </span>
      </div>

      {/* Template Sections by Category */}
      {suitesByCategory && categoriesInfo && Object.entries(suitesByCategory).map(([category, suiteIds]) => {
        const categoryInfo = categoriesInfo[category];
        if (!categoryInfo) return null;

        const categoryIcon = CATEGORY_ICONS[category] || CATEGORY_ICONS.default;

        return (
          <div key={category} style={{ marginBottom: '40px' }}>
            <div style={{ marginBottom: '16px' }}>
              <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
                {categoryIcon}
                <Title headingLevel="h3">{categoryInfo.name}</Title>
                <Label color="blue" variant="outline">{suiteIds.length} templates</Label>
                <Label color="green" variant="outline">Pre-configured</Label>
                <Label color="green" variant="outline">Ready to use</Label>
              </Flex>
            </div>
            
            <p style={{ marginBottom: '24px', color: '#6A6E73' }}>{categoryInfo.description}</p>

            {/* Suite Cards */}
            <Flex gap={{ default: 'gapMd' }} style={{ flexWrap: 'wrap' }}>
              {suiteIds.map((suiteId) => {
                const suite = getSuiteDetails(suiteId);
                if (!suite) return null;

                return (
                  <FlexItem key={suiteId} style={{ minWidth: '300px', maxWidth: '350px', flex: '1 1 300px' }}>
                    <Card style={{ height: '400px', display: 'flex', flexDirection: 'column' }}>
                      <CardBody style={{ flex: '1', display: 'flex', flexDirection: 'column' }}>
                        <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }} style={{ height: '100%' }}>
                          <FlexItem>
                            <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
                              {suite.icon}
                              <Title headingLevel="h4">{suite.title}</Title>
                            </Flex>
                          </FlexItem>
                          
                          <FlexItem>
                            <p>{suite.description}</p>
                          </FlexItem>

                          <FlexItem>
                            <p style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '14px' }}>
                              Included Agents:
                            </p>
                            <Flex gap={{ default: 'gapXs' }} style={{ flexWrap: 'wrap' }}>
                              {suite.agents.map((agent: string) => (
                                <Label key={agent} color="blue" variant="outline" style={{ marginBottom: '4px' }}>
                                  {agent}
                                </Label>
                              ))}
                            </Flex>
                          </FlexItem>

                          <FlexItem style={{ marginTop: 'auto' }}>
                            <p style={{ color: '#6A6E73', fontSize: '14px', marginBottom: '16px' }}>
                              {suite.agentCount} agents
                            </p>
                          </FlexItem>

                          <FlexItem>
                            <Button
                              variant="primary"
                              onClick={() => handleDeploySuite(suiteId)}
                              isDisabled={deployMutation.isPending}
                              isBlock
                            >
                              Deploy Suite
                            </Button>
                          </FlexItem>
                        </Flex>
                      </CardBody>
                    </Card>
                  </FlexItem>
                );
              })}
            </Flex>
          </div>
        );
      })}

      {/* Deploy Modal */}
      {showDeployModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <Card style={{ width: '400px', maxHeight: '80vh', overflow: 'auto' }}>
            <CardBody>
              <Title headingLevel="h3" style={{ marginBottom: '16px' }}>
                Deploying {selectedSuite ? selectedSuite.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) : 'Suite'}
              </Title>
              <div style={{ marginBottom: '16px' }}>
                {deployProgress.length === 0 && deployMutation.isPending && (
                  <p>Initializing deployment...</p>
                )}
                {deployProgress.map((progress, index) => (
                  <div key={index} style={{ 
                    fontFamily: 'monospace', 
                    fontSize: '14px', 
                    marginBottom: '4px',
                    color: progress.includes('✅') ? '#3E8635' : progress.includes('❌') ? '#C9190B' : '#6A6E73'
                  }}>
                    {progress}
                  </div>
                ))}
              </div>
              <Button
                variant="secondary"
                onClick={() => setShowDeployModal(false)}
                isDisabled={deployMutation.isPending}
                isBlock
              >
                {deployMutation.isPending ? 'Deploying...' : 'Close'}
              </Button>
            </CardBody>
          </Card>
        </div>
      )}
    </div>
  );
}

// Create Custom Agent Component
function CreateCustomAgent() {
  return (
    <div>
      <Title headingLevel="h2">Create Custom Agent</Title>
      <p style={{ marginBottom: '24px', color: '#6A6E73' }}>
        Build a custom AI agent tailored to your specific needs and requirements.
      </p>
      <NewAgentCard />
    </div>
  );
}

// Your Agents Component
function YourAgents() {
  return (
    <div>
      <Title headingLevel="h2">Your Agents</Title>
      <p style={{ marginBottom: '24px', color: '#6A6E73' }}>
        View and manage your deployed AI agents.
      </p>
      <AgentList />
    </div>
  );
}
