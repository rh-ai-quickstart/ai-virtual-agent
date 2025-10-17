import { Agent, NewAgent } from '@/types/agent';
import { ToolGroup, ToolAssociationInfo, SamplingStrategy, KnowledgeBaseWithStatus } from '@/types';
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
  Accordion,
  AccordionItem,
  AccordionToggle,
  AccordionContent,
  Tooltip,
} from '@patternfly/react-core';
import { useForm } from '@tanstack/react-form';
import { Fragment, useMemo, useState } from 'react';
import { CustomSelectOptionProps, MultiSelect } from './multi-select';
import { PaperPlaneIcon } from '@patternfly/react-icons';
import React from 'react';
import FormFieldSlider from './FormFieldSlider';
import { parameterFields } from '../config/samplingParametersConfig';
import { useModels, useKnowledgeBases, useTools, useShields } from '@/hooks';

interface AgentFormProps {
  defaultAgentProps?: Agent | undefined;
  onSubmit: (values: NewAgent) => void;
  isSubmitting: boolean;
  onCancel: () => void;
}

// Form interface for internal form state (user-friendly)
interface AgentFormData {
  name: string;
  model_name: string;
  prompt: string;
  knowledge_base_ids: string[];
  tool_ids: string[]; // Internal form uses tool IDs for easier UI handling
  sampling_strategy: SamplingStrategy;
  temperature: number;
  top_p: number;
  top_k: number;
  max_tokens: number;
  repetition_penalty: number;
  samplingAccordionExpanded: boolean; // Added for accordion state
  input_shields: string; // Single selection for form UI
  output_shields: string; // Single selection for form UI
}

// Helper functions to convert between formats
const convertAgentToFormData = (agent: Agent | undefined): AgentFormData => {
  if (!agent) {
    return {
      name: '',
      model_name: '',
      prompt: 'You are a helpful assistant. Provide clear, concise responses without repetition.',
      knowledge_base_ids: [],
      tool_ids: [],
      sampling_strategy: 'greedy',
      temperature: 0.0,
      top_p: 0.95,
      top_k: 40,
      max_tokens: 512,
      repetition_penalty: 1.0, // XXX: this is specific to vllm, and doesn't work with openai's API in llamastack
      samplingAccordionExpanded: false, // Initialize accordion state
      input_shields: '',
      output_shields: '',
    };
  }

  // Convert ToolAssociationInfo array to tool_ids array for form
  const tool_ids = agent.tools.map((tool) => tool.toolgroup_id);

  return {
    name: agent.name,
    model_name: agent.model_name,
    prompt: agent.prompt,
    knowledge_base_ids: agent.knowledge_base_ids,
    tool_ids,
    sampling_strategy: agent.sampling_strategy ?? 'greedy',
    temperature: agent.temperature ?? 0.0,
    top_p: agent.top_p ?? 0.95,
    top_k: agent.top_k ?? 40,
    max_tokens: agent.max_tokens ?? 512,
    repetition_penalty: agent.repetition_penalty ?? 1.0,
    samplingAccordionExpanded: false, // Initialize accordion state
    input_shields: agent.input_shields?.[0] || '', // Take first shield or empty string
    output_shields: agent.output_shields?.[0] || '', // Take first shield or empty string
  };
};

const convertFormDataToAgent = (formData: AgentFormData, tools: ToolGroup[]): NewAgent => {
  // Convert tool_ids back to ToolAssociationInfo array
  const toolAssociations: ToolAssociationInfo[] = formData.tool_ids.map((toolId) => {
    const tool = tools.find((t) => t.toolgroup_id === toolId);
    if (!tool) {
      throw new Error(`Tool with toolgroup_id ${toolId} not found`);
    }
    return {
      toolgroup_id: tool.toolgroup_id,
    };
  });

  // Only include knowledge bases if RAG tool is selected
  const hasRAGTool = formData.tool_ids.includes('builtin::rag');
  const knowledge_base_ids = hasRAGTool ? formData.knowledge_base_ids : [];

  return {
    name: formData.name,
    model_name: formData.model_name,
    prompt: formData.prompt,
    knowledge_base_ids,
    tools: toolAssociations,
    sampling_strategy: formData.sampling_strategy,
    temperature: formData.temperature,
    top_p: formData.top_p,
    top_k: formData.top_k,
    max_tokens: formData.max_tokens,
    repetition_penalty: formData.repetition_penalty,
    input_shields: formData.input_shields ? [formData.input_shields] : [], // Convert to array
    output_shields: formData.output_shields ? [formData.output_shields] : [], // Convert to array
  };
};

