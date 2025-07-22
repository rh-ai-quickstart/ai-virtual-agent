import { TemplateSuite } from '@/types/templates';
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  CardExpandableContent,
  Flex,
  FlexItem,
  Label,
  Button,
  Badge,
  Divider,
} from '@patternfly/react-core';
import {
  RocketIcon,
  UsersIcon,
  ClockIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@patternfly/react-icons';
// import { useState } from 'react';

interface TemplateCardProps {
  template: TemplateSuite;
  onDeploy: (templateId: string) => void;
  isDeploying?: boolean;
}

// Category-specific styling
const CATEGORY_STYLES: Record<
  string,
  {
    color: 'red' | 'green' | 'blue' | 'orange' | 'purple' | 'grey';
    bgColor: string;
    borderColor: string;
  }
> = {
  fsi_banking: {
    color: 'blue',
    bgColor: 'var(--pf-v6-global--palette--blue-50)',
    borderColor: 'var(--pf-v6-global--palette--blue-200)',
  },
  us_banking: {
    color: 'green',
    bgColor: 'var(--pf-v6-global--palette--green-50)',
    borderColor: 'var(--pf-v6-global--palette--green-200)',
  },
  wealth_management: {
    color: 'purple',
    bgColor: 'var(--pf-v6-global--palette--purple-50)',
    borderColor: 'var(--pf-v6-global--palette--purple-200)',
  },
  insurance: {
    color: 'orange',
    bgColor: 'var(--pf-v6-global--palette--orange-50)',
    borderColor: 'var(--pf-v6-global--palette--orange-200)',
  },
};

export function TemplateCard({ template, onDeploy, isDeploying = false }: TemplateCardProps) {
  // const [expanded, setExpanded] = useState(false);

  const categoryStyle = CATEGORY_STYLES[template.category] || {
    color: 'grey' as const,
    bgColor: 'var(--pf-v6-global--palette--grey-50)',
    borderColor: 'var(--pf-v6-global--palette--grey-200)',
  };
  const successRate = (template.metadata?.success_rate as number) || 0;
  const deploymentTime = (template.metadata?.deployment_time as string) || 'Unknown';
  const agentCount = template.agents?.length || 0;

  const handleDeploy = () => {
    onDeploy(template.id);
  };

  // const toggleExpanded = () => {
  //   setExpanded(!expanded);
  // };

  return (
    <Card
      style={{
        backgroundColor: categoryStyle.bgColor,
        borderColor: categoryStyle.borderColor,
        borderWidth: '2px',
      }}
    >
      <CardHeader
        toggleButtonProps={{
          'aria-label': 'Toggle template details',
          'aria-expanded': false,
        }}
      >
        <CardTitle>
          <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
            <FlexItem>
              <RocketIcon />
            </FlexItem>
            <FlexItem flex={{ default: 'flex_1' }}>{template.name}</FlexItem>
            <FlexItem>
              <Label color={categoryStyle.color} variant="outline">
                {template.category.replace('_', ' ').toUpperCase()}
              </Label>
            </FlexItem>
          </Flex>
        </CardTitle>
      </CardHeader>

      <CardBody>
        <p style={{ margin: 0, marginBottom: '1rem' }}>{template.description}</p>

        <Flex gap={{ default: 'gapMd' }} style={{ marginTop: '1rem' }}>
          <FlexItem>
            <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapXs' }}>
              <UsersIcon />
              <small>
                {agentCount} {agentCount === 1 ? 'Agent' : 'Agents'}
              </small>
            </Flex>
          </FlexItem>

          <FlexItem>
            <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapXs' }}>
              <ClockIcon />
              <small>{deploymentTime}</small>
            </Flex>
          </FlexItem>

          <FlexItem>
            <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapXs' }}>
              {successRate >= 90 ? (
                <CheckCircleIcon style={{ color: 'var(--pf-v6-global--palette--green-500)' }} />
              ) : (
                <ExclamationTriangleIcon
                  style={{ color: 'var(--pf-v6-global--palette--orange-500)' }}
                />
              )}
              <small>{successRate}% Success Rate</small>
            </Flex>
          </FlexItem>
        </Flex>

        {(() => {
          const features = template.metadata?.features;
          if (features && Array.isArray(features)) {
            return (
              <Flex gap={{ default: 'gapXs' }} style={{ marginTop: '1rem' }}>
                {features.map((feature: string, index: number) => (
                  <FlexItem key={index}>
                    <Badge isRead>{String(feature)}</Badge>
                  </FlexItem>
                ))}
              </Flex>
            );
          }
          return null;
        })()}

        <Flex justifyContent={{ default: 'justifyContentFlexEnd' }} style={{ marginTop: '1rem' }}>
          <Button
            variant="primary"
            icon={<RocketIcon />}
            onClick={handleDeploy}
            isDisabled={isDeploying}
            isLoading={isDeploying}
          >
            {isDeploying ? 'Deploying...' : 'Deploy Template'}
          </Button>
        </Flex>
      </CardBody>

      <CardExpandableContent>
        <Divider />
        <CardBody>
          <h4 style={{ marginBottom: '1rem' }}>Included Agents</h4>
          {template.agents?.map((agent, index) => (
            <div
              key={index}
              style={{
                marginBottom: '1rem',
                padding: '0.5rem',
                backgroundColor: 'var(--pf-v6-global--BackgroundColor--100)',
                borderRadius: '4px',
              }}
            >
              <Flex
                justifyContent={{ default: 'justifyContentSpaceBetween' }}
                alignItems={{ default: 'alignItemsCenter' }}
              >
                <FlexItem flex={{ default: 'flex_1' }}>
                  <h6 style={{ margin: 0 }}>{agent.name}</h6>
                  {agent.description && (
                    <small style={{ color: 'var(--pf-v6-global--Color--200)' }}>
                      {agent.description}
                    </small>
                  )}
                </FlexItem>
                <FlexItem>
                  <Label color="blue" variant="outline">
                    {agent.model_name.split('/').pop()}
                  </Label>
                </FlexItem>
              </Flex>
            </div>
          ))}
        </CardBody>
      </CardExpandableContent>
    </Card>
  );
}
