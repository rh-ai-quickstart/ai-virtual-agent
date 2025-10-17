import { PageSection } from '@patternfly/react-core';
import { createFileRoute } from '@tanstack/react-router';
import { ModelList } from '@/components/ModelList';

export const Route = createFileRoute('/_protected/_admin/config/models')({
  component: Models,
});

function Models() {
  return (
    <PageSection hasBodyWrapper={false}>
      <ModelList />
    </PageSection>
  );
}