export function AgentForm({ defaultAgentProps, onSubmit, isSubmitting, onCancel }: AgentFormProps) {
  // Use custom hooks to get data
  const { models, isLoadingModels, modelsError } = useModels();
  const {
    knowledgeBases,
    isLoading: isLoadingKnowledgeBases,
    error: knowledgeBasesError,
  } = useKnowledgeBases();
  const { tools, isLoading: isLoadingTools, error: toolsError } = useTools();
  const { shields, isLoading: isLoadingShields, error: shieldsError } = useShields();

  const initialAgentData: AgentFormData = convertAgentToFormData(defaultAgentProps);

  const form = useForm({
    defaultValues: initialAgentData,
    onSubmit: ({ value }) => {
      console.log('Test');
      const convertedAgent = convertFormDataToAgent(value, tools || []);
      onSubmit(convertedAgent);
    },
  });

  const handleCancel = () => {
    onCancel();
    form.reset();
  };

  const handleSliderChange = (
    event: unknown,
    field: { handleChange: (value: number) => void },
    sliderValue: number,
    inputValue: number | undefined,
    { min, max, step }: { min: number; max: number; step: number },
    setLocalInputValue?: React.Dispatch<React.SetStateAction<number>>
  ) => {
    // Use inputValue if present, otherwise sliderValue
    const rawValue = inputValue !== undefined ? Number(inputValue) : sliderValue;
    // Ensures the value stays within the defined range
    const clampedValue = Math.max(min, Math.min(rawValue, max));
    const roundedValue = min + Math.round((clampedValue - min) / step) * step;
    const decimalPlaces = step.toString().split('.')[1]?.length || 0;
    const finalValue = parseFloat(roundedValue.toFixed(decimalPlaces));

    // Update the local input value (for the input box)
    setLocalInputValue?.(finalValue);

    // Only update the field if the event is not a 'change' event (to avoid double updates)
    if (event && typeof event === 'object' && 'type' in event && event.type !== 'change') {
      field.handleChange(finalValue);
    } else if (!event || typeof event !== 'object' || !('type' in event)) {
      field.handleChange(finalValue);
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
    return knowledgeBases.map((kb: KnowledgeBaseWithStatus) => ({
      value: kb.vector_store_name, // Use vector_store_name as the primary key
      children: kb.name, // The name will be displayed
      id: `kb-option-${kb.vector_store_name}`, // Unique ID for React key and ARIA
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
      value: tool.toolgroup_id, // Use toolgroup_id as the primary key
      children: tool.name, // The name will be displayed
      id: `tools-option-${tool.toolgroup_id}`, // Unique ID for React key and ARIA
    }));
  }, [tools, isLoadingTools, toolsError]);

  const [isSamplingAccordionExpanded, setSamplingAccordionExpanded] = useState(false);
  const shieldsOptions = useMemo(() => {
    if (isLoadingShields) {
      return [{ value: '', label: 'Loading shields...', disabled: true }];
    }
    if (shieldsError) {
      return [{ value: '', label: 'Error loading shields', disabled: true }];
    }
    if (!shields || shields.length === 0) {
      return [{ value: '', label: 'No shields available', disabled: true }];
    }
    return [{ value: '', label: 'No shield selected', disabled: false }].concat(
      shields.map((shield) => ({
        value: shield.identifier,
        label: shield.name || shield.identifier,
        disabled: false,
      }))
    );
  }, [shields, isLoadingShields, shieldsError]);

  return (
    <Form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void form.handleSubmit();
      }}
    >
      <form.Field
        name="name"
        validators={{
          onChange: ({ value }) => (!value ? 'Name is required' : undefined),
        }}
      >
        {(field) => (
          <FormGroup label="Agent Name" isRequired fieldId="agent-name">
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
            {!field.state.meta.isValid && (
              <FormHelperText className="pf-v6-u-text-color-status-danger">
                {field.state.meta.errors.join(', ')}
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
                  {(models || []).map((model) => (
                    <FormSelectOption
                      key={model.model_id}
                      value={model.model_id}
                      label={model.model_id}
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
            <TextArea
              isRequired
              type="text"
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
            />
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
          <FormGroup
            label="Select Tool Groups"
            fieldId="tools-multiselect" // Unique ID for the FormGroup
          >
            <MultiSelect
              id="tools-multiselect-component" // Unique ID for the MultiSelect component itself
              value={field.state.value || []} // Ensure it's always an array
              options={toolsOptions} // Pass the prepared options
              onBlur={field.handleBlur}
              onChange={(selectedIds) => field.handleChange(selectedIds)} // Pass the new array directly
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
      <form.Field name="input_shields">
        {(field) => (
          <FormGroup label="Input Shield" fieldId="input-shield">
            <FormSelect
              id="input-shield"
              name={field.name}
              value={field.state.value || ''}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
              aria-label="Select Input Shield"
              isDisabled={isLoadingShields || !!shieldsError}
            >
              {shieldsOptions.map((option) => (
                <FormSelectOption
                  key={option.value}
                  value={option.value}
                  label={option.label}
                  isDisabled={option.disabled}
                />
              ))}
            </FormSelect>
          </FormGroup>
        )}
      </form.Field>
      <form.Field name="output_shields">
        {(field) => (
          <FormGroup label="Output Shield" fieldId="output-shield">
            <FormSelect
              id="output-shield"
              name={field.name}
              value={field.state.value || ''}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
              aria-label="Select Output Shield"
              isDisabled={isLoadingShields || !!shieldsError}
            >
              {shieldsOptions.map((option) => (
                <FormSelectOption
                  key={option.value}
                  value={option.value}
                  label={option.label}
                  isDisabled={option.disabled}
                />
              ))}
            </FormSelect>
          </FormGroup>
        )}
      </form.Field>
      <form.Subscribe selector={(state) => state.values.tool_ids}>
        {(toolIds) => {
          const hasRAGTool = toolIds?.includes('builtin::rag');

          // Clear knowledge bases if RAG tool is removed
          if (!hasRAGTool && form.state.values.knowledge_base_ids?.length > 0) {
            form.setFieldValue('knowledge_base_ids', []);
          }

          return hasRAGTool ? (
            <form.Field name="knowledge_base_ids">
              {(field) => (
                <FormGroup
                  label="Select Knowledge Bases"
                  fieldId="knowledge-bases-multiselect" // Unique ID for the FormGroup
                >
                  <MultiSelect
                    id="knowledge-bases-multiselect-component" // Unique ID for the MultiSelect component itself
                    value={field.state.value} // Pass the array of IDs
                    options={knowledgeBaseOptions} // Pass the prepared options
                    onBlur={field.handleBlur}
                    onChange={(selectedIds) => field.handleChange(selectedIds)} // Pass the new array directly
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
      {/* Sampling & Generation Parameters Accordion */}
      <Accordion asDefinitionList={false}>
        <AccordionItem isExpanded={isSamplingAccordionExpanded}>
          <Tooltip content="Advanced: Control how the model generates text.">
            <AccordionToggle
              id="sampling-params-toggle"
              onClick={() => setSamplingAccordionExpanded(!isSamplingAccordionExpanded)}
            >
              Sampling & Generation Parameters
            </AccordionToggle>
          </Tooltip>
          <AccordionContent id="sampling-params-content" hidden={!isSamplingAccordionExpanded}>
            {/* Sampling Strategy Dropdown */}
            <form.Field name="sampling_strategy">
              {(field) => (
                <FormGroup
                  label="Sampling Strategy"
                  fieldId="sampling-strategy"
                  className="wide-input-slider"
                  style={{ marginBottom: 24, marginLeft: 15 }}
                >
                  <FormHelperText>
                    The method for selecting the next token in a sequence.
                  </FormHelperText>
                  <div style={{ maxWidth: 200 }}>
                    <FormSelect
                      id="sampling-strategy"
                      name={field.name}
                      value={field.state.value}
                      onBlur={field.handleBlur}
                      onChange={(_event, value) => field.handleChange(value as SamplingStrategy)}
                    >
                      <FormSelectOption value="greedy" label="Greedy" />
                      <FormSelectOption value="top-p" label="Top-P" />
                      <FormSelectOption value="top-k" label="Top-K" />
                    </FormSelect>
                  </div>
                </FormGroup>
              )}
            </form.Field>
            {/* Render all parameter fields using config */}
            <form.Subscribe selector={(state) => state.values.sampling_strategy}>
              {(strategy) => (
                <>
                  {parameterFields.map((fieldConfig) => {
                    const shouldShow = !fieldConfig.showWhen || fieldConfig.showWhen(strategy);
                    return shouldShow ? (
                      <FormFieldSlider
                        key={fieldConfig.name}
                        form={form}
                        name={fieldConfig.name}
                        label={fieldConfig.label}
                        helperText={fieldConfig.helperText}
                        min={fieldConfig.min}
                        max={fieldConfig.max}
                        step={fieldConfig.step}
                        handleSliderChange={handleSliderChange}
                      />
                    ) : null;
                  })}
                </>
              )}
            </form.Subscribe>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
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
