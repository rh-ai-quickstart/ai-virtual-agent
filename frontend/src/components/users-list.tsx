import { User } from '@/services/users';
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
  Alert,
} from '@patternfly/react-core';
import { NewUserCard } from './new-user-card';

interface UsersListProps {
  users: User[];
  onUserClick: (user: User) => void;
}

export function UsersList({ users, onUserClick }: UsersListProps) {
  return (
    <PageSection>
      <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
        <FlexItem>
          <Title headingLevel="h1">Users</Title>
        </FlexItem>
        <FlexItem>
          <NewUserCard />
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
                            <DataListCell key="username">@{user.username}</DataListCell>,
                            <DataListCell key="email">{user.email}</DataListCell>,
                            <DataListCell key="role">
                              {user.role === 'devops'
                                ? 'DevOps'
                                : user.role === 'admin'
                                  ? 'Admin'
                                  : user.role === 'user'
                                    ? 'User'
                                    : user.role || 'User'}
                            </DataListCell>,
                            <DataListCell key="agents">
                              {user.agent_ids
                                ? `${user.agent_ids.length} agent${user.agent_ids.length !== 1 ? 's' : ''}`
                                : '0 agents'}
                            </DataListCell>,
                            <DataListCell key="actions">
                              <Button variant="primary" size="sm" onClick={() => onUserClick(user)}>
                                View Profile
                              </Button>
                            </DataListCell>,
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
