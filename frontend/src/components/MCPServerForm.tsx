import { useForm } from '@tanstack/react-form';
import { useEffect } from 'react';
import { MCPServer, MCPServerCreate } from '@/types';
import {
  Button,
  ActionGroup,
  Form,
  FormGroup,
  TextInput,
  TextArea,
  Alert,
} from '@patternfly/react-core';
import { PaperPlaneIcon } from '@patternfly/react-icons';

interface MCPServerFormProps {
  defaultServer?: MCPServer;
  isSubmitting: boolean;
  onSubmit: (values: MCPServerCreate) => void;
  onCancel: () => void;
  error?: Error | null;
  isEditing?: boolean; // True when editing existing server, false when creating new
}

export function MCPServerForm({
  defaultServer,
  isSubmitting,
  onSubmit,
  onCancel,
  error,
  isEditing = false,
}: MCPServerFormProps) {
  const initialData: MCPServerCreate = defaultServer
    ? {
        toolgroup_id: defaultServer.toolgroup_id,
        name: defaultServer.name,
        description: defaultServer.description || '',
        endpoint_url: defaultServer.endpoint_url,
        configuration: defaultServer.configuration || {},
      }
    : {
        toolgroup_id: '', // Now required - user must provide
        name: '',
        description: '',
        endpoint_url: '',
        configuration: {},
      };

  const form = useForm({
    defaultValues: initialData,
    onSubmit: ({ value }) => {
      // Convert configuration from string to object if needed
      const finalValue = { ...value };

      // If configuration is a string, try to parse it as JSON
      if (typeof value.configuration === 'string') {
        try {
          finalValue.configuration = value.configuration
            ? (JSON.parse(value.configuration) as Record<string, unknown>)
            : {};
        } catch (_e) {
          // If parsing fails, keep it as empty object
          finalValue.configuration = {};
        }
      }

      onSubmit(finalValue);
    },
  });

  // Reset form when defaultServer changes (e.g., when selecting a different discovered server)
  useEffect(() => {
    if (defaultServer) {
      const newData: MCPServerCreate = {
        toolgroup_id: defaultServer.toolgroup_id,
        name: defaultServer.name,
        description: defaultServer.description || '',
        endpoint_url: defaultServer.endpoint_url,
        configuration: defaultServer.configuration || {},
      };

      form.reset();
      // Set values without triggering validation
      (
        Object.entries(newData) as [keyof MCPServerCreate, string | Record<string, unknown>][]
      ).forEach(([key, value]) => {
        form.setFieldValue(key, value);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [defaultServer]);

  return (
    <Form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void form.handleSubmit();
      }}
    >
      {error && <Alert variant="danger" title={error.message} />}

      {/* Name field - FIRST */}
      <form.Field
        name="name"
        validators={{
          onChange: ({ value }) => (!value ? 'Name is required' : undefined),
        }}
      >
        {(field) => (
          <FormGroup label="Name" isRequired fieldId="mcp-form-name">
            <TextInput
              isRequired
              id="mcp-form-name"
              value={field.state.value}
              onChange={(_e, v) => {
                field.handleChange(v);
                // Auto-fill toolgroup_id as "mcp::" + name (only if not editing)
                if (!isEditing) {
                  form.setFieldValue('toolgroup_id', `mcp::${v}`);
                }
              }}
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
              placeholder="Enter MCP server name"
              isDisabled={isEditing} // Disable when editing to keep name and toolgroup_id consistent
            />
            {field.state.meta.errors.length > 0 && (
              <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                {field.state.meta.errors[0]}
              </div>
            )}
          </FormGroup>
        )}
      </form.Field>

      {/* Description field - SECOND */}
      <form.Field
        name="description"
        validators={{
          onChange: ({ value }) => (!value ? 'Description is required' : undefined),
        }}
      >
        {(field) => (
          <FormGroup label="Description" isRequired fieldId="mcp-form-description">
            <TextInput
              isRequired
              id="mcp-form-description"
              value={field.state.value || ''}
              onChange={(_e, v) => field.handleChange(v)}
              placeholder="Enter description"
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
            />
            {field.state.meta.errors.length > 0 && (
              <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                {field.state.meta.errors[0]}
              </div>
            )}
          </FormGroup>
        )}
      </form.Field>

      {/* Toolgroup ID field - THIRD (auto-filled from name) */}
      <form.Field
        name="toolgroup_id"
        validators={{
          onChange: ({ value }) => (!value ? 'Toolgroup ID is required' : undefined),
        }}
      >
        {(field) => (
          <FormGroup label="Toolgroup ID" isRequired fieldId="mcp-form-toolgroup-id">
            <TextInput
              isRequired
              id="mcp-form-toolgroup-id"
              value={field.state.value}
              onChange={(_e, v) => field.handleChange(v)}
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
              placeholder="mcp::my_server"
              isDisabled={!!defaultServer} // Disable editing for existing servers
            />
            {field.state.meta.errors.length > 0 && (
              <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                {field.state.meta.errors[0]}
              </div>
            )}
          </FormGroup>
        )}
      </form.Field>

      <form.Field
        name="endpoint_url"
        validators={{
          onChange: ({ value }) => {
            if (!value) return 'Endpoint URL is required';
            try {
              new URL(value);
              return undefined;
            } catch {
              return 'Please enter a valid URL';
            }
          },
        }}
      >
        {(field) => (
          <FormGroup label="Endpoint URL" isRequired fieldId="mcp-form-endpoint">
            <TextInput
              isRequired
              id="mcp-form-endpoint"
              value={field.state.value}
              onChange={(_e, v) => field.handleChange(v)}
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
              placeholder="https://example.com/mcp"
            />
            {field.state.meta.errors.length > 0 && (
              <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                {field.state.meta.errors[0]}
              </div>
            )}
          </FormGroup>
        )}
      </form.Field>

      <form.Field
        name="configuration"
        validators={{
          onChange: ({ value }) => {
            if (!value || typeof value !== 'string') return undefined;
            if (value === '') return undefined;
            try {
              JSON.parse(value);
              return undefined;
            } catch {
              return 'Invalid JSON format';
            }
          },
        }}
      >
        {(field) => (
          <FormGroup label="Configuration (JSON)" fieldId="mcp-form-config">
            <TextArea
              id="mcp-form-config"
              value={
                typeof field.state.value === 'string'
                  ? field.state.value
                  : JSON.stringify(field.state.value || {}, null, 2)
              }
              onChange={(_e, v) => field.handleChange(v as unknown as Record<string, unknown>)}
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
              rows={4}
              placeholder='{"key": "value"}'
            />
            {field.state.meta.errors.length > 0 && (
              <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                {field.state.meta.errors[0]}
              </div>
            )}
          </FormGroup>
        )}
      </form.Field>

      <ActionGroup>
        <form.Subscribe
          selector={(state) => [
            state.isSubmitting,
            state.values.toolgroup_id,
            state.values.name,
            state.values.description,
            state.values.endpoint_url,
            state.errors,
          ]}
        >
          {([isSubmittingForm, toolgroup_id, name, description, endpoint_url, errors]) => {
            // Check if all required fields are filled
            const hasRequiredFields =
              Boolean(toolgroup_id) &&
              Boolean(name) &&
              Boolean(description) &&
              Boolean(endpoint_url);

            // Check if there are any validation errors
            const hasErrors = Array.isArray(errors) && errors.length > 0;

            const shouldDisable = Boolean(isSubmittingForm) || !hasRequiredFields || hasErrors;

            return (
              <Button
                icon={<PaperPlaneIcon />}
                type="submit"
                variant="primary"
                isDisabled={Boolean(shouldDisable)}
                isLoading={Boolean(isSubmitting || isSubmittingForm)}
              >
                {isEditing ? 'Update' : 'Create'}
              </Button>
            );
          }}
        </form.Subscribe>
        <Button variant="link" onClick={onCancel} isDisabled={isSubmitting}>
          Cancel
        </Button>
      </ActionGroup>
    </Form>
  );
}
