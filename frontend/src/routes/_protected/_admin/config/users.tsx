import { fetchUsers, User } from '@/services/users';
import { useQuery } from '@tanstack/react-query';
import { Flex, PageSection, Spinner, Alert } from '@patternfly/react-core';
import { createFileRoute, useNavigate } from '@tanstack/react-router';
import { UserProfile } from '@/components/user-profile';
import { UsersList } from '@/components/users-list';

export const Route = createFileRoute('/_protected/_admin/config/users')({
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

  const handleUserClick = (user: User) => {
    void navigate({ search: { userId: user.id } });
  };

  const handleBackToList = () => {
    void navigate({ search: { userId: undefined } });
  };

  // User profile view
  if (userId) {
    return <UserProfile userId={userId} onBackToList={handleBackToList} />;
  }

  // Loading state for users list
  if (isUsersLoading) {
    return (
      <PageSection>
        <Flex justifyContent={{ default: 'justifyContentCenter' }}>
          <Spinner size="lg" />
        </Flex>
      </PageSection>
    );
  }

  // Error state for users list
  if (usersError) {
    return (
      <PageSection>
        <Alert variant="danger" title="Error loading users">
          {usersError.message}
        </Alert>
      </PageSection>
    );
  }

  // Users list view
  return <UsersList users={users} onUserClick={handleUserClick} />;
}
