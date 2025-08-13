import {
  fetchUserById,
  updateUserAgents,
  removeUserAgents,
  updateUser,
  deleteUser,
  UpdateUser,
} from '@/services/users';
import { fetchAgents } from '@/services/agents';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  PageSection,
  Title,
  Button,
  Spinner,
  Alert,
  DescriptionList,
  DescriptionListGroup,
  DescriptionListTerm,
  DescriptionListDescription,
  Label,
  LabelGroup,
  Dropdown,
  DropdownList,
  DropdownItem,
  MenuToggle,
  MenuToggleElement,
  Checkbox,
  ActionGroup,
  Modal,
  ModalVariant,
  ModalHeader,
  ModalBody,
  ModalFooter,
} from '@patternfly/react-core';
import { ArrowLeftIcon } from '@patternfly/react-icons';
import { useState } from 'react';
import type { Ref } from 'react';
import { UserForm } from './user-form';

interface UserProfileProps {
  userId: string;
  onBackToList: () => void;
}

export function UserProfile({ userId, onBackToList }: UserProfileProps) {
  const queryClient = useQueryClient();

  // Agent management state
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);

  // Edit mode state
  const [isEditing, setIsEditing] = useState(false);

  // Delete confirmation state
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  // Query for specific user profile
  const {
    data: userProfile,
    isLoading: isUserProfileLoading,
    error: userProfileError,
  } = useQuery({
    queryKey: ['user', userId],
    queryFn: () => fetchUserById(userId),
    enabled: !!userId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Query for available agents
  const {
    data: availableAgents = [],
    isLoading: isAgentsLoading,
    error: agentsError,
  } = useQuery({
    queryKey: ['agents'],
    queryFn: fetchAgents,
    enabled: !!userId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Mutation for adding agents to user
  const addAgentMutation = useMutation({
    mutationFn: ({ userId, agentId }: { userId: string; agentId: string }) => {
      const currentAgents = userProfile?.agent_ids || [];
      return updateUserAgents(userId, [...currentAgents, agentId]);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['user', userId] });
      void queryClient.invalidateQueries({ queryKey: ['users'] });
      void queryClient.invalidateQueries({ queryKey: ['currentUser'] });
    },
    onError: (error) => {
      console.error('Error adding agent:', error);
    },
  });

  // Mutation for removing agents from user
  const removeAgentMutation = useMutation({
    mutationFn: ({ userId, agentId }: { userId: string; agentId: string }) => {
      return removeUserAgents(userId, [agentId]);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['user', userId] });
      void queryClient.invalidateQueries({ queryKey: ['users'] });
      void queryClient.invalidateQueries({ queryKey: ['currentUser'] });
    },
    onError: (error) => {
      console.error('Error removing agent:', error);
    },
  });

  // Mutation for updating user details
  const updateUserMutation = useMutation({
    mutationFn: ({ userId, updates }: { userId: string; updates: UpdateUser }) => {
      return updateUser(userId, updates);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['user', userId] });
      void queryClient.invalidateQueries({ queryKey: ['users'] });
      void queryClient.invalidateQueries({ queryKey: ['currentUser'] });
      setIsEditing(false);
    },
    onError: (error) => {
      console.error('Error updating user:', error);
    },
  });

  // Mutation for deleting user
  const deleteUserMutation = useMutation({
    mutationFn: (userId: string) => {
      return deleteUser(userId);
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['users'] });
      void queryClient.invalidateQueries({ queryKey: ['currentUser'] });
      setIsDeleteModalOpen(false);
      onBackToList();
    },
    onError: (error) => {
      console.error('Error deleting user:', error);
      setIsDeleteModalOpen(false);
    },
  });

  // Derive loading and error states
  const loading = isUserProfileLoading || isAgentsLoading;
  const error = userProfileError?.message || agentsError?.message || null;

  // Event handlers
  const handleAddAgent = (agentId: string) => {
    if (!userProfile) return;
    addAgentMutation.mutate({ userId: userProfile.id, agentId });
  };

  const handleRemoveAgent = (agentId: string) => {
    if (!userProfile) return;
    removeAgentMutation.mutate({ userId: userProfile.id, agentId });
  };

  const handleEditClick = () => {
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
  };

  const handleDeleteClick = () => {
    setIsDeleteModalOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (!userProfile) return;
    deleteUserMutation.mutate(userProfile.id);
  };

  const handleDeleteCancel = () => {
    setIsDeleteModalOpen(false);
  };

  if (loading) {
    return (
      <PageSection>
        <Flex justifyContent={{ default: 'justifyContentCenter' }}>
          <Spinner size="lg" />
        </Flex>
      </PageSection>
    );
  }

  if (error) {
    return (
      <PageSection>
        <Alert variant="danger" title="Error loading user profile">
          {error}
        </Alert>
      </PageSection>
    );
  }

  if (!userProfile) {
    return (
      <PageSection>
        <Alert variant="warning" title="User not found">
          The requested user could not be found.
        </Alert>
      </PageSection>
    );
  }

  return (
    <PageSection>
      <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
        <FlexItem>
          <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
            <Button variant="link" icon={<ArrowLeftIcon />} onClick={onBackToList}>
              Back to Users
            </Button>
            <Title headingLevel="h1">User Profile</Title>
          </Flex>
        </FlexItem>
        <FlexItem>
          <Card>
            <CardHeader>
              <Flex justifyContent={{ default: 'justifyContentSpaceBetween' }}>
                <CardTitle>{userProfile.username}</CardTitle>
                <FlexItem>
                  {!isEditing ? (
                    <Flex columnGap={{ default: 'columnGapSm' }}>
                      <Button
                        variant="danger"
                        onClick={handleDeleteClick}
                        isLoading={deleteUserMutation.isPending}
                      >
                        Delete Profile
                      </Button>
                      <Button variant="secondary" onClick={handleEditClick}>
                        Edit Profile
                      </Button>
                    </Flex>
                  ) : (
                    <ActionGroup>
                      <Button
                        variant="primary"
                        onClick={() => {
                          const form = document.querySelector(
                            'form[data-user-edit-form]'
                          ) as HTMLFormElement;
                          if (form) {
                            form.requestSubmit();
                          }
                        }}
                        isLoading={updateUserMutation.isPending}
                      >
                        Save Changes
                      </Button>
                      <Button variant="link" onClick={handleCancelEdit}>
                        Cancel
                      </Button>
                    </ActionGroup>
                  )}
                </FlexItem>
              </Flex>
            </CardHeader>
            <CardBody>
              {!isEditing ? (
                <DescriptionList>
                  <DescriptionListGroup>
                    <DescriptionListTerm>ID</DescriptionListTerm>
                    <DescriptionListDescription>{userProfile.id}</DescriptionListDescription>
                  </DescriptionListGroup>
                  <DescriptionListGroup>
                    <DescriptionListTerm>Username</DescriptionListTerm>
                    <DescriptionListDescription>{userProfile.username}</DescriptionListDescription>
                  </DescriptionListGroup>
                  <DescriptionListGroup>
                    <DescriptionListTerm>Email</DescriptionListTerm>
                    <DescriptionListDescription>{userProfile.email}</DescriptionListDescription>
                  </DescriptionListGroup>
                  {userProfile.role && (
                    <DescriptionListGroup>
                      <DescriptionListTerm>Role</DescriptionListTerm>
                      <DescriptionListDescription>{userProfile.role}</DescriptionListDescription>
                    </DescriptionListGroup>
                  )}
                </DescriptionList>
              ) : (
                <UserForm
                  mode="edit"
                  initialUser={userProfile}
                  isSubmitting={updateUserMutation.isPending}
                  onSubmit={(values) => {
                    updateUserMutation.mutate({
                      userId: userProfile.id,
                      updates: values as UpdateUser,
                    });
                  }}
                  onCancel={handleCancelEdit}
                  error={updateUserMutation.error}
                  showButtons={false}
                />
              )}
              <DescriptionList style={{ marginTop: '24px' }}>
                <DescriptionListGroup>
                  <DescriptionListTerm>Assigned Agents</DescriptionListTerm>
                  <DescriptionListDescription>
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
                              const isAssigned = userProfile.agent_ids?.includes(agent.id);
                              const isLoading =
                                addAgentMutation.isPending &&
                                addAgentMutation.variables?.agentId === agent.id;
                              const hasError =
                                addAgentMutation.isError &&
                                addAgentMutation.variables?.agentId === agent.id;

                              return (
                                <DropdownItem
                                  key={agent.id}
                                  onClick={() => {
                                    if (!isAssigned && !isLoading) {
                                      handleAddAgent(agent.id);
                                    }
                                  }}
                                  isDisabled={isAssigned || isLoading}
                                >
                                  <Flex
                                    alignItems={{ default: 'alignItemsCenter' }}
                                    gap={{ default: 'gapSm' }}
                                  >
                                    <Checkbox
                                      isChecked={isAssigned}
                                      isDisabled={isLoading}
                                      id={`agent-${agent.id}`}
                                      name={`agent-${agent.id}`}
                                      onChange={() => {
                                        if (!isAssigned && !isLoading) {
                                          handleAddAgent(agent.id);
                                        }
                                      }}
                                    />
                                    <FlexItem>
                                      <span>{agent.name}</span>
                                      {isLoading && (
                                        <Spinner size="sm" style={{ marginLeft: '8px' }} />
                                      )}
                                      {hasError && (
                                        <span
                                          style={{
                                            color: 'red',
                                            fontSize: '0.8em',
                                            marginLeft: '8px',
                                          }}
                                        >
                                          {addAgentMutation.error?.message || 'Failed to add agent'}
                                        </span>
                                      )}
                                    </FlexItem>
                                  </Flex>
                                </DropdownItem>
                              );
                            })}
                          </DropdownList>
                        </Dropdown>
                      </FlexItem>
                      <FlexItem>
                        {userProfile.agent_ids && userProfile.agent_ids.length > 0 ? (
                          <LabelGroup>
                            {userProfile.agent_ids.map((agentId) => {
                              const agent = availableAgents.find((a) => a.id === agentId);
                              const isLoading =
                                removeAgentMutation.isPending &&
                                removeAgentMutation.variables?.agentId === agentId;

                              return (
                                <Label
                                  key={agentId}
                                  color="blue"
                                  onClose={isLoading ? undefined : () => handleRemoveAgent(agentId)}
                                  closeBtnAriaLabel={`Remove ${agent?.name || agentId}`}
                                >
                                  {agent?.name || agentId}
                                  {isLoading && <Spinner size="sm" style={{ marginLeft: '8px' }} />}
                                  {removeAgentMutation.isError &&
                                    removeAgentMutation.variables?.agentId === agentId && (
                                      <span
                                        style={{
                                          color: 'red',
                                          fontSize: '0.8em',
                                          marginLeft: '8px',
                                        }}
                                      >
                                        Error
                                      </span>
                                    )}
                                </Label>
                              );
                            })}
                          </LabelGroup>
                        ) : (
                          <span style={{ color: '#6a6e73', fontStyle: 'italic' }}>
                            No agents assigned
                          </span>
                        )}
                      </FlexItem>
                    </Flex>
                  </DescriptionListDescription>
                </DescriptionListGroup>
                <DescriptionListGroup>
                  <DescriptionListTerm>Created</DescriptionListTerm>
                  <DescriptionListDescription>
                    {new Date(userProfile.created_at).toLocaleString()}
                  </DescriptionListDescription>
                </DescriptionListGroup>
                <DescriptionListGroup>
                  <DescriptionListTerm>Updated</DescriptionListTerm>
                  <DescriptionListDescription>
                    {new Date(userProfile.updated_at).toLocaleString()}
                  </DescriptionListDescription>
                </DescriptionListGroup>
              </DescriptionList>
            </CardBody>
          </Card>
        </FlexItem>
      </Flex>

      {/* Delete Confirmation Modal */}
      <Modal
        variant={ModalVariant.small}
        isOpen={isDeleteModalOpen}
        onClose={handleDeleteCancel}
        aria-labelledby="delete-user-modal-title"
        aria-describedby="delete-user-modal-desc"
      >
        <ModalHeader title="Delete Profile" labelId="delete-user-modal-title" />
        <ModalBody id="delete-user-modal-desc">
          <p>
            Are you sure you want to delete the profile for <strong>{userProfile.username}</strong>?
          </p>
          <br />
          <p>
            This action cannot be undone. All user data and associated agent assignments will be
            permanently removed.
          </p>
        </ModalBody>
        <ModalFooter>
          <Button
            variant="danger"
            onClick={handleDeleteConfirm}
            isLoading={deleteUserMutation.isPending}
          >
            Delete Profile
          </Button>
          <Button variant="link" onClick={handleDeleteCancel}>
            Cancel
          </Button>
        </ModalFooter>
      </Modal>
    </PageSection>
  );
}
