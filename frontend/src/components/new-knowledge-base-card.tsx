import { KnowledgeBase } from '@/types';
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
import { KnowledgeBaseForm } from './knowledge-base-form';
import { useModels, useKnowledgeBases } from '@/hooks';

export function NewKnowledgeBaseCard() {
  const [isOpen, setIsOpen] = useState(false);

  // Use custom hooks
  const {
    embeddingModels,
    isLoadingEmbeddingModels,
    embeddingModelsError,
    providers,
    isLoadingProviders,
    providersError,
  } = useModels();
  const { createKnowledgeBase, isCreating, createError } = useKnowledgeBases();

  const handleCreateKb = (values: KnowledgeBase) => {
    // Strip out fields that shouldn't be sent to the API
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { created_at, updated_at, ...createPayload } = values;
    void (async () => {
      try {
        await createKnowledgeBase(createPayload);
        setIsOpen(false);
        console.log('Knowledge base created successfully');
      } catch (error) {
        console.error('Error creating knowledge base:', error);
      }
    })();
  };

  return (
    <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
      <FlexItem>
        <Card isExpanded={isOpen} isClickable={!isOpen}>
          <CardHeader
            selectableActions={{
              onClickAction: () => setIsOpen(!isOpen),
              selectableActionAriaLabelledby: 'clickable-kb-card-title-1',
            }}
          >
            <CardTitle>
              {!isOpen ? (
                <Flex>
                  <FlexItem>
                    <PlusIcon />
                  </FlexItem>
                  <FlexItem>
                    <Title headingLevel="h3">New Knowledge Base</Title>
                  </FlexItem>
                </Flex>
              ) : (
                <Title headingLevel="h3">New Knowledge Base</Title>
              )}
            </CardTitle>
          </CardHeader>
          <CardExpandableContent>
            <CardBody>
              <Flex direction={{ default: 'column' }} gap={{ default: 'gapLg' }}>
                <FlexItem>
                  <KnowledgeBaseForm
                    embeddingModelProps={{
                      models: embeddingModels ?? [],
                      isLoadingModels: isLoadingEmbeddingModels,
                      modelsError: embeddingModelsError,
                    }}
                    providersProps={{
                      providers: providers ?? [],
                      isLoadingProviders,
                      providersError,
                    }}
                    isSubmitting={isCreating}
                    onSubmit={handleCreateKb}
                    onCancel={() => setIsOpen(false)}
                    error={createError}
                  />
                </FlexItem>
                {createError && (
                  <FlexItem>
                    <Alert
                      variant="danger"
                      title="Failed to create knowledge base"
                      className="pf-v6-u-mt-md"
                    >
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
