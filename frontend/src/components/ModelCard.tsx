import {
  Card,
  CardHeader,
  CardTitle,
  CardBody,
  CardExpandableContent,
  Title,
  Flex,
  FlexItem,
  Label,
  DescriptionList,
  DescriptionListGroup,
  DescriptionListTerm,
  DescriptionListDescription,
} from '@patternfly/react-core';
import { useState } from 'react';
import { Model } from '@/types';

interface ModelCardProps {
  model: Model;
}

export function ModelCard({ model }: ModelCardProps) {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  const onExpand = () => setIsExpanded(!isExpanded);

  return (
    <Card isExpanded={isExpanded} isClickable>
      <CardHeader
        selectableActions={{
          onClickAction: onExpand,
          selectableActionAriaLabelledby: `model-${model.model_id}`,
        }}
      >
        <CardTitle>
          <Flex>
            <FlexItem>
              <Title headingLevel="h3" id={`model-${model.model_id}`}>
                {model.model_id}
              </Title>
            </FlexItem>
            <FlexItem>
              <Label
                color={
                  model.model_type === 'llm'
                    ? 'green'
                    : model.model_type === 'embedding'
                      ? 'blue'
                      : 'grey'
                }
              >
                {model.model_type}
              </Label>
            </FlexItem>
          </Flex>
        </CardTitle>
      </CardHeader>
      <CardExpandableContent>
        <CardBody>
          <DescriptionList isHorizontal>
            <DescriptionListGroup>
              <DescriptionListTerm>Model ID</DescriptionListTerm>
              <DescriptionListDescription>{model.model_id}</DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup>
              <DescriptionListTerm>Model Type</DescriptionListTerm>
              <DescriptionListDescription>{model.model_type}</DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup>
              <DescriptionListTerm>Provider ID</DescriptionListTerm>
              <DescriptionListDescription>{model.provider_id}</DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup>
              <DescriptionListTerm>Provider Type</DescriptionListTerm>
              <DescriptionListDescription>{model.provider_type}</DescriptionListDescription>
            </DescriptionListGroup>
            <DescriptionListGroup>
              <DescriptionListTerm>Provider Config</DescriptionListTerm>
              <DescriptionListDescription>
                <pre style={{ margin: 0, fontSize: '12px' }}>
                  {JSON.stringify(model.provider_config, null, 2)}
                </pre>
              </DescriptionListDescription>
            </DescriptionListGroup>
          </DescriptionList>
        </CardBody>
      </CardExpandableContent>
    </Card>
  );
}
