import { AgentList } from '@/components/agent-list';
import { NewAgentCard } from '@/components/new-agent-card';
import { SuiteDetails } from '@/types/agent';

import {
  Flex,
  FlexItem,
  PageSection,
  Title,
  Tabs,
  Tab,
  TabTitleText,
  Card,
  CardBody,
  Button,
  Label,
  Spinner,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Checkbox,
} from '@patternfly/react-core';
import { HomeIcon, RobotIcon, CubeIcon } from '@patternfly/react-icons';
import { SUITE_ICONS, CATEGORY_ICONS } from '@/utils/icons';
import { createFileRoute } from '@tanstack/react-router';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getSuitesByCategory,
  getSuiteDetails as getSuiteDetailsApi,
  initializeSuite,
  getCategoriesInfo,
  initializeAgentFromTemplate,
} from '@/services/agent-templates';

export const Route = createFileRoute('/_protected/_admin/config/agents')({
  component: Agents,
});

// --- 5. Main AgentsPage Component ---
export function Agents() {
  const [activeTabKey, setActiveTabKey] = useState<string | number>(0);

  const handleTabClick = (_event: React.MouseEvent, tabIndex: string | number) => {
    setActiveTabKey(tabIndex);
  };

  return (
    <PageSection>
      <div style={{ position: 'relative' }}>
        <style>{`
          .agents-page-tabs .pf-v6-c-tabs__item.pf-m-current .pf-v6-c-tabs__link {
            color: var(--pf-v6-global--primary-color--100, #0066cc) !important;
            border-bottom-color: var(--pf-v6-global--primary-color--100, #0066cc) !important;
            border-bottom-width: 2px !important;
          }
          .agents-page-tabs .pf-v6-c-tabs__item.pf-m-current {
            border-bottom: 2px solid var(--pf-v6-global--primary-color--100, #0066cc) !important;
          }
        `}</style>
      </div>
      <Tabs
        className="agents-page-tabs"
        activeKey={activeTabKey}
        onSelect={handleTabClick}
        aria-label="Agent management tabs"
      >
        <Tab
          eventKey={0}
          title={
            <TabTitleText>
              <RobotIcon style={{ marginRight: '8px' }} />
              My Agents
            </TabTitleText>
          }
        >
          <div style={{ padding: '24px 0' }}>
            <MyAgents />
          </div>
        </Tab>
        <Tab
          eventKey={1}
          title={
            <TabTitleText>
              <CubeIcon style={{ marginRight: '8px' }} />
              Agent Templates
            </TabTitleText>
          }
        >
          <div style={{ padding: '24px 0' }}>
            <AgentTemplates />
          </div>
        </Tab>
      </Tabs>
    </PageSection>
  );
}

// Suite and category icon mappings are now shared via '@/utils/icons'

