import { fetchUsers, fetchUserById, updateUserAgents, removeUserAgents, User } from '@/services/users';
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
  DataList,
  DataListItem,
  DataListItemRow,
  DataListItemCells,
  DataListCell,
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
} from '@patternfly/react-core';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { ArrowLeftIcon } from '@patternfly/react-icons';
import { useState } from 'react';
import type { Ref } from 'react';

export const Route = createFileRoute('/config/users')({
  component: Users,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      userId: search.userId as string | undefined,
    };
  },
});

function Users() {
  const { userId } = Route.useSearch();
  const navigate = useNavigate({ from: '/config/users' });
  const queryClient = useQueryClient();

  // Agent management state
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);

  // Query for users list (when not viewing a specific user)
  const {
    data: users = [],
    isLoading: isUsersLoading,
    error: usersError,
  } = useQuery({
    queryKey: ['users'],
    queryFn: fetchUsers,
    enabled: !userId, // Only fetch when not viewing a specific user
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Query for specific user profile (when userId is provided)
  const {
    data: userProfile,
    isLoading: isUserProfileLoading,
    error: userProfileError,
  } = useQuery({
    queryKey: ['user', userId],
    queryFn: () => fetchUserById(userId!),
    enabled: !!userId, // Only fetch when userId is provided
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Query for available agents (when in profile view)
  const {
    data: availableAgents = [],
    isLoading: isAgentsLoading,
    error: agentsError,
  } = useQuery({
    queryKey: ['agents'],
    queryFn: fetchAgents,
    enabled: !!userId, // Only fetch when viewing a user profile
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Mutation for adding agents to user
  const addAgentMutation = useMutation({
    mutationFn: ({ userId, agentId }: { userId: string; agentId: string }) => {
      const currentAgents = userProfile?.agent_ids || [];
      return updateUserAgents(userId, [...currentAgents, agentId]);
    },
    onSuccess: () => {
      // Invalidate user profile data to update the current view
      queryClient.invalidateQueries({ queryKey: ['user', userId] });
      // Invalidate users list to update agent counts on the users list page
      queryClient.invalidateQueries({ queryKey: ['users'] });
      // Invalidate current user if they are the same user being updated
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
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
      // Invalidate user profile data to update the current view
      queryClient.invalidateQueries({ queryKey: ['user', userId] });
      // Invalidate users list to update agent counts on the users list page
      queryClient.invalidateQueries({ queryKey: ['users'] });
      // Invalidate current user if they are the same user being updated
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
    },
    onError: (error) => {
      console.error('Error removing agent:', error);
    },
  });

  // Derive loading and error states from queries
  const loading = isUsersLoading || isUserProfileLoading || isAgentsLoading;
  const error = usersError?.message || userProfileError?.message || agentsError?.message || null;

  const handleAddAgent = (agentId: string) => {
    if (!userProfile) return;
    addAgentMutation.mutate({ userId: userProfile.id, agentId });
  };

  const handleRemoveAgent = (agentId: string) => {
    if (!userProfile) return;
    removeAgentMutation.mutate({ userId: userProfile.id, agentId });
  };

  const handleUserClick = (user: User) => {
    navigate({ search: { userId: user.id } });
  };

  const handleBackToList = () => {
    navigate({ search: { userId: undefined } });
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
        <Alert variant="danger" title="Error loading users">
          {error}
        </Alert>
      </PageSection>
    );
  }

  // User profile view
  if (userId && userProfile) {
    return (
      <PageSection>
        <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
          <FlexItem>
            <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
              <Button variant="link" icon={<ArrowLeftIcon />} onClick={handleBackToList}>
                Back to Users
              </Button>
              <Title headingLevel="h1">User Profile</Title>
            </Flex>
          </FlexItem>
          <FlexItem>
            <Card>
              <CardHeader>
                <CardTitle>{userProfile.username}</CardTitle>
              </CardHeader>
              <CardBody>
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
                                const isLoading = addAgentMutation.isPending && addAgentMutation.variables?.agentId === agent.id;
                                const hasError = addAgentMutation.isError && addAgentMutation.variables?.agentId === agent.id;

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
                                    <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
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
                                        {isLoading && <Spinner size="sm" style={{ marginLeft: '8px' }} />}
                                        {hasError && (
                                          <span style={{ color: 'red', fontSize: '0.8em', marginLeft: '8px' }}>
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
                                const agent = availableAgents.find(a => a.id === agentId);
                                const isLoading = removeAgentMutation.isPending && removeAgentMutation.variables?.agentId === agentId;

                                return (
                                  <Label
                                    key={agentId}
                                    color="blue"
                                    onClose={isLoading ? undefined : () => handleRemoveAgent(agentId)}
                                    closeBtnAriaLabel={`Remove ${agent?.name || agentId}`}
                                  >
                                    {agent?.name || agentId}
                                    {isLoading && <Spinner size="sm" style={{ marginLeft: '8px' }} />}
                                    {removeAgentMutation.isError && removeAgentMutation.variables?.agentId === agentId && (
                                      <span style={{ color: 'red', fontSize: '0.8em', marginLeft: '8px' }}>
                                        Error
                                      </span>
                                    )}
                                  </Label>
                                );
                              })}
                            </LabelGroup>
                          ) : (
                            <span style={{ color: '#6a6e73', fontStyle: 'italic' }}>No agents assigned</span>
                          )}
                        </FlexItem>
                      </Flex>
                    </DescriptionListDescription>
                  </DescriptionListGroup>
                  <DescriptionListGroup>
                    <DescriptionListTerm>Created</DescriptionListTerm>
                    <DescriptionListDescription>{new Date(userProfile.created_at).toLocaleString()}</DescriptionListDescription>
                  </DescriptionListGroup>
                  <DescriptionListGroup>
                    <DescriptionListTerm>Updated</DescriptionListTerm>
                    <DescriptionListDescription>{new Date(userProfile.updated_at).toLocaleString()}</DescriptionListDescription>
                  </DescriptionListGroup>
                </DescriptionList>
              </CardBody>
            </Card>
          </FlexItem>
        </Flex>
      </PageSection>
    );
  }

  // Users list view
  return (
    <PageSection>
      <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
        <FlexItem>
          <Title headingLevel="h1">Users</Title>
        </FlexItem>
        <FlexItem>
          <Card>
            <CardHeader>
              <CardTitle>All Users</CardTitle>
            </CardHeader>
            <CardBody>
              {users.length === 0 ? (
                <Alert variant="info" title="No users found" />
              ) : (
                <DataList aria-label="Users list">
                  {users.map((user) => (
                    <DataListItem key={user.id} aria-labelledby={`user-${user.id}`}>
                      <DataListItemRow>
                        <DataListItemCells
                          dataListCells={[
                            <DataListCell key="username">
                              @{user.username}
                            </DataListCell>,
                            <DataListCell key="email">
                              {user.email}
                            </DataListCell>,
                            <DataListCell key="role">
                              {user.role || 'User'}
                            </DataListCell>,
                            <DataListCell key="agents">
                              {user.agent_ids ? `${user.agent_ids.length} agent${user.agent_ids.length !== 1 ? 's' : ''}` : '0 agents'}
                            </DataListCell>,
                            <DataListCell key="actions">
                              <Button
                                variant="primary"
                                size="sm"
                                onClick={() => handleUserClick(user)}
                              >
                                View Profile
                              </Button>
                            </DataListCell>
                          ]}
                        />
                      </DataListItemRow>
                    </DataListItem>
                  ))}
                </DataList>
              )}
            </CardBody>
          </Card>
        </FlexItem>
      </Flex>
    </PageSection>
  );
}
