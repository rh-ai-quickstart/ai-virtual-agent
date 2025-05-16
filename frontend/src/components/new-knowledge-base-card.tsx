import {
  AGENTS_API_ENDPOINT,
  //   KNOWLEDGE_BASES_API_ENDPOINT,
  //   TOOLS_API_ENDPOINT,
} from '@/config/api';
import { KnowledgeBase, NewKnowledgeBase } from '@/routes/config/knowledge-bases';
// import { fetchModels } from '@/services/models';
// import { Model, Tool } from '@/types';
import {
  Alert,
  Card,
  CardBody,
  CardExpandableContent,
  CardHeader,
  CardTitle,
  Flex,
  FlexItem,
  Title,
} from '@patternfly/react-core';
import { PlusIcon } from '@patternfly/react-icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { KnowledgeBaseForm } from './knowledge-base-form';

// const fetchKnowledgeBases = async (): Promise<KnowledgeBase[]> => {
//   const response = await fetch(KNOWLEDGE_BASES_API_ENDPOINT);
//   if (!response.ok) {
//     throw new Error('Network response was not ok');
//   }
//   return response.json();
// };
// const fetchTools = async (): Promise<Tool[]> => {
//   const response = await fetch(TOOLS_API_ENDPOINT);
//   if (!response.ok) {
//     throw new Error('Network response was not ok');
//   }
//   return response.json();
// };

const createKnowledgeBase = async (newKnowledgeBase: NewKnowledgeBase): Promise<KnowledgeBase> => {
  const response = await fetch(AGENTS_API_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(newKnowledgeBase),
  });
  if (!response.ok) {
    throw new Error('Network response was not ok');
  }
  return response.json();
};

export function NewKnowledgeBaseCard() {
  const [isOpen, setIsOpen] = useState(false);
  // Or whatever name fits your routing setup e.g. ConfigKnowledgeBases
  const queryClient = useQueryClient();

  //   // Query for AI Models
  //   const {
  //     data: models,
  //     isLoading: isLoadingModels,
  //     error: modelsError,
  //   } = useQuery<Model[], Error>({
  //     queryKey: ['models'],
  //     queryFn: fetchModels,
  //   });
  //   // Query for Knowledge bases
  //   const {
  //     data: knowledgeBases,
  //     isLoading: isLoadingKnowledgeBases,
  //     error: knowledgeBasesError,
  //   } = useQuery<KnowledgeBase[], Error>({
  //     queryKey: ['knowledgeBases'],
  //     queryFn: fetchKnowledgeBases,
  //   });
  //   // Query for tools
  //   const {
  //     data: tools,
  //     isLoading: isLoadingTools,
  //     error: toolsError,
  //   } = useQuery<Tool[], Error>({
  //     queryKey: ['tools'],
  //     queryFn: fetchTools,
  //   });

  // Mutation for creating an Knowledge Base
  const knowledgebaseMutation = useMutation<KnowledgeBase, Error, NewKnowledgeBase>({
    mutationFn: createKnowledgeBase,
    onSuccess: (newKnowledgeBaseData) => {
      queryClient.invalidateQueries({ queryKey: ['knowledgebase'] });
      console.log('KnowledgeBase created successfully:', newKnowledgeBaseData);
    },
    onError: (error) => {
      console.error('Error creating knowledgebase:', error);
      // Show an error message
    },
  });

  const handleCreateKnowledgeBase = (values: NewKnowledgeBase) => {
    knowledgebaseMutation.mutate(values);
  };

  return (
    <Card isExpanded={isOpen} isClickable={!isOpen}>
      <CardHeader
        selectableActions={{
          // eslint-disable-next-line no-console
          onClickAction: () => setIsOpen(!isOpen),
          selectableActionAriaLabelledby: 'clickable-card-example-title-1',
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
            <Title headingLevel="h1">New Knowledge Base</Title>
          )}
        </CardTitle>
      </CardHeader>
      <CardExpandableContent className="pf-v5-u-mb-lg">
        <CardBody>
          <KnowledgeBaseForm
            onSubmit={handleCreateKnowledgeBase}
            isSubmitting={knowledgebaseMutation.isPending}
            onCancel={() => setIsOpen(false)}
          />
          {knowledgebaseMutation.isError && (
            <Alert
              variant="danger"
              title="Failed to create knowledge base"
              className="pf-v5-u-mt-md"
            >
              {knowledgebaseMutation.error?.message || 'An unexpected error occurred.'}
            </Alert>
          )}

          {knowledgebaseMutation.isSuccess && (
            <Alert
              variant="success"
              title="Knowledge Base created successfully!"
              className="pf-v5-u-mt-md"
            />
          )}
        </CardBody>
      </CardExpandableContent>
    </Card>
  );
}
