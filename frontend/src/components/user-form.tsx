import { useForm } from '@tanstack/react-form';
import { NewUser, UpdateUser, User } from '@/services/users';
import { Agent } from '@/types';
import {
  Button,
  ActionGroup,
  Form,
  FormGroup,
  TextInput,
  Alert,
  FormSelect,
  FormSelectOption,
  Checkbox,
  Flex,
  FlexItem,
  Dropdown,
  DropdownList,
  DropdownItem,
  MenuToggle,
  MenuToggleElement,
  Label,
  LabelGroup,
} from '@patternfly/react-core';
import { useState } from 'react';
import type { Ref } from 'react';
import { PaperPlaneIcon } from '@patternfly/react-icons';

const ROLE_OPTIONS = [
  { value: '', label: 'Select a role', disabled: true },
  { value: 'user', label: 'User', disabled: false },
  { value: 'devops', label: 'DevOps', disabled: false },
  { value: 'admin', label: 'Admin', disabled: false },
];

interface UserFormProps {
  mode: 'create' | 'edit';
  availableAgents?: Agent[];
  isLoadingAgents?: boolean;
  agentsError?: Error | null;
  initialUser?: Partial<User>;
  isSubmitting: boolean;
  onSubmit: (values: NewUser | UpdateUser) => void;
  onCancel: () => void;
  error?: Error | null;
  showButtons?: boolean;
}