// Agent Templates Component
function AgentTemplates() {
  const [showDeployModal, setShowDeployModal] = useState(false);
  const [showSelectionModal, setShowSelectionModal] = useState(false);
  const [selectedSuite, setSelectedSuite] = useState<string | null>(null);
  const [deployProgress, setDeployProgress] = useState<string[]>([]);
  const [selectedTemplateIds, setSelectedTemplateIds] = useState<string[]>([]);
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
  const { data: suiteDetailsMap } = useQuery<Record<string, SuiteDetails>>({
    queryKey: ['suite-details', suitesByCategory],
    queryFn: async () => {
      if (!suitesByCategory) return {};

      const detailsMap: Record<string, SuiteDetails> = {};
      for (const [category, suiteIds] of Object.entries(suitesByCategory)) {
        for (const suiteId of suiteIds) {
          try {
            const details = await getSuiteDetailsApi(suiteId);
            detailsMap[suiteId] = {
              ...details,
              name: details.name,
              title: details.name,
              icon: SUITE_ICONS[suiteId] || <HomeIcon style={{ color: '#8A2BE2' }} />,
              agents: details.agent_names,
              agentCount: details.agent_count,
              templateIds: details.template_ids,
              category,
            };
          } catch (error) {
            console.error(`Failed to fetch details for suite ${suiteId}:`, error);
            detailsMap[suiteId] = {
              id: suiteId,
              name: suiteId.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
              title: suiteId.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
              description: `Specialized agents for ${category} services.`,
              icon: SUITE_ICONS[suiteId] || <HomeIcon style={{ color: '#8A2BE2' }} />,
              agents: ['Agent 1', 'Agent 2', 'Agent 3'],
              agentCount: 3,
              category,
            };
          }
        }
      }
      return detailsMap;
    },
    enabled: !!suitesByCategory,
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
          setDeployProgress((prev) => [...prev, `✅ Deployed ${result.agent_name}`]);
        } else if (result.status === 'skipped') {
          setDeployProgress((prev) => [
            ...prev,
            `ℹ️ ${result.message || `Already deployed ${result.agent_name} — skipped`}`,
          ]);
        } else {
          setDeployProgress((prev) => [
            ...prev,
            `❌ Failed to deploy ${result.agent_name}: ${result.message}`,
          ]);
        }
      }
      await queryClient.invalidateQueries({ queryKey: ['agents'] });
    },
    onError: (error) => {
      setDeployProgress((prev) => [
        ...prev,
        `❌ Deployment failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
      ]);
    },
  });

  const handleDeploySuite = (suiteId: string) => {
    setSelectedSuite(suiteId);
    // Preselect all templates for this suite
    const suite: SuiteDetails | undefined = suiteDetailsMap?.[suiteId];
    if (suite && Array.isArray(suite.templateIds)) {
      setSelectedTemplateIds([...suite.templateIds]);
    } else {
      setSelectedTemplateIds([]);
    }
    setShowSelectionModal(true);
  };

  const getSuiteDetails = (suiteId: string): SuiteDetails | null => {
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
        Professional, pre-configured AI agent suites ready for immediate deployment. Each template
        includes multiple specialized agents working together seamlessly.
      </p>
      <div style={{ marginBottom: '16px' }}>
        <span
          style={{
            border: '1px solid #0066CC',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '12px',
            color: '#0066CC',
            marginRight: '8px',
          }}
        >
          {totalTemplates} Templates Available
        </span>
        <span
          style={{
            border: '1px solid #0066CC',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '12px',
            color: '#0066CC',
            marginRight: '8px',
          }}
        >
          Enterprise Ready
        </span>
        <span
          style={{
            border: '1px solid #0066CC',
            borderRadius: '4px',
            padding: '4px 8px',
            fontSize: '12px',
            color: '#0066CC',
          }}
        >
          Instant Deploy
        </span>
      </div>

      {/* Template Sections by Category */}
      {suitesByCategory &&
        categoriesInfo &&
        Object.entries(suitesByCategory).map(([category, suiteIds]) => {
          const categoryInfo = categoriesInfo[category];
          if (!categoryInfo) return null;

          const categoryIcon = CATEGORY_ICONS[category] || CATEGORY_ICONS.default;

          return (
            <div key={category} style={{ marginBottom: '40px' }}>
              <div style={{ marginBottom: '16px' }}>
                <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
                  {categoryIcon}
                  <Title headingLevel="h3">{categoryInfo.name}</Title>
                  <Label color="blue" variant="outline">
                    {suiteIds.length} templates
                  </Label>
                  <Label color="green" variant="outline">
                    Pre-configured
                  </Label>
                  <Label color="green" variant="outline">
                    Ready to use
                  </Label>
                </Flex>
              </div>

              <p style={{ marginBottom: '24px', color: '#6A6E73' }}>{categoryInfo.description}</p>

              {/* Suite Cards */}
              <Flex gap={{ default: 'gapMd' }} style={{ flexWrap: 'wrap' }}>
                {suiteIds.map((suiteId) => {
                  const suite = getSuiteDetails(suiteId);
                  if (!suite) return null;

                  return (
                    <FlexItem
                      key={suiteId}
                      style={{ minWidth: '300px', maxWidth: '350px', flex: '1 1 300px' }}
                    >
                      <Card style={{ height: '400px', display: 'flex', flexDirection: 'column' }}>
                        <CardBody style={{ flex: '1', display: 'flex', flexDirection: 'column' }}>
                          <Flex
                            direction={{ default: 'column' }}
                            gap={{ default: 'gapMd' }}
                            style={{ height: '100%' }}
                          >
                            <FlexItem>
                              <Flex
                                alignItems={{ default: 'alignItemsCenter' }}
                                gap={{ default: 'gapSm' }}
                              >
                                {suite.icon}
                                <Title headingLevel="h4">{suite.title}</Title>
                              </Flex>
                            </FlexItem>

                            <FlexItem>
                              <p>{suite.description}</p>
                            </FlexItem>

                            <FlexItem>
                              <p
                                style={{
                                  fontWeight: 'bold',
                                  marginBottom: '8px',
                                  fontSize: '14px',
                                }}
                              >
                                Included Agents:
                              </p>
                              <Flex gap={{ default: 'gapXs' }} style={{ flexWrap: 'wrap' }}>
                                {Array.isArray(suite.agents) &&
                                  suite.agents.map((agent: string) => (
                                    <Label
                                      key={agent}
                                      color="blue"
                                      variant="outline"
                                      style={{ marginBottom: '4px' }}
                                    >
                                      {agent}
                                    </Label>
                                  ))}
                              </Flex>
                            </FlexItem>

                            <FlexItem style={{ marginTop: 'auto' }}>
                              <p
                                style={{ color: '#6A6E73', fontSize: '14px', marginBottom: '16px' }}
                              >
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

      {/* Selection Modal */}
      {showSelectionModal && selectedSuite && (
        <Modal
          isOpen={showSelectionModal}
          onClose={() => setShowSelectionModal(false)}
          variant="medium"
          aria-labelledby="deploy-suite-select-title"
        >
          <ModalHeader
            title={`Deploy ${selectedSuite
              .replace(/_/g, ' ')
              .replace(/\b\w/g, (l) => l.toUpperCase())}`}
            labelId="deploy-suite-select-title"
          />
          <ModalBody>
            {(() => {
              const suite = suiteDetailsMap?.[selectedSuite];
              const ids: string[] = suite?.templateIds ?? [];
              const names: string[] = suite?.agents ?? [];
              const pairs: Array<{ id: string; name: string }> = ids.map(
                (id: string, idx: number) => ({ id, name: names[idx] ?? id })
              );
              const allSelected: boolean =
                selectedTemplateIds.length === pairs.length && pairs.length > 0;
              return (
                <div>
                  <div style={{ marginBottom: '12px' }}>
                    <Checkbox
                      id="select-all-templates"
                      label={`Select All (${pairs.length} agents)`}
                      isChecked={allSelected}
                      onChange={(_event, checked: boolean) => {
                        setSelectedTemplateIds(checked ? pairs.map((p) => p.id) : []);
                      }}
                    />
                  </div>
                  <div style={{ display: 'grid', gap: 8 }}>
                    {pairs.map((pair: { id: string; name: string }) => (
                      <div
                        key={pair.id}
                        style={{ border: '1px solid #d2d2d2', borderRadius: 6, padding: 12 }}
                      >
                        <Checkbox
                          id={`template-${pair.id}`}
                          label={pair.name}
                          isChecked={selectedTemplateIds.includes(pair.id)}
                          onChange={(_event, checked: boolean) => {
                            setSelectedTemplateIds((prev: string[]) => {
                              if (checked) return Array.from(new Set([...prev, pair.id]));
                              return prev.filter((id: string) => id !== pair.id);
                            });
                          }}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}
          </ModalBody>
          <ModalFooter className="pf-v6-u-justify-content-flex-end">
            <Button variant="link" onClick={() => setShowSelectionModal(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (!selectedSuite) return;
                setShowSelectionModal(false);
                setShowDeployModal(true);
                deployMutation.mutate(selectedSuite);
              }}
              isDisabled={deployMutation.isPending || selectedTemplateIds.length === 0}
            >
              Deploy All
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                void (async () => {
                  if (!selectedSuite) return;
                  setShowSelectionModal(false);
                  setShowDeployModal(true);
                  setDeployProgress([]);
                  try {
                    const ids: string[] = selectedTemplateIds;
                    for (const id of ids) {
                      try {
                        const result = await initializeAgentFromTemplate({
                          template_name: id,
                          include_knowledge_base: true,
                        });
                        if (result.status === 'success') {
                          setDeployProgress((prev: string[]) => [
                            ...prev,
                            `✅ Deployed ${result.agent_name}`,
                          ]);
                        } else if (result.status === 'skipped') {
                          setDeployProgress((prev: string[]) => [
                            ...prev,
                            `ℹ️ ${result.message || `Already deployed ${result.agent_name} — skipped`}`,
                          ]);
                        } else {
                          setDeployProgress((prev: string[]) => [
                            ...prev,
                            `❌ Failed to deploy ${result.agent_name}: ${result.message}`,
                          ]);
                        }
                      } catch (e) {
                        setDeployProgress((prev: string[]) => [
                          ...prev,
                          `❌ Failed to deploy ${id}: ${e instanceof Error ? e.message : 'Unknown error'}`,
                        ]);
                      }
                    }
                    await queryClient.invalidateQueries({ queryKey: ['agents'] });
                  } finally {
                  }
                })();
              }}
              isDisabled={selectedTemplateIds.length === 0}
            >
              {`Deploy Selected (${selectedTemplateIds.length})`}
            </Button>
          </ModalFooter>
        </Modal>
      )}

      {/* Deploy Progress Modal */}
      {showDeployModal && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
          }}
        >
          <Card style={{ width: '400px', maxHeight: '80vh', overflow: 'auto' }}>
            <CardBody>
              <Title headingLevel="h3" style={{ marginBottom: '16px' }}>
                Deploying{' '}
                {selectedSuite
                  ? selectedSuite.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
                  : 'Suite'}
              </Title>
              <div style={{ marginBottom: '16px' }}>
                {deployProgress.length === 0 && deployMutation.isPending && (
                  <p>Initializing deployment...</p>
                )}
                {deployProgress.map((progress, index) => (
                  <div
                    key={index}
                    style={{
                      fontFamily: 'monospace',
                      fontSize: '14px',
                      marginBottom: '4px',
                      color: progress.includes('✅')
                        ? '#3E8635'
                        : progress.includes('❌')
                          ? '#C9190B'
                          : progress.includes('ℹ️')
                            ? '#0066CC'
                            : '#6A6E73',
                    }}
                  >
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

// My Agents Component
function MyAgents() {
  return (
    <div>
      <Flex direction={{ default: 'column' }} gap={{ default: 'gapLg' }}>
        <FlexItem>
          <Title headingLevel="h2">My Agents</Title>
          <p style={{ marginBottom: '24px', color: '#6A6E73' }}>
            View and manage your deployed AI agents.
          </p>
        </FlexItem>
        <FlexItem>
          <NewAgentCard />
        </FlexItem>
        <FlexItem>
          <AgentList />
        </FlexItem>
      </Flex>
    </div>
  );
}
