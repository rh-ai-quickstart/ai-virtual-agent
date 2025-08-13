import { NewUser, UpdateUser } from '@/services/users';
import {
  Card,
  CardBody,
  CardExpandableContent,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  Title,
  Alert,
} from '@patternfly/react-core';
import { PlusIcon } from '@patternfly/react-icons';
import { useState } from 'react';
import { UserForm } from './user-form';
import { useAgents } from '@/hooks';
import { useUsers } from '@/hooks/useUsers';

export function NewUserCard() {
  const [isOpen, setIsOpen] = useState(false);

  // Use custom hooks
  const { agents, isLoading: isLoadingAgents, error: agentsError } = useAgents();
  const { createUser, isCreating, createError } = useUsers();

  const handleCreateUser = (values: NewUser | UpdateUser) => {
    void (async () => {
      try {
        // Since we're in create mode, we expect NewUser with all required fields
        const newUserData: NewUser = {
          username: values.username!,
          email: values.email!,
          role: values.role!,
          agent_ids: 'agent_ids' in values ? values.agent_ids : [],
        };

        await createUser(newUserData);
        setIsOpen(false);
        console.log('User created successfully');
      } catch (error) {
        console.error('Error creating user:', error);
      }
    })();
  };

  return (
    <Flex direction={{ default: 'column' }}>
      <FlexItem>
        <Card isExpanded={isOpen} isClickable={!isOpen}>
          <CardHeader
            selectableActions={{
              onClickAction: () => setIsOpen(!isOpen),
              selectableActionAriaLabelledby: 'clickable-user-card-title-1',
            }}
          >
            <CardTitle>
              {!isOpen ? (
                <Flex>
                  <FlexItem>
                    <PlusIcon />
                  </FlexItem>
                  <FlexItem>
                    <Title headingLevel="h3">New User</Title>
                  </FlexItem>
                </Flex>
              ) : (
                <Title headingLevel="h3">New User</Title>
              )}
            </CardTitle>
          </CardHeader>
          <CardExpandableContent>
            <CardBody>
              <Flex direction={{ default: 'column' }} gap={{ default: 'gapLg' }}>
                <FlexItem>
                  <UserForm
                    mode="create"
                    availableAgents={agents || []}
                    isLoadingAgents={isLoadingAgents}
                    agentsError={agentsError}
                    isSubmitting={isCreating}
                    onSubmit={handleCreateUser}
                    onCancel={() => setIsOpen(false)}
                    error={createError}
                  />
                </FlexItem>
                {createError && (
                  <FlexItem>
                    <Alert variant="danger" title="Failed to create user" className="pf-v6-u-mt-md">
                      {createError?.message || 'An unexpected error occurred.'}
                    </Alert>
                  </FlexItem>
                )}
              </Flex>
            </CardBody>
          </CardExpandableContent>
        </Card>
      </FlexItem>
    </Flex>
  );
}
