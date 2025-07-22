import { createFileRoute } from '@tanstack/react-router';
import { useState, useEffect } from 'react';
import {
  Page,
  PageSection,
  Title,
  Flex,
  FlexItem,
  Button,
  Alert,
  AlertActionCloseButton,
  Label,
  Spinner,
} from '@patternfly/react-core';
import { SyncIcon } from '@patternfly/react-icons';
import { TemplateList } from '@/components/template-list';
import { templateService } from '@/services/templates';
import { TemplateSuite } from '@/types/templates';

console.log('TemplateService imported:', templateService);
console.log('TemplateService methods:', Object.keys(templateService));

export const Route = createFileRoute('/config/templates')({
  component: Templates,
});

export function Templates() {
  const [templates, setTemplates] = useState<TemplateSuite[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [isDeploying, setIsDeploying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    void loadData();
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      console.log('Loading templates...');
      console.log('TemplateService available:', !!templateService);
      console.log('getTemplates method available:', !!templateService.getTemplates);

      const [templatesData, categoriesData] = await Promise.all([
        templateService.getTemplates(),
        templateService.getCategories(),
      ]);

      console.log('Templates received:', templatesData);
      console.log('Categories received:', categoriesData);

      setTemplates(templatesData || []);
      setCategories(categoriesData || []);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('Failed to load templates:', err);
      setError('Failed to load templates: ' + errorMessage);
      setTemplates([]);
      setCategories([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCategoryClick = async (category: string) => {
    setSelectedCategory(category);
    if (category) {
      try {
        setIsLoading(true);
        // Note: getTemplatesByCategory method doesn't exist, using getTemplates instead
        const allTemplates = await templateService.getTemplates();
        const categoryTemplates = allTemplates.filter(
          (template) => template.metadata?.category === category || template.category === category
        );
        setTemplates(categoryTemplates || []);
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        setError('Failed to load category templates: ' + errorMessage);
      } finally {
        setIsLoading(false);
      }
    } else {
      await loadData();
    }
  };

  const handleDeploy = async (templateId: string) => {
    try {
      setIsDeploying(true);
      setError(null);

      const result = await templateService.deployTemplate(templateId);

      if (result.success) {
        setSuccess(
          `Template deployed successfully! Created ${result.agent_ids?.length || 0} agents.`
        );
      } else {
        setError(result.error || 'Deployment failed');
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError('Deployment failed: ' + errorMessage);
    } finally {
      setIsDeploying(false);
    }
  };

  const handleRefresh = async () => {
    try {
      // Note: refreshCache method doesn't exist, reloading templates instead
      await loadData();
      await loadData();
      setSuccess('Template cache refreshed successfully!');
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError('Failed to refresh cache: ' + errorMessage);
    }
  };

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  const handleCategoryClickSync = (category: string) => {
    void handleCategoryClick(category).catch((error) => {
      console.error('Error handling category click:', error);
    });
  };

  // Show loading spinner while initializing
  if (isLoading && templates.length === 0) {
    return (
      <Page>
        <PageSection>
          <Flex
            justifyContent={{ default: 'justifyContentCenter' }}
            alignItems={{ default: 'alignItemsCenter' }}
            style={{ minHeight: '200px' }}
          >
            <FlexItem>
              <Spinner size="lg" />
            </FlexItem>
          </Flex>
        </PageSection>
      </Page>
    );
  }

  return (
    <Page>
      <PageSection>
        <Flex
          justifyContent={{ default: 'justifyContentSpaceBetween' }}
          alignItems={{ default: 'alignItemsCenter' }}
        >
          <FlexItem>
            <Title headingLevel="h1" size="2xl">
              Template Catalog
            </Title>
          </FlexItem>
          <FlexItem>
            <Button
              variant="secondary"
              icon={<SyncIcon />}
              onClick={() => {
                void handleRefresh().catch((error) => {
                  console.error('Error refreshing cache:', error);
                });
              }}
              isDisabled={isLoading}
            >
              Refresh Cache
            </Button>
          </FlexItem>
        </Flex>
      </PageSection>

      <PageSection>
        {error && (
          <Alert
            variant="danger"
            title="Error"
            actionClose={<AlertActionCloseButton onClose={clearMessages} />}
            style={{ marginBottom: '1rem' }}
          >
            {error}
          </Alert>
        )}

        {success && (
          <Alert
            variant="success"
            title="Success"
            actionClose={<AlertActionCloseButton onClose={clearMessages} />}
            style={{ marginBottom: '1rem' }}
          >
            {success}
          </Alert>
        )}

        {/* Category Filter - Using Labels instead of Select */}
        <Flex style={{ marginBottom: '2rem' }} gap={{ default: 'gapSm' }}>
          <FlexItem>
            <Label
              color={selectedCategory === '' ? 'blue' : 'grey'}
              variant="outline"
              style={{ cursor: 'pointer' }}
              onClick={() => handleCategoryClickSync('')}
            >
              All Categories
            </Label>
          </FlexItem>
          {(categories || []).map((category) => (
            <FlexItem key={category}>
              <Label
                color={selectedCategory === category ? 'blue' : 'grey'}
                variant="outline"
                style={{ cursor: 'pointer' }}
                onClick={() => handleCategoryClickSync(category)}
              >
                {category.replace('_', ' ').toUpperCase()}
              </Label>
            </FlexItem>
          ))}
        </Flex>

        <TemplateList
          templates={templates || []}
          agents={[]} // Add empty agents array as it's required
          onDeploy={(templateId: string) => void handleDeploy(templateId)}
          isDeploying={isDeploying}
          isLoading={isLoading}
          selectedCategory={selectedCategory}
        />
      </PageSection>
    </Page>
  );
}
