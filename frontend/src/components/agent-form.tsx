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
} from '@patternfly/react-core';
import { useForm } from '@tanstack/react-form';
import { Fragment, useMemo } from 'react';
import { CustomSelectOptionProps, MultiSelect } from './multi-select';
import { PaperPlaneIcon } from '@patternfly/react-icons';

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
}

// Helper functions to convert between formats
const convertAgentToFormData = (agent: Agent | undefined): AgentFormData => {
  if (!agent) {
    return {
      name: '',
      model_name: '',
      prompt: '',
      knowledge_base_ids: [],
      tool_ids: [],
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
  };
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
      console.log('Test');
      const convertedAgent = convertFormDataToAgent(value, tools);
      onSubmit(convertedAgent);
    },
  });

  const handleCancel = () => {
    onCancel();
    form.reset();
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
      value: kb.kb_name, // Use vector_db_name as the primary key
      children: kb.kb_name, // The name will be displayed
      id: `kb-option-${kb.kb_name}`, // Unique ID for React key and ARIA
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
