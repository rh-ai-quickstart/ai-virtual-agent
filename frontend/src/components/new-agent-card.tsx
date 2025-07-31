import { NewAgent } from '@/types/agent';
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
import { useAgents } from '@/hooks';
import { useState } from 'react';
import { AgentForm } from './agent-form';

export function NewAgentCard() {
  const [isOpen, setIsOpen] = useState(false);

  // Use agents hook for creating agents
  const { createAgent, isCreating, createError } = useAgents();

  const handleCreateAgent = (values: NewAgent) => {
    void (async () => {
      try {
        await createAgent(values);
        setIsOpen(false);
        console.log('Agent created successfully');
      } catch (error) {
        console.error('Error creating agent:', error);
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
                    onSubmit={handleCreateAgent}
                    isSubmitting={isCreating}
                    onCancel={() => setIsOpen(false)}
                  />
                </FlexItem>
                {createError && (
                  <FlexItem>
                    <Alert
                      variant="danger"
                      title="Failed to create agent"
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
