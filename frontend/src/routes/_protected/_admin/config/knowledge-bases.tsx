import { KnowledgeBaseList } from '@/components/knowledge-base-list';
import { PageSection } from '@patternfly/react-core';
import { createFileRoute } from '@tanstack/react-router';

export const Route = createFileRoute('/_protected/_admin/config/knowledge-bases')({
  component: KnowledgeBases,
});

export function KnowledgeBases() {
  return (
    <PageSection>
      <KnowledgeBaseList />
    </PageSection>
  );
}
