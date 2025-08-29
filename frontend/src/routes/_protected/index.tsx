import { Chat } from '@/components/chat';
import { Page, PageSection } from '@patternfly/react-core';
import { createFileRoute, useSearch } from '@tanstack/react-router';
import { Masthead } from '../../components/masthead';

export const Route = createFileRoute('/_protected/')({
  component: ChatPage,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      agentId: (search.agentId as string) ?? undefined,
    };
  },
});

const pageId = 'primary-app-container';

function ChatPage() {
  const search = useSearch({ from: '/_protected/' });

  return (
    <Page mainContainerId={pageId} masthead={<Masthead />} style={{ padding: 0 }}>
      <PageSection hasBodyWrapper={false} style={{ height: 'calc(100vh - 110px)', padding: 0 }}>
        <Chat preSelectedAgentId={search.agentId} />
      </PageSection>
    </Page>
  );
}
