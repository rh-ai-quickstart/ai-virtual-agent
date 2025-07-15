import { Agent, NewAgent } from '@/routes/config/agents';
import { Model, ToolGroup, ToolAssociationInfo, LSKnowledgeBase } from '@/types';
import {
  ActionGroup,
  Button,
  Form,
  FormGroup,
  FormHelperText,
  FormSelect,
  FormSelectOption,
  TextArea,
  TextInput,
  Flex,
  FlexItem,
  Label,
} from '@patternfly/react-core';
import { useForm } from '@tanstack/react-form';
import { Fragment, useMemo } from 'react';
import { CustomSelectOptionProps, MultiSelect } from './multi-select';
import { PaperPlaneIcon, MagicIcon } from '@patternfly/react-icons';

// Banking personas for your demo
const BANKING_PERSONAS = [
  { value: '', label: 'Select a banking role', disabled: true },
  { value: 'compliance_officer', label: 'Compliance Officer', disabled: false },
  { value: 'relationship_manager', label: 'Relationship Manager / Loan Officer', disabled: false },
  { value: 'branch_teller', label: 'Branch Teller / Customer Service Rep', disabled: false },
  { value: 'fraud_analyst', label: 'Fraud Analyst / AML Specialist', disabled: false },
  { value: 'training_lead', label: 'Training Lead / Market Analyst', disabled: false },
  { value: 'it_support', label: 'IT Support / Operations', disabled: false },
];

// NEW: Auto-naming suggestions for each persona
const PERSONA_NAME_SUGGESTIONS: Record<string, string> = {
  'compliance_officer': 'Compliance Policy Assistant',
  'relationship_manager': 'Lending Policy Assistant',
  'branch_teller': 'Customer Service Assistant',
  'fraud_analyst': 'Fraud Detection Assistant',
  'training_lead': 'Training & Market Intelligence Assistant',
  'it_support': 'IT Support Assistant'
};

// NEW: Professional prompts for each persona
const PERSONA_PROMPT_SUGGESTIONS: Record<string, string> = {
  'compliance_officer': 'You are a Compliance Policy Agent for a US bank. You help ensure adherence to US banking regulations including BSA/AML, OFAC, CFPB, OCC, and FDIC guidance. You provide accurate information about compliance procedures, reporting requirements, and regulatory updates.',
  'relationship_manager': 'You are a Lending Policy Assistant for relationship managers and loan officers. You help with credit assessment, lending requests, documentation requirements, and regulatory compliance for loans. You know FHA guidelines, conventional loan requirements, and small business lending procedures.',
  'branch_teller': 'You are a Customer Service Assistant for branch tellers and customer service representatives. You help with day-to-day customer queries about product fees, account policies, transaction processing, and regulatory timelines. You provide accurate information about bank products and services.',
  'fraud_analyst': 'You are a Fraud Detection Assistant for fraud analysts and AML specialists. You help review alerts for suspicious transactions, investigate AML/BSA/OFAC red flags, and ensure reporting compliance. You provide guidance on escalation procedures and regulatory requirements.',
  'training_lead': 'You are a Training & Market Intelligence Assistant for training leads and analysts. You help keep staff current on new US regulations, industry certifications, and market developments. You provide information about regulatory updates, certification requirements, and industry best practices.',
  'it_support': 'You are an IT Support Assistant for banking operations. You help support banking employees with system/process issues and ensure adherence to IT policies. You provide guidance on password resets, system access, security protocols, and technical procedures.'
};

interface ModelsFieldProps {
  models: Model[];
  isLoadingModels: boolean;
  modelsError: Error | null;
}

interface KnowledgeBasesFieldProps {
  knowledgeBases: LSKnowledgeBase[];
  isLoadingKnowledgeBases: boolean;
  knowledgeBasesError: Error | null;
}

interface ToolsFieldProps {
  tools: ToolGroup[];
  isLoadingTools: boolean;
  toolsError: Error | null;
}

interface AgentFormProps {
  defaultAgentProps?: Agent | undefined;
  modelsProps: ModelsFieldProps;
  knowledgeBasesProps: KnowledgeBasesFieldProps;
  toolsProps: ToolsFieldProps;
  onSubmit: (values: NewAgent & { persona?: string }) => void;
  isSubmitting: boolean;
  onCancel: () => void;
}

// Form interface for internal form state (user-friendly)
interface AgentFormData {
  name: string;
  model_name: string;
  prompt: string;
  persona: string;
  knowledge_base_ids: string[];
  tool_ids: string[];
}

