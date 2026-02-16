import { useForm } from '@tanstack/react-form';
import { ProviderCreate } from '@/types/models';
import {
  Button,
  ActionGroup,
  Form,
  FormGroup,
  TextInput,
  Alert,
  FormSelect,
  FormSelectOption,
} from '@patternfly/react-core';
import { PaperPlaneIcon } from '@patternfly/react-icons';

interface ProviderFormProps {
  isSubmitting: boolean;
  onSubmit: (values: ProviderCreate) => void;
  onCancel: () => void;
  error?: Error | null;
}

export function ProviderForm({ isSubmitting, onSubmit, onCancel, error }: ProviderFormProps) {
  const initialData: ProviderCreate = {
    provider_id: '',
    provider_type: 'remote::vllm',
    config: {
      base_url: '',
      api_token: 'fake',
      max_tokens: 4096,
      tls_verify: false,
    },
  };

  const form = useForm({
    defaultValues: initialData,
    onSubmit: ({ value }) => {
      // Build config based on provider type
      let config = {};
      if (value.provider_type === 'remote::vllm') {
        config = {
          base_url: (value.config as { base_url?: string }).base_url,
          api_token: (value.config as { api_token?: string }).api_token || 'fake',
          max_tokens: (value.config as { max_tokens?: number }).max_tokens || 4096,
          tls_verify: (value.config as { tls_verify?: boolean }).tls_verify ?? false,
        };
      } else if (value.provider_type === 'remote::ollama') {
        config = {
          base_url: (value.config as { base_url?: string }).base_url,
        };
      }

      onSubmit({
        ...value,
        config,
      });
    },
  });

  return (
    <Form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void form.handleSubmit();
      }}
    >
      {error && <Alert variant="danger" title={error.message} />}

      {/* Provider ID field */}
      <form.Field
        name="provider_id"
        validators={{
          onChange: ({ value }) => (!value ? 'Provider ID is required' : undefined),
        }}
      >
        {(field) => (
          <FormGroup label="Provider ID" isRequired fieldId="provider-form-id">
            <TextInput
              isRequired
              id="provider-form-id"
              value={field.state.value}
              onChange={(_e, v) => field.handleChange(v)}
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
              placeholder="my-vllm-provider"
            />
            {field.state.meta.errors.length > 0 && (
              <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                {field.state.meta.errors[0]}
              </div>
            )}
          </FormGroup>
        )}
      </form.Field>

      {/* Provider Type field */}
      <form.Field
        name="provider_type"
        validators={{
          onChange: ({ value }) => (!value ? 'Provider type is required' : undefined),
        }}
      >
        {(field) => (
          <FormGroup label="Provider Type" isRequired fieldId="provider-form-type">
            <FormSelect
              id="provider-form-type"
              value={field.state.value}
              onChange={(_e, v) => {
                field.handleChange(v as 'remote::vllm' | 'remote::ollama');
                // Reset config when type changes
                if (v === 'remote::ollama') {
                  form.setFieldValue('config', { base_url: '' });
                } else {
                  form.setFieldValue('config', {
                    base_url: '',
                    api_token: 'fake',
                    max_tokens: 4096,
                    tls_verify: false,
                  });
                }
              }}
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
            >
              <FormSelectOption value="remote::vllm" label="vLLM (Remote)" />
              <FormSelectOption value="remote::ollama" label="Ollama (Remote)" />
            </FormSelect>
            {field.state.meta.errors.length > 0 && (
              <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                {field.state.meta.errors[0]}
              </div>
            )}
          </FormGroup>
        )}
      </form.Field>

      {/* URL field */}
      <form.Field name="config">
        {(field) => (
          <FormGroup label="Server URL" isRequired fieldId="provider-form-url">
            <TextInput
              isRequired
              id="provider-form-url"
              value={(field.state.value as { base_url?: string }).base_url || ''}
              onChange={(_e, v) =>
                field.handleChange({
                  ...field.state.value,
                  base_url: v,
                })
              }
              placeholder={
                form.state.values.provider_type === 'remote::ollama'
                  ? 'http://ollama:11434'
                  : 'http://my-vllm.namespace.svc.cluster.local/v1'
              }
            />
          </FormGroup>
        )}
      </form.Field>

      {/* vLLM-specific fields */}
      <form.Subscribe selector={(state) => state.values.provider_type}>
        {(providerType) =>
          providerType === 'remote::vllm' && (
            <>
              <form.Field name="config">
                {(field) => (
                  <FormGroup label="API Token" fieldId="provider-form-token">
                    <TextInput
                      id="provider-form-token"
                      value={(field.state.value as { api_token?: string }).api_token || 'fake'}
                      onChange={(_e, v) =>
                        field.handleChange({
                          ...field.state.value,
                          api_token: v,
                        })
                      }
                      placeholder="fake"
                    />
                  </FormGroup>
                )}
              </form.Field>

              <form.Field name="config">
                {(field) => (
                  <FormGroup label="Max Tokens" fieldId="provider-form-max-tokens">
                    <TextInput
                      id="provider-form-max-tokens"
                      type="number"
                      value={String(
                        (field.state.value as { max_tokens?: number }).max_tokens || 4096
                      )}
                      onChange={(_e, v) =>
                        field.handleChange({
                          ...field.state.value,
                          max_tokens: parseInt(v) || 4096,
                        })
                      }
                      placeholder="4096"
                    />
                  </FormGroup>
                )}
              </form.Field>

              <form.Field name="config">
                {(field) => (
                  <FormGroup label="TLS Verify" fieldId="provider-form-tls">
                    <FormSelect
                      id="provider-form-tls"
                      value={String(
                        (field.state.value as { tls_verify?: boolean }).tls_verify ?? false
                      )}
                      onChange={(_e, v) =>
                        field.handleChange({
                          ...field.state.value,
                          tls_verify: v === 'true',
                        })
                      }
                    >
                      <FormSelectOption value="false" label="Disabled" />
                      <FormSelectOption value="true" label="Enabled" />
                    </FormSelect>
                  </FormGroup>
                )}
              </form.Field>
            </>
          )
        }
      </form.Subscribe>

      <ActionGroup>
        <form.Subscribe selector={(state) => [state.isSubmitting, state.values.provider_id]}>
          {([isSubmittingForm, provider_id]) => {
            const hasRequiredFields = Boolean(provider_id);

            return (
              <Button
                icon={<PaperPlaneIcon />}
                type="submit"
                variant="primary"
                isDisabled={!hasRequiredFields}
                isLoading={Boolean(isSubmitting || isSubmittingForm)}
              >
                Register Provider
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
