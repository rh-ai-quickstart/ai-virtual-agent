import { Agent, NewAgent } from '@/routes/config/agents';
import { createAgent } from '@/services/agents';
import { fetchLlamaStackKnowledgeBases } from '@/services/knowledge-bases';
import { fetchModels } from '@/services/models';
import { fetchTools } from '@/services/tools';
import { LSKnowledgeBase, Model, ToolGroup } from '@/types';
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
import { AgentForm } from './agent-form';

export function NewAgentCard() {
  const [isOpen, setIsOpen] = useState(false);
  // Or whatever name fits your routing setup e.g. ConfigAgents
  const queryClient = useQueryClient();

  // Query for AI Models
  const {
    data: models,
    isLoading: isLoadingModels,
    error: modelsError,
  } = useQuery<Model[], Error>({
    queryKey: ['models'],
    queryFn: fetchModels,
  });
  // Query for Knowledge bases
  const {
    data: knowledgeBases,
    isLoading: isLoadingKnowledgeBases,
    error: knowledgeBasesError,
  } = useQuery<LSKnowledgeBase[], Error>({
    queryKey: ['knowledgeBases'],
    queryFn: fetchLlamaStackKnowledgeBases,
  });
  // Query for tools
  const {
    data: tools,
    isLoading: isLoadingTools,
    error: toolsError,
  } = useQuery<ToolGroup[], Error>({
    queryKey: ['tools'],
    queryFn: fetchTools,
  });

  // Mutation for creating an Agent
  const agentMutation = useMutation<Agent, Error, NewAgent>({
    mutationFn: createAgent,
    onSuccess: async (newAgentData) => {
      await queryClient.invalidateQueries({ queryKey: ['agents'] });
      setIsOpen(false);
      console.log('Agent created successfully:', newAgentData);
    },
    onError: (error) => {
      console.error('Error creating agent:', error);
      // Show an error message
    },
  });

  const handleCreateAgent = (values: NewAgent) => {
    agentMutation.mutate(values);
  };

  return (
    <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
      {agentMutation.isSuccess && (
        <FlexItem>
          <Alert
            timeout={5000}
            variant="success"
            title="Agent created successfully!"
            className="pf-v6-u-mb-sm"
          />
        </FlexItem>
      )}
      <FlexItem>
        <Card isExpanded={isOpen} isClickable={!isOpen}>
          <CardHeader
            selectableActions={{
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
                    <Title headingLevel="h3">New Agent</Title>
                  </FlexItem>
                </Flex>
              ) : (
                <Title headingLevel="h3">New Agent</Title>
              )}
            </CardTitle>
          </CardHeader>
          <CardExpandableContent>
            <CardBody>
              <Flex direction={{ default: 'column' }} gap={{ default: 'gapLg' }}>
                <FlexItem>
                  <AgentForm
                    modelsProps={{
                      models: models || [],
                      isLoadingModels,
                      modelsError,
                    }}
                    knowledgeBasesProps={{
                      knowledgeBases: knowledgeBases || [],
                      isLoadingKnowledgeBases,
                      knowledgeBasesError,
                    }}
                    toolsProps={{
                      tools: tools || [],
                      isLoadingTools,
                      toolsError,
                    }}
                    onSubmit={handleCreateAgent}
                    isSubmitting={agentMutation.isPending}
                    onCancel={() => setIsOpen(false)}
                  />
                </FlexItem>
                {agentMutation.isError && (
                  <FlexItem>
                    <Alert
                      variant="danger"
                      title="Failed to create agent"
                      className="pf-v6-u-mt-md"
                    >
                      {agentMutation.error?.message || 'An unexpected error occurred.'}
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
