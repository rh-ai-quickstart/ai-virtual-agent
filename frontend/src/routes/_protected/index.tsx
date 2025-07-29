import { Chat } from '@/components/chat';
import { Page, PageSection } from '@patternfly/react-core';
import { createFileRoute } from '@tanstack/react-router';
import { Masthead } from '../../components/masthead';

export const Route = createFileRoute('/_protected/')({
  component: ChatPage,
});

const pageId = 'primary-app-container';

function ChatPage() {
  return (
    <Page mainContainerId={pageId} masthead={<Masthead />}>
      <PageSection hasBodyWrapper={false}>
        <Chat />
      </PageSection>
    </Page>
  );
}
