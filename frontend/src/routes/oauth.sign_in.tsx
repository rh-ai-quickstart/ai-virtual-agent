import { createFileRoute } from '@tanstack/react-router';
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Page,
  PageSection,
  Title,
} from '@patternfly/react-core';

export const Route = createFileRoute('/oauth/sign_in')({
  component: OAuthSignIn,
  validateSearch: (search: Record<string, unknown>) => ({
    redirect: (search.redirect as string) || '/',
  }),
});

function OAuthSignIn() {
  const enableLocalDevMode = () => {
    alert(
      'To enable Local Dev Mode:\n\n1. Stop your backend server\n2. Run: export LOCAL_DEV_ENV_MODE=true\n3. Restart your backend server\n4. Refresh this page'
    );
  };

  return (
    <Page>
      <PageSection>
        <Title headingLevel="h1" size="2xl">
          🔒 Authentication Required
        </Title>
        <p>The AI Virtual Agent requires authentication to access this application.</p>

        <Card>
          <CardHeader>
            <CardTitle>
              <Title headingLevel="h3" size="lg">
                🚀 Local Development (Recommended)
              </Title>
            </CardTitle>
          </CardHeader>
          <CardBody>
            <p>Skip authentication for local development and testing.</p>
            <p>
              <code>export LOCAL_DEV_ENV_MODE=true</code>
            </p>
            <Button variant="primary" onClick={enableLocalDevMode}>
              Show Setup Instructions
            </Button>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              <Title headingLevel="h3" size="lg">
                🔐 Production OAuth Setup
              </Title>
            </CardTitle>
          </CardHeader>
          <CardBody>
            <p>Configure OAuth provider for production deployment.</p>
            <ul>
              <li>Set up OAuth proxy (oauth2-proxy, etc.)</li>
              <li>Configure OAuth provider (GitHub, Google, etc.)</li>
              <li>Set OAuth headers: X-Forwarded-User, X-Forwarded-Email</li>
              <li>Ensure LOCAL_DEV_ENV_MODE=false</li>
            </ul>
            <Button
              variant="secondary"
              component="a"
              href="https://github.com/rh-ai-quickstart/ai-virtual-agent/blob/main/README.md"
              target="_blank"
              rel="noopener noreferrer"
            >
              View Documentation
            </Button>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              <Title headingLevel="h3" size="lg">
                Next Steps
              </Title>
            </CardTitle>
          </CardHeader>
          <CardBody>
            <p>
              After configuring your authentication method above, refresh this page to continue to
              the application.
            </p>
          </CardBody>
        </Card>

        <p>
          <strong>Need help?</strong> Check the{' '}
          <a
            href="https://github.com/rh-ai-quickstart/ai-virtual-agent"
            target="_blank"
            rel="noopener noreferrer"
          >
            project documentation
          </a>{' '}
          or contact your system administrator.
        </p>
      </PageSection>
    </Page>
  );
}
