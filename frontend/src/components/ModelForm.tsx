import { useForm } from '@tanstack/react-form';
import { RegisterModelRequest, fetchProviderModels } from '@/services/models';
import {
  Button,
  ActionGroup,
  Form,
  FormGroup,
  TextInput,
  FormSelect,
  FormSelectOption,
  Spinner,
} from '@patternfly/react-core';
import { PaperPlaneIcon } from '@patternfly/react-icons';
import { useState, useEffect } from 'react';

interface ModelFormProps {
  isSubmitting: boolean;
  onSubmit: (values: RegisterModelRequest) => void;
  onCancel: () => void;
}

const PROVIDER_CONFIGS: Record<
  string,
  {
    label: string;
    urlPlaceholder: string;
    fields: Array<{
      name: string;
      label: string;
      type: 'text' | 'number' | 'select';
      required: boolean;
      placeholder?: string;
      defaultValue?: string | number | boolean;
      options?: Array<{ value: string; label: string }>;
      helpText?: string;
    }>;
  }
> = {
  'remote::vllm': {
    label: 'Remote vLLM',
    urlPlaceholder: 'http://localhost:8000/v1',
    fields: [
      {
        name: 'api_token',
        label: 'API Token',
        type: 'text',
        required: true,
        placeholder: 'fake',
        defaultValue: 'fake',
        helpText: 'API token for authentication',
      },
      {
        name: 'max_tokens',
        label: 'Max Tokens',
        type: 'number',
        required: true,
        placeholder: '4096',
        defaultValue: 4096,
        helpText: 'Maximum number of tokens',
      },
      {
        name: 'tls_verify',
        label: 'TLS Verify',
        type: 'select',
        required: false,
        defaultValue: false,
        options: [
          { value: 'true', label: 'Enabled' },
          { value: 'false', label: 'Disabled' },
        ],
        helpText: 'Verify TLS certificates',
      },
    ],
  },
  'remote::ollama': {
    label: 'Remote Ollama',
    urlPlaceholder: 'http://localhost:11434/v1',
    fields: [],
  },
};

