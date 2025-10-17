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
import { ModelForm } from './ModelForm';
import { useModels } from '@/hooks/useModels';
import { RegisterModelRequest } from '@/services/models';

export function NewModelCard() {
  const [isOpen, setIsOpen] = useState(false);

  // Use custom hook
  const { registerModel, isRegisteringModel, registerModelError } = useModels();

  const handleSubmit = (values: RegisterModelRequest) => {
    registerModel(values, {
      onSuccess: () => {
        console.log('Model registered successfully');
        setIsOpen(false);
      },
      onError: (error) => {
        console.error('Error registering model:', error);
      },
    });
  };

  const handleCancel = () => {
    setIsOpen(false);
  };

  return (
    <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
      <FlexItem>
        <Card isExpanded={isOpen} isClickable={!isOpen}>
          <CardHeader
            selectableActions={{
              onClickAction: () => setIsOpen(!isOpen),
              selectableActionAriaLabelledby: 'clickable-model-card-title-1',
            }}
          >
            <CardTitle>
              {!isOpen ? (
                <Flex>
                  <FlexItem>
                    <PlusIcon />
                  </FlexItem>
                  <FlexItem>
                    <Title headingLevel="h3">Register New Model</Title>
                  </FlexItem>
                </Flex>
              ) : (
                <Title headingLevel="h3">Register New Model</Title>
              )}
            </CardTitle>
          </CardHeader>
          <CardExpandableContent>
            <CardBody>
              <Flex direction={{ default: 'column' }} gap={{ default: 'gapLg' }}>
                <FlexItem>
                  <ModelForm
                    isSubmitting={isRegisteringModel}
                    onSubmit={handleSubmit}
                    onCancel={handleCancel}
                  />
                </FlexItem>
                {registerModelError && (
                  <FlexItem>
                    <Alert variant="danger" title="Registration Error">
                      {registerModelError.message}
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
