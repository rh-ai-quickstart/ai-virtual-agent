import { createFileRoute } from '@tanstack/react-router';
import { PageSection, Flex, Spinner, Alert } from '@patternfly/react-core';
import { useCurrentUser } from '@/contexts/UserContext';
import { UserProfile } from '@/components/user-profile';

export const Route = createFileRoute('/_protected/config/profile')({
  component: UserProfilePage,
});

function UserProfilePage() {
  const { currentUser, isLoading, error } = useCurrentUser();

  if (isLoading) {
    return (
      <PageSection>
        <Flex justifyContent={{ default: 'justifyContentCenter' }}>
          <Spinner size="lg" />
        </Flex>
      </PageSection>
    );
  }

  if (error || !currentUser) {
    return (
      <PageSection>
        <Alert variant="danger" title="Error loading user">
          {error || 'User not authenticated'}
        </Alert>
      </PageSection>
    );
  }

  return (
    <UserProfile
      userId={currentUser.id}
      onBackToList={() => {
        /* no-op for non-admin */
      }}
    />
  );
}
