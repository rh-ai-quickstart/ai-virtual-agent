import { AgentList } from '@/components/agent-list';
import { NewAgentCard } from '@/components/new-agent-card';
import { createAgent } from '@/services/agents';
import { personaStorage } from '@/services/persona-storage';
import { ToolAssociationInfo } from '@/types';
import { 
  Flex, 
  FlexItem, 
  PageSection, 
  Title, 
  Button, 
  Alert,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Card,
  CardBody,
  Label
} from '@patternfly/react-core';
import { MagicIcon, RocketIcon } from '@patternfly/react-icons';
import { createFileRoute } from '@tanstack/react-router';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

// Type def for fetching agents
export interface Agent {
  id: string;
  name: string;
  model_name: string;
  prompt: string;
  persona?: string; // Added persona field
  tools: ToolAssociationInfo[];
  knowledge_base_ids: string[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

// Type def for creating agents
export interface NewAgent {
  name: string;
  model_name: string;
  prompt: string;
  persona?: string; // Added persona field
  tools: ToolAssociationInfo[];
  knowledge_base_ids: string[];
}

// NEW: Banking demo agents configuration
const BANKING_DEMO_AGENTS = [
  {
    name: 'Compliance Policy Assistant',
    persona: 'compliance_officer',
    prompt: 'You are a Compliance Policy Agent for a US bank. You help ensure adherence to US banking regulations including BSA/AML, OFAC, CFPB, OCC, and FDIC guidance. You provide accurate information about compliance procedures, reporting requirements, and regulatory updates.',
    model_name: 'meta-llama/Llama-3.1-8B-Instruct',
    tools: [{ toolgroup_id: 'builtin::websearch' }],
    knowledge_base_ids: []
  },
  {
    name: 'Lending Policy Assistant',
    persona: 'relationship_manager',
    prompt: 'You are a Lending Policy Assistant for relationship managers and loan officers. You help with credit assessment, lending requests, documentation requirements, and regulatory compliance for loans. You know FHA guidelines, conventional loan requirements, and small business lending procedures.',
    model_name: 'meta-llama/Llama-3.1-8B-Instruct',
    tools: [{ toolgroup_id: 'builtin::websearch' }],
    knowledge_base_ids: []
  },
  {
    name: 'Customer Service Assistant',
    persona: 'branch_teller',
    prompt: 'You are a Customer Service Assistant for branch tellers and customer service representatives. You help with day-to-day customer queries about product fees, account policies, transaction processing, and regulatory timelines. You provide accurate information about bank products and services.',
    model_name: 'meta-llama/Llama-3.1-8B-Instruct',
    tools: [{ toolgroup_id: 'builtin::websearch' }],
    knowledge_base_ids: []
  },
  {
    name: 'Fraud Detection Assistant',
    persona: 'fraud_analyst',
    prompt: 'You are a Fraud Detection Assistant for fraud analysts and AML specialists. You help review alerts for suspicious transactions, investigate AML/BSA/OFAC red flags, and ensure reporting compliance. You provide guidance on escalation procedures and regulatory requirements.',
    model_name: 'meta-llama/Llama-3.1-8B-Instruct',
    tools: [{ toolgroup_id: 'builtin::websearch' }],
    knowledge_base_ids: []
  },
  {
    name: 'Training & Market Intelligence Assistant',
    persona: 'training_lead',
    prompt: 'You are a Training & Market Intelligence Assistant for training leads and analysts. You help keep staff current on new US regulations, industry certifications, and market developments. You provide information about regulatory updates, certification requirements, and industry best practices.',
    model_name: 'meta-llama/Llama-3.1-8B-Instruct',
    tools: [{ toolgroup_id: 'builtin::websearch' }],
    knowledge_base_ids: []
  },
  {
    name: 'IT Support Assistant',
    persona: 'it_support',
    prompt: 'You are an IT Support Assistant for banking operations. You help support banking employees with system/process issues and ensure adherence to IT policies. You provide guidance on password resets, system access, security protocols, and technical procedures.',
    model_name: 'meta-llama/Llama-3.1-8B-Instruct',
    tools: [{ toolgroup_id: 'builtin::websearch' }],
    knowledge_base_ids: []
  }
];

export const Route = createFileRoute('/config/agents')({
  component: Agents,
});

export function Agents() {
  const [showDemoModal, setShowDemoModal] = useState(false);
  const [demoProgress, setDemoProgress] = useState<string[]>([]);
  const queryClient = useQueryClient();

  // Mutation for creating demo agents
  const createDemoMutation = useMutation({
    mutationFn: async () => {
      const results = [];
      setDemoProgress([]);
      
      for (const demoAgent of BANKING_DEMO_AGENTS) {
        try {
          // Extract persona from the demo agent
          const { persona, ...agentPayload } = demoAgent;
          
          // Create the agent
          const createdAgent = await createAgent(agentPayload as NewAgent);
          
          // Save persona mapping if persona exists
          if (persona && createdAgent.id) {
            personaStorage.setPersona(createdAgent.id, persona);
          }
          
          results.push(createdAgent);
          setDemoProgress(prev => [...prev, `✅ Created ${demoAgent.name}`]);
          
          // Small delay to show progress
          await new Promise(resolve => setTimeout(resolve, 500));
        } catch (error) {
          console.error(`Failed to create ${demoAgent.name}:`, error);
          setDemoProgress(prev => [...prev, `❌ Failed to create ${demoAgent.name}`]);
        }
      }
      
      return results;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['agents'] });
              setDemoProgress(prev => [...prev, '🏦 Banking templates deployed successfully!']);
      setTimeout(() => {
        setShowDemoModal(false);
        setDemoProgress([]);
      }, 2000);
    },
    onError: (error) => {
      console.error('Demo creation failed:', error);
      setDemoProgress(prev => [...prev, '❌ Demo creation failed']);
    }
  });