export function ModelForm({ isSubmitting, onSubmit, onCancel }: ModelFormProps) {
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [providerType, setProviderType] = useState('');
  const [urlValue, setUrlValue] = useState('');

  const initialData = {
    model_id: '',
    provider_id: '',
    provider_type: '',
    url: '',
    api_token: 'fake',
    max_tokens: 4096,
    tls_verify: false,
  };

  const form = useForm({
    defaultValues: initialData,
    onSubmit: ({ value }) => {
      const config: Record<string, unknown> = { url: value.url };

      // Add provider-specific config fields
      const providerConfig = PROVIDER_CONFIGS[value.provider_type];
      if (providerConfig) {
        providerConfig.fields.forEach((field) => {
          if (field.name in value) {
            config[field.name] = value[field.name as keyof typeof value];
          }
        });
      }

      const request: RegisterModelRequest = {
        provider: {
          provider_id: value.provider_id,
          provider_type: value.provider_type,
          config,
        },
        model_id: value.model_id,
      };
      onSubmit(request);
    },
  });

  // Fetch models when URL changes
  useEffect(() => {
    const fetchModels = async () => {
      let url = urlValue;
      if (url && url.trim()) {
        // For Ollama, append /v1 if not present
        if (providerType === 'remote::ollama' && !url.includes('/v1')) {
          url = url.endsWith('/') ? `${url}v1` : `${url}/v1`;
        }

        setLoadingModels(true);
        try {
          const models = await fetchProviderModels(url);
          setAvailableModels(models);
        } catch (error) {
          console.error('Failed to fetch models:', error);
          setAvailableModels([]);
        } finally {
          setLoadingModels(false);
        }
      } else {
        setAvailableModels([]);
      }
    };

    const debounceTimer = setTimeout(() => {
      void fetchModels();
    }, 500);
    return () => clearTimeout(debounceTimer);
  }, [urlValue, providerType]);

  return (
    <Form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void form.handleSubmit();
      }}
    >
      <form.Field
        name="provider_id"
        validators={{
          onChange: ({ value }) => (!value ? 'Provider ID is required' : undefined),
        }}
      >
        {(field) => (
          <FormGroup label="Provider ID" isRequired fieldId="model-form-provider-id">
            <TextInput
              isRequired
              id="model-form-provider-id"
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
            <div style={{ fontSize: '14px', color: '#6a6e73', marginTop: '4px' }}>
              Unique identifier for the provider
            </div>
          </FormGroup>
        )}
      </form.Field>

      <form.Field
        name="provider_type"
        validators={{
          onChange: ({ value }) => (!value ? 'Provider Type is required' : undefined),
        }}
      >
        {(field) => (
          <FormGroup label="Provider Type" isRequired fieldId="model-form-provider-type">
            <FormSelect
              isRequired
              id="model-form-provider-type"
              value={field.state.value}
              onChange={(_e, v) => {
                field.handleChange(v);
                setProviderType(v);
              }}
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
            >
              <FormSelectOption value="" label="Select a provider type" isDisabled />
              {Object.entries(PROVIDER_CONFIGS).map(([value, config]) => (
                <FormSelectOption key={value} value={value} label={config.label} />
              ))}
            </FormSelect>
            {field.state.meta.errors.length > 0 && (
              <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                {field.state.meta.errors[0]}
              </div>
            )}
          </FormGroup>
        )}
      </form.Field>

      {providerType && PROVIDER_CONFIGS[providerType] && (
        <>
          <form.Field
            name="url"
            validators={{
              onChange: ({ value }) => (!value ? 'URL is required' : undefined),
            }}
          >
            {(field) => (
              <FormGroup label="URL" isRequired fieldId="model-form-url">
                <TextInput
                  isRequired
                  id="model-form-url"
                  value={field.state.value}
                  onChange={(_e, v) => {
                    field.handleChange(v);
                    setUrlValue(v);
                  }}
                  validated={
                    !field.state.meta.isTouched
                      ? 'default'
                      : field.state.meta.errors.length > 0
                        ? 'error'
                        : 'success'
                  }
                  placeholder={PROVIDER_CONFIGS[providerType].urlPlaceholder}
                />
                {field.state.meta.errors.length > 0 && (
                  <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                    {field.state.meta.errors[0]}
                  </div>
                )}
                <div style={{ fontSize: '14px', color: '#6a6e73', marginTop: '4px' }}>
                  {loadingModels ? (
                    <span>
                      <Spinner size="sm" /> Loading available models...
                    </span>
                  ) : (
                    `URL where the ${PROVIDER_CONFIGS[providerType].label} provider is hosted`
                  )}
                </div>
              </FormGroup>
            )}
          </form.Field>

          <form.Field
            name="model_id"
            validators={{
              onChange: ({ value }) => (!value ? 'Model ID is required' : undefined),
            }}
          >
            {(field) => (
              <FormGroup label="Model ID" isRequired fieldId="model-form-id">
                {availableModels.length > 0 ? (
                  <FormSelect
                    isRequired
                    id="model-form-id"
                    value={field.state.value}
                    onChange={(_e, v) => field.handleChange(v)}
                    validated={
                      !field.state.meta.isTouched
                        ? 'default'
                        : field.state.meta.errors.length > 0
                          ? 'error'
                          : 'success'
                    }
                  >
                    <FormSelectOption value="" label="Select a model" isDisabled />
                    {availableModels.map((modelId) => (
                      <FormSelectOption key={modelId} value={modelId} label={modelId} />
                    ))}
                  </FormSelect>
                ) : (
                  <div style={{ color: '#6a6e73', fontSize: '14px', fontStyle: 'italic' }}>
                    Enter a provider URL above to load available models
                  </div>
                )}
                {field.state.meta.errors.length > 0 && (
                  <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                    {field.state.meta.errors[0]}
                  </div>
                )}
                {availableModels.length > 0 && (
                  <div style={{ fontSize: '14px', color: '#6a6e73', marginTop: '4px' }}>
                    Select a model from the provider
                  </div>
                )}
              </FormGroup>
            )}
          </form.Field>

          {PROVIDER_CONFIGS[providerType].fields.map((fieldConfig) => {
            const fieldName = fieldConfig.name as 'api_token' | 'max_tokens' | 'tls_verify';
            return (
              <form.Field
                key={fieldConfig.name}
                name={fieldName}
                validators={{
                  onChange: ({ value }) =>
                    fieldConfig.required && !value ? `${fieldConfig.label} is required` : undefined,
                }}
              >
                {(field) => (
                  <FormGroup
                    label={fieldConfig.label}
                    isRequired={fieldConfig.required}
                    fieldId={`model-form-${fieldConfig.name}`}
                  >
                    {fieldConfig.type === 'select' ? (
                      <FormSelect
                        id={`model-form-${fieldConfig.name}`}
                        value={String(field.state.value)}
                        onChange={(_e, v) => field.handleChange(v === 'true')}
                      >
                        {fieldConfig.options?.map((option) => (
                          <FormSelectOption
                            key={option.value}
                            value={option.value}
                            label={option.label}
                          />
                        ))}
                      </FormSelect>
                    ) : fieldConfig.type === 'number' ? (
                      <TextInput
                        type="number"
                        isRequired={fieldConfig.required}
                        id={`model-form-${fieldConfig.name}`}
                        value={String(field.state.value)}
                        onChange={(_e, v) => field.handleChange(parseInt(v) || 0)}
                        validated={
                          !field.state.meta.isTouched
                            ? 'default'
                            : field.state.meta.errors.length > 0
                              ? 'error'
                              : 'success'
                        }
                        placeholder={fieldConfig.placeholder}
                      />
                    ) : (
                      <TextInput
                        isRequired={fieldConfig.required}
                        id={`model-form-${fieldConfig.name}`}
                        value={String(field.state.value)}
                        onChange={(_e, v) => field.handleChange(v)}
                        validated={
                          !field.state.meta.isTouched
                            ? 'default'
                            : field.state.meta.errors.length > 0
                              ? 'error'
                              : 'success'
                        }
                        placeholder={fieldConfig.placeholder}
                      />
                    )}
                    {field.state.meta.errors.length > 0 && (
                      <div style={{ color: '#c9190b', fontSize: '14px', marginTop: '4px' }}>
                        {field.state.meta.errors[0]}
                      </div>
                    )}
                    {fieldConfig.helpText && (
                      <div style={{ fontSize: '14px', color: '#6a6e73', marginTop: '4px' }}>
                        {fieldConfig.helpText}
                      </div>
                    )}
                  </FormGroup>
                )}
              </form.Field>
            );
          })}
        </>
      )}

      <ActionGroup>
        <Button
          variant="primary"
          type="submit"
          icon={<PaperPlaneIcon />}
          isLoading={isSubmitting}
          isDisabled={isSubmitting}
        >
          {isSubmitting ? 'Registering...' : 'Register Model'}
        </Button>
        <Button variant="link" onClick={onCancel} isDisabled={isSubmitting}>
          Cancel
        </Button>
      </ActionGroup>
    </Form>
  );
}