// Helper functions to convert between formats
const convertAgentToFormData = (agent: Agent | undefined): AgentFormData => {
  if (!agent) {
    return {
      name: '',
      model_name: '',
      prompt: '',
      persona: '',
      knowledge_base_ids: [],
      tool_ids: [],
    };
  }

  const tool_ids = agent.tools.map((tool) => tool.toolgroup_id);

  return {
    name: agent.name,
    model_name: agent.model_name,
    prompt: agent.prompt,
    persona: '', // Always start with empty persona for new forms
    knowledge_base_ids: agent.knowledge_base_ids,
    tool_ids,
  };
};

const convertFormDataToAgent = (formData: AgentFormData, tools: ToolGroup[]): NewAgent & { persona?: string } => {
  const toolAssociations: ToolAssociationInfo[] = formData.tool_ids.map((toolId) => {
    const tool = tools.find((t) => t.toolgroup_id === toolId);
    if (!tool) {
      throw new Error(`Tool with toolgroup_id ${toolId} not found`);
    }
    return {
      toolgroup_id: tool.toolgroup_id,
    };
  });

  const hasRAGTool = formData.tool_ids.includes('builtin::rag');
  const knowledge_base_ids = hasRAGTool ? formData.knowledge_base_ids : [];

  const result = {
    name: formData.name,
    model_name: formData.model_name,
    prompt: formData.prompt,
    knowledge_base_ids,
    tools: toolAssociations,
    persona: formData.persona || undefined,
  };

  console.log('=== FORM SUBMISSION ===');
  console.log('Selected persona:', formData.persona);
  console.log('Agent payload:', result);
  console.log('======================');

  return result;
};