  const handleCreateDemo = () => {
    setShowDemoModal(true);
    createDemoMutation.mutate();
  };

  return (
    <PageSection>
      <Flex direction={{ default: 'column' }} gap={{ default: 'gapMd' }}>
        <FlexItem>
          <Flex justifyContent={{ default: 'justifyContentSpaceBetween' }} alignItems={{ default: 'alignItemsCenter' }}>
            <FlexItem>
              <Title headingLevel="h1">Agents</Title>
            </FlexItem>
            {/* NEW: Banking Templates Button */}
            <FlexItem>
              <Button
                variant="tertiary"
                icon={<RocketIcon />}
                onClick={handleCreateDemo}
                isDisabled={createDemoMutation.isPending}
              >
                Use Banking Templates
              </Button>
            </FlexItem>
          </Flex>
        </FlexItem>
        
        {/* NEW: Banking Templates Card */}
        <FlexItem>
          <Card>
            <CardBody>
              <Flex alignItems={{ default: 'alignItemsCenter' }} gap={{ default: 'gapSm' }}>
                <FlexItem>
                  <MagicIcon />
                </FlexItem>
                <FlexItem flex={{ default: 'flex_1' }}>
                  <strong>Banking Templates:</strong> Get started quickly with pre-configured banking agent templates. Choose from specialized roles designed for financial institutions.
                </FlexItem>
                <FlexItem>
                  <Flex gap={{ default: 'gapXs' }}>
                    <Label color="red" variant="outline">Compliance</Label>
                    <Label color="green" variant="outline">Lending</Label>
                    <Label color="blue" variant="outline">Customer Service</Label>
                    <Label color="orange" variant="outline">Fraud</Label>
                    <Label color="purple" variant="outline">Training</Label>
                    <Label color="grey" variant="outline">IT Support</Label>
                  </Flex>
                </FlexItem>
              </Flex>
            </CardBody>
          </Card>
        </FlexItem>

        <FlexItem>
          <NewAgentCard />
        </FlexItem>
        <FlexItem>
          <AgentList />
        </FlexItem>
      </Flex>

      {/* NEW: Banking Templates Modal */}
      <Modal
        variant="small"
        title="Banking Templates"
        isOpen={showDemoModal}
        onClose={() => !createDemoMutation.isPending && setShowDemoModal(false)}
        hasNoBodyWrapper
      >
        <ModalHeader title="Setting Up Banking Agent Templates" />
        <ModalBody>
          <Flex direction={{ default: 'column' }} gap={{ default: 'gapSm' }}>
            <FlexItem>
              <p>Creating specialized banking agents from templates...</p>
            </FlexItem>
            {demoProgress.map((progress, index) => (
              <FlexItem key={index}>
                <div style={{ fontFamily: 'monospace', fontSize: '14px' }}>
                  {progress}
                </div>
              </FlexItem>
            ))}
            {createDemoMutation.isPending && demoProgress.length === 0 && (
              <FlexItem>
                <div>🏦 Deploying banking templates...</div>
              </FlexItem>
            )}
          </Flex>
        </ModalBody>
        <ModalFooter>
          <Button
            variant="link"
            onClick={() => setShowDemoModal(false)}
            isDisabled={createDemoMutation.isPending}
          >
            {createDemoMutation.isPending ? 'Creating...' : 'Close'}
          </Button>
        </ModalFooter>
      </Modal>
    </PageSection>
  );
}