import { KnowledgeBase, NewKnowledgeBase } from '@/routes/config/knowledge-bases';
// import { KnowledgeBase, Model, Tool } from '@/types';
import {
  ActionGroup,
  Alert,
  Button,
  Form,
  FormGroup,
  FormSelect,
  FormSelectOption,
  TextArea,
  TextInput,
} from '@patternfly/react-core';
import { useForm } from '@tanstack/react-form';
import { Fragment, useMemo } from 'react';
import { CustomSelectOptionProps, MultiSelect } from './multi-select';

interface KnowledgeBaseFormProps {
  defaultKnowledgeBaseProps?: KnowledgeBase | undefined;
  onSubmit: (values: NewKnowledgeBase | KnowledgeBase) => void;
  isSubmitting: boolean;
  onCancel: () => void;
}

export function KnowledgeBaseForm({
  defaultKnowledgeBaseProps,
  onSubmit,
  isSubmitting,
  onCancel,
}: KnowledgeBaseFormProps) {
  const initialKnowledgeBaseData: NewKnowledgeBase = defaultKnowledgeBaseProps ?? {
    id: '',
    name: '',
    provider_id: '',
    type: '',
    embedding_model: '',
    version: '',
    vector_db_name: '',
    is_external: false,
    source: '',
    source_configuration: {},
  };

  const form = useForm({
    defaultValues: initialKnowledgeBaseData,
    onSubmit: async ({ value }) => {
      onSubmit(value);
    },
  });

  const handleCancel = () => {
    onCancel();
    form.reset();
  };

  return (
    <Form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        form.handleSubmit();
      }}
    >
      <form.Field
        name="name"
        children={(field) => (
          <FormGroup label="Name" isRequired fieldId="name">
            <TextInput
              isRequired
              type="text"
              id="name"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
            />
          </FormGroup>
        )}
      />
      <form.Field
        name="version"
        children={(field) => (
          <FormGroup label="Version" isRequired fieldId="version">
            <TextInput
              isRequired
              type="text"
              id="version"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
            />
          </FormGroup>
        )}
      />

      <ActionGroup>
        <Button
          variant="primary"
          type="submit"
          isLoading={isSubmitting}
          isDisabled={isSubmitting || !form.state.canSubmit}
        >
          Create Knowledge Base
        </Button>
        <Button variant="link" onClick={handleCancel} isDisabled={isSubmitting}>
          Cancel
        </Button>
      </ActionGroup>
      {form.state.submissionAttempts > 0 &&
        !form.state.isSubmitted &&
        form.state.errors.length > 0 && (
          <Alert variant="danger" title="Form submission failed" className="pf-v5-u-mt-md">
            Please check the form for errors.
          </Alert>
        )}
    </Form>
  );
}