export function AgentForm({
  defaultAgentProps,
  modelsProps,
  knowledgeBasesProps,
  toolsProps,
  onSubmit,
  isSubmitting,
  onCancel,
}: AgentFormProps) {
  const { models, isLoadingModels, modelsError } = modelsProps;
  const { knowledgeBases, isLoadingKnowledgeBases, knowledgeBasesError } = knowledgeBasesProps;
  const { tools, isLoadingTools, toolsError } = toolsProps;

  const initialAgentData: AgentFormData = convertAgentToFormData(defaultAgentProps);

  const form = useForm({
    defaultValues: initialAgentData,
    onSubmit: ({ value }) => {
      const convertedAgent = convertFormDataToAgent(value, tools);
      onSubmit(convertedAgent);
    },
  });

  const handleCancel = () => {
    onCancel();
    form.reset();
  };

  // NEW: Auto-fill name based on persona selection
  const handlePersonaChange = (persona: string) => {
    form.setFieldValue('persona', persona);
    
    // Auto-suggest name if current name is empty or was a previous suggestion
    const currentName = form.state.values.name;
    const isEmptyOrSuggestion = !currentName || Object.values(PERSONA_NAME_SUGGESTIONS).includes(currentName);
    
    if (persona && isEmptyOrSuggestion) {
      const suggestedName = PERSONA_NAME_SUGGESTIONS[persona];
      if (suggestedName) {
        form.setFieldValue('name', suggestedName);
      }
    }
    
    // Auto-suggest prompt if current prompt is empty or was a previous suggestion
    const currentPrompt = form.state.values.prompt;
    const isEmptyPromptOrSuggestion = !currentPrompt || Object.values(PERSONA_PROMPT_SUGGESTIONS).includes(currentPrompt);
    
    if (persona && isEmptyPromptOrSuggestion) {
      const suggestedPrompt = PERSONA_PROMPT_SUGGESTIONS[persona];
      if (suggestedPrompt) {
        form.setFieldValue('prompt', suggestedPrompt);
      }
    }
  };

  // NEW: Manual suggestion buttons
  const applySuggestedName = () => {
    const currentPersona = form.state.values.persona;
    if (currentPersona && PERSONA_NAME_SUGGESTIONS[currentPersona]) {
      form.setFieldValue('name', PERSONA_NAME_SUGGESTIONS[currentPersona]);
    }
  };

  const applySuggestedPrompt = () => {
    const currentPersona = form.state.values.persona;
    if (currentPersona && PERSONA_PROMPT_SUGGESTIONS[currentPersona]) {
      form.setFieldValue('prompt', PERSONA_PROMPT_SUGGESTIONS[currentPersona]);
    }
  };

  const knowledgeBaseOptions = useMemo((): CustomSelectOptionProps[] => {
    if (isLoadingKnowledgeBases) {
      return [
        {
          value: 'loading_kb',
          children: 'Loading knowledge bases...',
          isDisabled: true,
          id: 'loading_kb_opt',
        },
      ];
    }
    if (knowledgeBasesError) {
      return [
        {
          value: 'error_kb',
          children: 'Error loading knowledge bases',
          isDisabled: true,
          id: 'error_kb_opt',
        },
      ];
    }
    if (!knowledgeBases || knowledgeBases.length === 0) {
      return [
        {
          value: 'no_kb_options',
          children: 'No knowledge bases available',
          isDisabled: true,
          id: 'no_kb_options_opt',
        },
      ];
    }
    return knowledgeBases.map((kb) => ({
      value: kb.kb_name,
      children: kb.kb_name,
      id: `kb-option-${kb.kb_name}`,
    }));
  }, [knowledgeBases, isLoadingKnowledgeBases, knowledgeBasesError]);

  const toolsOptions = useMemo((): CustomSelectOptionProps[] => {
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
    return tools.map((tool) => ({
      value: tool.toolgroup_id,
      children: tool.name,
      id: `tools-option-${tool.toolgroup_id}`,
    }));
  }, [tools, isLoadingTools, toolsError]);

  return (
    <Form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void form.handleSubmit();
      }}
    >
      {/* PERSONA FIELD - MOVED TO TOP */}
      <form.Field name="persona">
        {(field) => (
          <FormGroup label="Banking Role" fieldId="banking-persona">
            <FormSelect
              id="banking-persona"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => {
                console.log('Banking role selected:', value);
                handlePersonaChange(value); // NEW: Auto-fill name and prompt
              }}
              aria-label="Select Banking Role"
            >
              {BANKING_PERSONAS.map((persona) => (
                <FormSelectOption
                  key={persona.value}
                  value={persona.value}
                  label={persona.label}
                  isDisabled={persona.disabled}
                />
              ))}
            </FormSelect>
            {field.state.value && (
              <FormHelperText>
                <Label color="purple" variant="outline" className="pf-v6-u-mt-xs">
                  {BANKING_PERSONAS.find(p => p.value === field.state.value)?.label}
                </Label>
              </FormHelperText>
            )}
          </FormGroup>
        )}
      </form.Field>

      <form.Field
        name="name"
        validators={{
          onChange: ({ value }) => (!value ? 'Name is required' : undefined),
        }}
      >
        {(field) => (
          <FormGroup label="Agent Name" isRequired fieldId="agent-name">
            <Flex gap={{ default: 'gapSm' }} alignItems={{ default: 'alignItemsEnd' }}>
              <FlexItem flex={{ default: 'flex_1' }}>
                <TextInput
                  isRequired
                  type="text"
                  id="agent-name"
                  name={field.name}
                  value={field.state.value}
                  onBlur={field.handleBlur}
                  onChange={(_event, value) => {
                    field.handleChange(value);
                  }}
                  validated={
                    !field.state.meta.isTouched
                      ? 'default'
                      : !field.state.meta.isValid
                        ? 'error'
                        : 'success'
                  }
                />
              </FlexItem>
              {/* NEW: Auto-suggest name button */}
              {form.state.values.persona && PERSONA_NAME_SUGGESTIONS[form.state.values.persona] && (
                <FlexItem>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={applySuggestedName}
                    icon={<MagicIcon />}
                  >
                    Suggest
                  </Button>
                </FlexItem>
              )}
            </Flex>
            {!field.state.meta.isValid && (
              <FormHelperText className="pf-v6-u-text-color-status-danger">
                {field.state.meta.errors.join(', ')}
              </FormHelperText>
            )}
            {/* NEW: Show suggestion preview */}
            {form.state.values.persona && PERSONA_NAME_SUGGESTIONS[form.state.values.persona] && 
             field.state.value !== PERSONA_NAME_SUGGESTIONS[form.state.values.persona] && (
              <FormHelperText>
                💡 Suggestion: <em>{PERSONA_NAME_SUGGESTIONS[form.state.values.persona]}</em>
              </FormHelperText>
            )}
          </FormGroup>
        )}
      </form.Field>

      <form.Field
        name="model_name"
        validators={{
          onChange: ({ value }) => (!value ? 'Model is required' : undefined),
        }}
      >
        {(field) => (
          <FormGroup label="Select AI Model" isRequired fieldId="ai-model">
            <FormSelect
              id="ai-model"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
              aria-label="Select AI Model"
              isDisabled={isLoadingModels || !!modelsError}
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : !field.state.meta.isValid
                    ? 'error'
                    : 'success'
              }
            >
              {isLoadingModels ? (
                <FormSelectOption key="loading" value="" label="Loading models..." isDisabled />
              ) : modelsError ? (
                <FormSelectOption key="error" value="" label="Error loading models" isDisabled />
              ) : (
                <Fragment>
                  <FormSelectOption key="placeholder" value="" label="Select a model" isDisabled />
                  {models.map((model) => (
                    <FormSelectOption
                      key={model.model_name}
                      value={model.model_name}
                      label={model.model_name}
                    />
                  ))}
                </Fragment>
              )}
            </FormSelect>
            {!field.state.meta.isValid && (
              <FormHelperText className="pf-v6-u-text-color-status-danger">
                {field.state.meta.errors.join(', ')}
              </FormHelperText>
            )}
          </FormGroup>
        )}
      </form.Field>
      
      <form.Field
        name="prompt"
        validators={{
          onChange: ({ value }) => (!value ? 'Prompt is required' : undefined),
        }}
      >
        {(field) => (
          <FormGroup label="Agent Prompt" isRequired fieldId="prompt">
            <Flex direction={{ default: 'column' }} gap={{ default: 'gapSm' }}>
              <FlexItem>
                <Flex gap={{ default: 'gapSm' }} alignItems={{ default: 'alignItemsEnd' }}>
                  <FlexItem flex={{ default: 'flex_1' }}>
                    <TextArea
                      isRequired
                      id="prompt"
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(_event, value) => field.handleChange(value)}
                      validated={
                        !field.state.meta.isTouched
                          ? 'default'
                          : !field.state.meta.isValid
                            ? 'error'
                            : 'success'
                      }
                      rows={4}
                    />
                  </FlexItem>
                  {/* NEW: Auto-suggest prompt button */}
                  {form.state.values.persona && PERSONA_PROMPT_SUGGESTIONS[form.state.values.persona] && (
                    <FlexItem>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={applySuggestedPrompt}
                        icon={<MagicIcon />}
                      >
                        Suggest
                      </Button>
                    </FlexItem>
                  )}
                </Flex>
              </FlexItem>
            </Flex>
            {!field.state.meta.isValid && (
              <FormHelperText className="pf-v6-u-text-color-status-danger">
                {field.state.meta.errors.join(', ')}
              </FormHelperText>
            )}
          </FormGroup>
        )}
      </form.Field>
      
      <form.Field name="tool_ids">
        {(field) => (
          <FormGroup label="Select Tool Groups" fieldId="tools-multiselect">
            <MultiSelect
              id="tools-multiselect-component"
              value={field.state.value || []}
              options={toolsOptions}
              onBlur={field.handleBlur}
              onChange={(selectedIds) => field.handleChange(selectedIds)}
              ariaLabel="Select Tool Groups"
              isDisabled={
                isLoadingTools ||
                toolsError != null ||
                (tools && tools.length === 0 && !isLoadingTools && !toolsError)
              }
              placeholder="Type or select tool groups..."
            />
          </FormGroup>
        )}
      </form.Field>
      
      <form.Subscribe selector={(state) => state.values.tool_ids}>
        {(toolIds) => {
          const hasRAGTool = toolIds?.includes('builtin::rag');

          if (!hasRAGTool && form.state.values.knowledge_base_ids?.length > 0) {
            form.setFieldValue('knowledge_base_ids', []);
          }

          return hasRAGTool ? (
            <form.Field name="knowledge_base_ids">
              {(field) => (
                <FormGroup
                  label="Select Knowledge Bases"
                  fieldId="knowledge-bases-multiselect"
                >
                  <MultiSelect
                    id="knowledge-bases-multiselect-component"
                    value={field.state.value}
                    options={knowledgeBaseOptions}
                    onBlur={field.handleBlur}
                    onChange={(selectedIds) => field.handleChange(selectedIds)}
                    ariaLabel="Select Knowledge Bases"
                    isDisabled={
                      isLoadingKnowledgeBases ||
                      knowledgeBasesError != null ||
                      (knowledgeBases &&
                        knowledgeBases.length === 0 &&
                        !isLoadingKnowledgeBases &&
                        !knowledgeBasesError)
                    }
                    placeholder="Type or select knowledge bases..."
                  />
                </FormGroup>
              )}
            </form.Field>
          ) : null;
        }}
      </form.Subscribe>
      
      <ActionGroup>
        <form.Subscribe
          selector={(state) => [state.canSubmit, state.isSubmitting, state.isPristine]}
        >
          {([canSubmit, isSubmitting]) => (
            <Button
              icon={<PaperPlaneIcon />}
              variant="primary"
              type="submit"
              isLoading={isSubmitting}
              isDisabled={isSubmitting || !canSubmit}
            >
              Submit
            </Button>
          )}
        </form.Subscribe>
        <Button variant="link" onClick={handleCancel} isDisabled={isSubmitting}>
          Cancel
        </Button>
      </ActionGroup>
    </Form>
  );
}