export function UserForm({
  mode,
  availableAgents = [],
  isLoadingAgents = false,
  agentsError,
  initialUser,
  isSubmitting,
  onSubmit,
  onCancel,
  error,
  showButtons = true,
}: UserFormProps) {
  const [selectedAgentIds, setSelectedAgentIds] = useState<string[]>(initialUser?.agent_ids || []);
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);

  const initialData = initialUser
    ? {
        username: initialUser.username || '',
        email: initialUser.email || '',
        role: initialUser.role || 'user',
        agent_ids: initialUser.agent_ids || [],
      }
    : {
        username: '',
        email: '',
        role: 'user',
        agent_ids: [],
      };

  const form = useForm({
    defaultValues: initialData,
    onSubmit: ({ value }) => {
      if (mode === 'create') {
        const finalValue: NewUser = {
          username: value.username,
          email: value.email,
          role: value.role as 'user' | 'devops' | 'admin',
          agent_ids: selectedAgentIds,
        };
        onSubmit(finalValue);
      } else {
        const finalValue: UpdateUser = {
          username: value.username,
          email: value.email,
          role: value.role as 'user' | 'devops' | 'admin',
        };
        onSubmit(finalValue);
      }
    },
  });

  const validateEmail = (email: string): string | undefined => {
    if (!email.trim()) return 'Email is required';
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) return 'Please enter a valid email address';
    return undefined;
  };

  const validateUsername = (username: string): string | undefined => {
    if (!username.trim()) return 'Username is required';
    if (username.length < 3) return 'Username must be at least 3 characters';
    if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
      return 'Username can only contain letters, numbers, hyphens, and underscores';
    }
    return undefined;
  };

  const handleAddAgent = (agentId: string) => {
    setSelectedAgentIds((prev) => {
      if (!prev.includes(agentId)) {
        return [...prev, agentId];
      }
      return prev;
    });
  };

  const handleRemoveAgent = (agentId: string) => {
    setSelectedAgentIds((prev) => prev.filter((id) => id !== agentId));
  };

  return (
    <Form
      onSubmit={(e) => {
        e.preventDefault();
        e.stopPropagation();
        void form.handleSubmit();
      }}
      data-user-edit-form={mode === 'edit' ? 'true' : undefined}
    >
      {error && (
        <Alert
          variant="danger"
          title={`Error ${mode === 'create' ? 'creating' : 'updating'} user`}
          className="pf-v6-u-mb-md"
        >
          {error.message}
        </Alert>
      )}

      <form.Field name="username" validators={{ onChange: ({ value }) => validateUsername(value) }}>
        {(field) => (
          <FormGroup label="Username" isRequired fieldId="user-form-username">
            <TextInput
              isRequired
              id="user-form-username"
              value={field.state.value}
              onChange={(_e, v) => field.handleChange(v)}
              placeholder="Enter username"
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

      <form.Field name="email" validators={{ onChange: ({ value }) => validateEmail(value) }}>
        {(field) => (
          <FormGroup label="Email" isRequired fieldId="user-form-email">
            <TextInput
              isRequired
              type="email"
              id="user-form-email"
              value={field.state.value}
              onChange={(_e, v) => field.handleChange(v)}
              placeholder="Enter email address"
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

      <form.Field
        name="role"
        validators={{
          onChange: ({ value }) => (!value ? 'Role is required' : undefined),
        }}
      >
        {(field) => (
          <FormGroup label="Role" isRequired fieldId="user-form-role">
            <FormSelect
              isRequired
              id="user-form-role"
              name={field.name}
              value={field.state.value}
              onBlur={field.handleBlur}
              onChange={(_event, value) => field.handleChange(value)}
              aria-label="Select Role"
              validated={
                !field.state.meta.isTouched
                  ? 'default'
                  : field.state.meta.errors.length > 0
                    ? 'error'
                    : 'success'
              }
            >
              {ROLE_OPTIONS.map((opt) => (
                <FormSelectOption
                  key={opt.value}
                  value={opt.value}
                  label={opt.label}
                  isDisabled={opt.disabled}
                />
              ))}
            </FormSelect>
          </FormGroup>
        )}
      </form.Field>

      {mode === 'create' && (
        <FormGroup label="Assign Agents" fieldId="user-form-agents">
          {isLoadingAgents ? (
            <div>Loading agents...</div>
          ) : agentsError ? (
            <Alert variant="warning" title="Error loading agents" className="pf-v6-u-mb-md">
              {agentsError.message}
            </Alert>
          ) : availableAgents.length === 0 ? (
            <div>No agents available to assign</div>
          ) : (
            <Flex direction={{ default: 'column' }} gap={{ default: 'gapSm' }}>
              <FlexItem>
                <Dropdown
                  isOpen={agentDropdownOpen}
                  onOpenChange={(isOpen) => setAgentDropdownOpen(isOpen)}
                  toggle={(toggleRef: Ref<MenuToggleElement>) => (
                    <MenuToggle
                      ref={toggleRef}
                      onClick={() => setAgentDropdownOpen(!agentDropdownOpen)}
                      isExpanded={agentDropdownOpen}
                    >
                      Add Agent
                    </MenuToggle>
                  )}
                  shouldFocusToggleOnSelect
                >
                  <DropdownList>
                    {availableAgents.map((agent) => {
                      const isAssigned = selectedAgentIds.includes(agent.id);

                      return (
                        <DropdownItem
                          key={agent.id}
                          onClick={() => {
                            if (!isAssigned) {
                              handleAddAgent(agent.id);
                            }
                          }}
                          isDisabled={isAssigned}
                        >
                          <Flex
                            alignItems={{ default: 'alignItemsCenter' }}
                            gap={{ default: 'gapSm' }}
                          >
                            <Checkbox
                              isChecked={isAssigned}
                              id={`agent-${agent.id}`}
                              name={`agent-${agent.id}`}
                              onChange={() => {
                                if (!isAssigned) {
                                  handleAddAgent(agent.id);
                                }
                              }}
                            />
                            <FlexItem>
                              <span>{agent.name}</span>
                            </FlexItem>
                          </Flex>
                        </DropdownItem>
                      );
                    })}
                  </DropdownList>
                </Dropdown>
              </FlexItem>
              <FlexItem>
                {selectedAgentIds.length > 0 ? (
                  <LabelGroup>
                    {selectedAgentIds.map((agentId) => {
                      const agent = availableAgents.find((a) => a.id === agentId);

                      return (
                        <Label
                          key={agentId}
                          color="blue"
                          onClose={() => handleRemoveAgent(agentId)}
                          closeBtnAriaLabel={`Remove ${agent?.name || agentId}`}
                        >
                          {agent?.name || agentId}
                        </Label>
                      );
                    })}
                  </LabelGroup>
                ) : (
                  <span style={{ color: '#6a6e73', fontStyle: 'italic' }}>No agents assigned</span>
                )}
              </FlexItem>
            </Flex>
          )}
        </FormGroup>
      )}

      {showButtons && (
        <ActionGroup>
          <form.Subscribe
            selector={(state) => [state.canSubmit, state.isSubmitting, state.isPristine]}
          >
            {([canSubmit, isSubmitting, isPristine]) => (
              <Button
                icon={<PaperPlaneIcon />}
                type="submit"
                variant="primary"
                isDisabled={!canSubmit || isSubmitting || isPristine}
                isLoading={isSubmitting}
              >
                {mode === 'create' ? 'Create User' : 'Save Changes'}
              </Button>
            )}
          </form.Subscribe>
          <Button variant="link" onClick={onCancel} isDisabled={isSubmitting}>
            Cancel
          </Button>
        </ActionGroup>
      )}
    </Form>
  );
}
