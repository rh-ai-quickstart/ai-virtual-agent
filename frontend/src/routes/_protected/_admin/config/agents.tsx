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
  FormGroup,
  FormSelect,
  FormSelectOption,
  FormHelperText,
  Alert,
} from '@patternfly/react-core';
import { HomeIcon, RobotIcon, CubeIcon } from '@patternfly/react-icons';
import { SUITE_ICONS, CATEGORY_ICONS } from '@/utils/icons';
import { createFileRoute } from '@tanstack/react-router';
import { useEffect, useMemo, useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getSuitesByCategory,
  getSuiteDetails as getSuiteDetailsApi,
  initializeSuite,
  getCategoriesInfo,
  initializeAgentFromTemplate,
  getTemplateDetails as getTemplateDetailsApi,
} from '@/services/agent-templates';
import { useModels, useTools } from '@/hooks';
import { MultiSelect, CustomSelectOptionProps } from '@/components/multi-select';
import { ToolGroup } from '@/types';
import { TemplateInitializationRequest } from '@/types/agent';

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
  // Per-template overrides state
  const [templateOverrides, setTemplateOverrides] = useState<
    Record<
      string,
      {
        model_name: string;
        tool_ids: string[];
        template_model?: string;
        template_tool_ids?: string[];
      }
    >
  >({});
  const [templatesPrefetching, setTemplatesPrefetching] = useState<boolean>(false);

  // Data for models and tools
  const { models, isLoadingModels, modelsError } = useModels();
  const { tools, isLoading: isLoadingTools, error: toolsError } = useTools();
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
    setTemplateOverrides({});
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

  // When selectedTemplateIds changes, add defaults for newly selected templates (preserve existing overrides)
  useEffect(() => {
    if (selectedTemplateIds.length === 0) return;

    setTemplateOverrides((prev) => {
      const next = { ...prev };

      // For each selected template, set up default overrides immediately
      for (const id of selectedTemplateIds) {
        if (!next[id]) {
          // We'll populate with template details when available, but set up structure now
          next[id] = {
            model_name: '',
            tool_ids: [],
            template_model: '',
            template_tool_ids: [],
          };
        }
      }

      return next;
    });

    // Prefetch template details in parallel using React Query
    setTemplatesPrefetching(true);
    Promise.all(
      selectedTemplateIds.map(async (id) => {
        try {
          const t = await getTemplateDetailsApi(id);
          return { id, t } as const;
        } catch (_e) {
          return { id, t: null } as const;
        }
      })
    )
      .then((details) => {
        setTemplateOverrides((prev) => {
          const next = { ...prev };
          for (const { id, t } of details) {
            if (!t) continue;
            // Default tools from template
            const defaultToolIds = (t.tools || []).map((x) => x.toolgroup_id);
            // Tentative model: will be reconciled against available models below
            const templateModel = t.model_name || '';

            // Update with template details, preserving any user edits.
            // Keep active selection empty unless user picked one; reconcile later against available models
            next[id] = {
              model_name: next[id]?.model_name || '',
              tool_ids: next[id]?.tool_ids?.length ? next[id].tool_ids : defaultToolIds,
              template_model: templateModel,
              template_tool_ids: defaultToolIds,
            };
          }
          return next;
        });
        setTemplatesPrefetching(false);
      })
      .catch(() => {
        setTemplatesPrefetching(false);
      });
  }, [selectedTemplateIds]);

  // Reconcile model selection:
  // - If template model exists in the available list, preselect it
  // - Otherwise leave empty and require user selection
  useEffect(() => {
    if (!models || models.length === 0) return;
    const available = new Set(models.map((m) => m.model_name));
    setTemplateOverrides((prev) => {
      const next = { ...prev };
      const keys = new Set<string>([...Object.keys(next), ...selectedTemplateIds]);
      for (const key of keys) {
        const o = next[key] || { model_name: '', tool_ids: [], template_model: '' };

        // If user already picked a valid model, keep it
        if (o.model_name && available.has(o.model_name)) {
          next[key] = o;
          continue;
        }

        const templateModel = o.template_model || '';
        if (templateModel && available.has(templateModel)) {
          next[key] = { ...o, model_name: templateModel };
        } else {
          next[key] = { ...o, model_name: '' };
        }
      }
      return next;
    });
  }, [models, selectedTemplateIds]);

  // Tools options for MultiSelect
  const toolsOptions: CustomSelectOptionProps[] = useMemo(() => {
    if (isLoadingTools) {
      return [
        {
          value: 'loading_tools',
          children: 'Loading tool groups...',
          isDisabled: true,
          id: 'loading_tools_opt',
        },
      ];
    }
    if (toolsError) {
      return [
        {
          value: 'error_tools',
          children: 'Error loading tool groups',
          isDisabled: true,
          id: 'error_tools_opt',
        },
      ];
    }
    if (!tools || tools.length === 0) {
      return [
        {
          value: 'no_tools_options',
          children: 'No tool groups available',
          isDisabled: true,
          id: 'no_tools_options_opt',
        },
      ];
    }
    return tools.map((tool: ToolGroup) => ({
      value: tool.toolgroup_id,
      children: tool.name,
      id: `tools-option-${tool.toolgroup_id}`,
    }));
  }, [tools, isLoadingTools, toolsError]);

  const modelOptions = useMemo(() => {
    if (isLoadingModels) {
      return [<FormSelectOption key="loading" value="" label="Loading models..." isDisabled />];
    }
    if (modelsError) {
      return [<FormSelectOption key="error" value="" label="Error loading models" isDisabled />];
    }
    const opts = [
      <FormSelectOption key="placeholder" value="" label="Select a model" isDisabled />,
    ];
    for (const m of models || []) {
      opts.push(<FormSelectOption key={m.model_name} value={m.model_name} label={m.model_name} />);
    }
    return opts;
  }, [models, isLoadingModels, modelsError]);

  // Validation helpers
  const areModelsReady = !isLoadingModels && !modelsError && (models?.length || 0) > 0;

  // Precompute model name sets for validation/use
  const normalize = (s: string) => (s || '').split('/').pop()?.trim().toLowerCase() || '';
  const modelNames = useMemo(() => new Set((models || []).map((m) => m.model_name)), [models]);
  const modelBaseNames = useMemo(
    () => new Set(Array.from(modelNames).map((n) => normalize(n))),
    [modelNames]
  );

  // Centralized model validation function
  const validateModelSelection = useCallback(
    (selectedModel: string): { isValid: boolean } => {
      return {
        isValid: modelNames.has(selectedModel) || modelBaseNames.has(normalize(selectedModel)),
      };
    },
    [modelNames, modelBaseNames]
  );
  const hasModelSelectionErrors = useMemo(() => {
    if (!areModelsReady) return true;

    // If we're still prefetching template data, wait
    if (templatesPrefetching) return true;

    // Check if templateOverrides has been initialized for all selected templates
    const hasUnprocessedTemplates = selectedTemplateIds.some((id) => !(id in templateOverrides));
    if (hasUnprocessedTemplates) return true; // Still processing defaults

    return selectedTemplateIds.some((id) => {
      const selected = templateOverrides[id]?.model_name || '';
      if (!selected) return true;
      const validation = validateModelSelection(selected);
      return !validation.isValid;
    });
  }, [
    areModelsReady,
    selectedTemplateIds,
    templateOverrides,
    templatesPrefetching,
    validateModelSelection,
  ]);

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
          onClose={() => {
            setShowSelectionModal(false);
            setSelectedTemplateIds([]);
            setTemplateOverrides({});
          }}
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
                  {(modelsError || toolsError) && (
                    <div style={{ marginBottom: 12 }}>
                      <Alert
                        variant="danger"
                        isInline
                        title="Error loading models or tools. Please try again."
                      />
                    </div>
                  )}
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

                        {/* Model select */}
                        <div className="pf-v6-u-ml-lg" style={{ marginTop: 8 }}>
                          <FormGroup label="Model" isRequired fieldId={`model-${pair.id}`}>
                            <FormSelect
                              id={`model-${pair.id}`}
                              value={templateOverrides[pair.id]?.model_name || ''}
                              onChange={(_e, value) =>
                                setTemplateOverrides((prev) => ({
                                  ...prev,
                                  [pair.id]: {
                                    ...(prev[pair.id] || { model_name: '', tool_ids: [] }),
                                    model_name: value,
                                  },
                                }))
                              }
                              isDisabled={isLoadingModels || !!modelsError}
                              aria-label={`Select model for ${pair.name}`}
                              validated={(() => {
                                const selected = templateOverrides[pair.id]?.model_name || '';
                                if (!selected) return 'default';
                                if (isLoadingModels || modelsError) return 'default';
                                const validation = validateModelSelection(selected);
                                return validation.isValid ? 'success' : 'error';
                              })()}
                            >
                              {modelOptions}
                            </FormSelect>
                            {(() => {
                              const selected = templateOverrides[pair.id]?.model_name || '';
                              const validation = validateModelSelection(selected);
                              const invalid = selected ? !validation.isValid : false;
                              return invalid ? (
                                <FormHelperText className="pf-v6-u-text-color-status-danger">
                                  {templatesPrefetching || isLoadingModels
                                    ? 'Loading models...'
                                    : 'Select a valid model'}
                                </FormHelperText>
                              ) : null;
                            })()}
                          </FormGroup>
                        </div>

                        {/* Tools multiselect */}
                        <div className="pf-v6-u-ml-lg" style={{ marginTop: 8 }}>
                          <FormGroup label="Tool Groups" fieldId={`tools-${pair.id}`}>
                            <MultiSelect
                              id={`tools-${pair.id}-multiselect`}
                              value={templateOverrides[pair.id]?.tool_ids || []}
                              options={toolsOptions}
                              onBlur={() => {}}
                              onChange={(selectedIds) =>
                                setTemplateOverrides((prev) => ({
                                  ...prev,
                                  [pair.id]: {
                                    ...(prev[pair.id] || { model_name: '', tool_ids: [] }),
                                    tool_ids: selectedIds,
                                  },
                                }))
                              }
                              ariaLabel={`Select tools for ${pair.name}`}
                              isDisabled={isLoadingTools || !!toolsError}
                              placeholder="Type or select tool groups..."
                            />
                          </FormGroup>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })()}
          </ModalBody>
          <ModalFooter className="pf-v6-u-justify-content-flex-end">
            <Button
              variant="link"
              onClick={() => {
                setShowSelectionModal(false);
                setSelectedTemplateIds([]);
                setTemplateOverrides({});
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={() => {
                if (!selectedSuite) return;
                setShowSelectionModal(false);
                setShowDeployModal(true);
                deployMutation.mutate(selectedSuite);
              }}
              isDisabled={
                deployMutation.isPending ||
                selectedTemplateIds.length === 0 ||
                hasModelSelectionErrors
              }
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
                        const overrides = templateOverrides[id] || { model_name: '', tool_ids: [] };

                        // Determine if we should send a model override
                        const templateModel = overrides.template_model || '';
                        const selectedModel = overrides.model_name || '';
                        const modelNames = new Set((models || []).map((m) => m.model_name));
                        const templateModelExists =
                          !!templateModel && modelNames.has(templateModel);
                        const modelOverride = (() => {
                          if (!selectedModel) {
                            return undefined; // nothing selected
                          }
                          if (templateModelExists && selectedModel === templateModel) {
                            return undefined; // same as template
                          }
                          return selectedModel; // either user changed it, or template model doesn't exist
                        })();

                        // Determine if tools changed compared to template defaults
                        const selectedToolIds = overrides.tool_ids || [];
                        const templateToolIds = overrides.template_tool_ids || [];
                        const selectedSet = new Set(selectedToolIds);
                        const templateSet = new Set(templateToolIds);
                        const toolsChanged =
                          selectedToolIds.length !== templateToolIds.length ||
                          [...selectedSet].some((x) => !templateSet.has(x)) ||
                          [...templateSet].some((x) => !selectedSet.has(x));
                        const toolsPayload = toolsChanged
                          ? selectedToolIds.map((toolId) => ({ toolgroup_id: toolId }))
                          : undefined;

                        const payload: TemplateInitializationRequest = {
                          template_name: id,
                          include_knowledge_base: true,
                        };
                        // Keep template default unless user provides one elsewhere
                        if (modelOverride) {
                          payload.model_name = modelOverride;
                        }
                        if (toolsPayload) {
                          payload.tools = toolsPayload;
                        }

                        const result = await initializeAgentFromTemplate(payload);
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
              isDisabled={selectedTemplateIds.length === 0 || hasModelSelectionErrors}
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
