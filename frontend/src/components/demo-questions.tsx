import React from 'react';
import { Flex, FlexItem, Button } from '@patternfly/react-core';
import { templateService } from '@/services/templates';
import { personaStorage } from '@/services/persona-storage';

interface DemoQuestionsProps {
  agentId: string;
  agentName?: string;
  onQuestionClick: (question: string) => void;
  maxQuestions?: number;
}

export function DemoQuestions({
  agentId,
  agentName,
  onQuestionClick,
  maxQuestions = 4,
}: DemoQuestionsProps) {
  const [demoQuestions, setDemoQuestions] = React.useState<string[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    const loadDemoQuestions = async () => {
      try {
        setIsLoading(true);
        
        // First, try to get the persona from storage (for deployed agents)
        const persona = personaStorage.getPersona(agentId);
        let foundQuestions: string[] = [];
        
        if (persona) {
          // Agent has a persona assigned, get questions from templates
          const templates = await templateService.getTemplates();
          
          for (const template of templates) {
            if (template.personas && template.personas[persona]) {
              const personaData = template.personas[persona];
              
              // First try to find agent-specific questions
              if (agentName) {
                const agent = personaData.agents.find(a => a.name === agentName);
                if (agent && agent.demo_questions) {
                  foundQuestions = agent.demo_questions;
                  break;
                }
              }
              
              // Fall back to persona-level questions
              if (foundQuestions.length === 0 && personaData.demo_questions) {
                foundQuestions = personaData.demo_questions;
                break;
              }
            }
          }
        } else if (agentName) {
          // No persona assigned, try to find by agent name in templates
          const templates = await templateService.getTemplates();
          
          for (const template of templates) {
            if (template.personas) {
              // Look through personas to find the agent by name
              for (const [personaKey, persona] of Object.entries(template.personas)) {
                const agent = persona.agents.find(a => a.name === agentName);
                if (agent) {
                  // First try agent-specific questions
                  if (agent.demo_questions) {
                    foundQuestions = agent.demo_questions;
                    break;
                  }
                  // Fall back to persona-level questions
                  else if (persona.demo_questions) {
                    foundQuestions = persona.demo_questions;
                    break;
                  }
                }
              }
            }
            
            if (foundQuestions.length > 0) break;
          }
        }
        
        setDemoQuestions(foundQuestions);
      } catch (error) {
        console.error('Failed to load demo questions:', error);
        setDemoQuestions([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadDemoQuestions();
  }, [agentId, agentName]);

  if (isLoading) {
    return null;
  }
  
  if (!demoQuestions || demoQuestions.length === 0) {
    return null;
  }

  const questionsToShow = demoQuestions.slice(0, maxQuestions);

  return (
    <div className="demo-questions" style={{ marginBottom: '1rem' }}>
      <Flex direction={{ default: 'column' }} gap={{ default: 'gapSm' }}>
        {questionsToShow.map((question, index) => (
          <FlexItem key={index}>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onQuestionClick(question)}
              className="demo-question-card"
              style={{
                whiteSpace: 'normal',
                height: 'auto',
                padding: '12px 16px',
                fontSize: '14px',
                borderRadius: '20px', // More rounded corners
                border: '1px solid #94a3b8', // Light grey/blue border
                backgroundColor: 'transparent', // Transparent background
                width: '100%',
                textAlign: 'left',
                display: 'block',
                color: 'white', // White text
                transition: 'all 0.2s ease',
                boxShadow: 'none' // No shadow
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(148, 163, 184, 0.1)'; // Very subtle background on hover
                e.currentTarget.style.borderColor = '#cbd5e1'; // Slightly lighter border on hover
                e.currentTarget.style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent';
                e.currentTarget.style.borderColor = '#94a3b8';
                e.currentTarget.style.transform = 'translateY(0)';
              }}
            >
              {question}
            </Button>
          </FlexItem>
        ))}
      </Flex>
    </div>
  );
} 