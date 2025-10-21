import { Alert, Button, Flex, FlexItem, Spinner, Title } from '@patternfly/react-core';
import { SyncIcon } from '@patternfly/react-icons';
import { useModels } from '@/hooks/useModels';
import React, { useState } from 'react';
import { NewModelCard } from '@/components/NewModelCard';
import { ModelCard } from '@/components/ModelCard';
import { useQueryClient } from '@tanstack/react-query';

export function ModelList() {
  const queryClient = useQueryClient();
  const [lastFetchTime, setLastFetchTime] = useState<string>('');

  // Use custom models hook
  const {
    models,
    embeddingModels,
    isLoadingModels,
    isLoadingEmbeddingModels,
    modelsError,
    embeddingModelsError,
  } = useModels();

  // Get dataUpdatedAt from the underlying query for timestamp tracking
  const { dataUpdatedAt } = queryClient.getQueryState(['models']) || {};

  // Update timestamp when data is fetched
  React.useEffect(() => {
    if (dataUpdatedAt) {
      setLastFetchTime(new Date(dataUpdatedAt).toLocaleString());
    }
  }, [dataUpdatedAt]);

  const handleRefresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['models'] });
    void queryClient.invalidateQueries({ queryKey: ['embeddingModels'] });
  };

  const isLoading = isLoadingModels || isLoadingEmbeddingModels;
  const error = modelsError || embeddingModelsError;
  const allModels = [...(models || []), ...(embeddingModels || [])];

  return (
    <div>
      {/* Header with title, refresh button, and timestamp */}
      <Flex
        justifyContent={{ default: 'justifyContentSpaceBetween' }}
        alignItems={{ default: 'alignItemsCenter' }}
        className="pf-v6-u-mb-md"
      >
        <FlexItem>
          <Title headingLevel="h2">Models</Title>
        </FlexItem>
        <FlexItem>
          <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
            {lastFetchTime && (
              <FlexItem>
                <span className="pf-v6-u-text-color-subtle pf-v6-u-font-size-sm">
                  Last updated: {lastFetchTime}
                </span>
              </FlexItem>
            )}
            <FlexItem>
              <Button
                variant="plain"
                icon={<SyncIcon />}
                onClick={handleRefresh}
                isLoading={isLoading}
                aria-label="Refresh models"
              >
                Refresh
              </Button>
            </FlexItem>
          </Flex>
        </FlexItem>
      </Flex>

      {/* Content */}
      {isLoading && <Spinner aria-label="Loading models" />}
      {error && (
        <Alert variant="danger" title="Error loading models">
          {error.message}
        </Alert>
      )}
      <Flex direction={{ default: 'column' }}>
        <FlexItem>
          <NewModelCard />
        </FlexItem>
        {!isLoading &&
          !error &&
          allModels &&
          allModels.length > 0 &&
          allModels.map((model) => <ModelCard key={model.model_id} model={model} />)}
        {!isLoading && !error && allModels && allModels.length === 0 && (
          <p>No models registered yet.</p>
        )}
      </Flex>
    </div>
  );
}
