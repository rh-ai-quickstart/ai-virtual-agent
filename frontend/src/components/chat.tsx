import React, { Fragment, useEffect, useState, useCallback } from 'react';
import { useSearch, useNavigate } from '@tanstack/react-router';
import {
  Chatbot,
  ChatbotContent,
  ChatbotConversationHistoryNav,
  ChatbotDisplayMode,
  ChatbotFooter,
  ChatbotFootnote,
  ChatbotHeader,
  ChatbotHeaderActions,
  ChatbotHeaderMain,
  ChatbotHeaderMenu,
  ChatbotHeaderSelectorDropdown,
  ChatbotHeaderTitle,
  Conversation,
  Message,
  MessageBar,
  MessageBox,
  MessageProps,
} from '@patternfly/chatbot';
import {
  DropdownItem,
  DropdownList,
  Modal,
  ModalVariant,
  Button,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Flex,
  Breadcrumb,
  BreadcrumbItem,
} from '@patternfly/react-core';
import { 
  AngleLeftIcon
} from '@patternfly/react-icons';
import { Agent } from '@/routes/config/agents';
import { fetchAgents } from '@/services/agents';
import { personaStorage } from '@/services/persona-storage';
import { useChat } from '@/hooks/useChat';
import {
  fetchChatSessions,
  createChatSession,
  deleteChatSession,
  ChatSessionSummary,
} from '@/services/chat-sessions';
import { useMutation } from '@tanstack/react-query';
import botAvatar from "../assets/img/bot-avatar.svg";
import userAvatar from "../assets/img/user-avatar.svg";
// import { templateService } from '@/services/templates';
import { DemoQuestions } from '@/components/demo-questions';
import { personaService } from '@/services/personas';

// Persona labels are now loaded from template YAML files via personaService
// This ensures no hard-coded persona configurations

// NEW: Persona icons mapping
// const PERSONA_ICONS: Record<string, React.ComponentType> = {
//   'compliance_officer': ShieldAltIcon,
//   'relationship_manager': DollarSignIcon,
//   'branch_teller': UserIcon,
//   'fraud_analyst': EyeIcon,
//   'training_lead': BookIcon,
//   'it_support': CogIcon,
// };

// NEW: Persona colors mapping
// const PERSONA_COLORS: Record<string, 'red' | 'green' | 'blue' | 'orange' | 'purple' | 'grey'> = {
//   'compliance_officer': 'red',
//   'relationship_manager': 'green',
//   'branch_teller': 'blue',
//   'fraud_analyst': 'orange',
//   'training_lead': 'purple',
//   'it_support': 'grey',
// };

// Sample questions for each banking persona - ORGANIZED AS CARDS
// const BANKING_SAMPLE_QUESTIONS: Record<string, { title: string; questions: string[] }> = {
//   'compliance_officer': {
//     title: 'Compliance & Regulations',
//     questions: [
//       "What is the CTR threshold according to the BSA?",
//       "What steps do we follow for a potential OFAC match?",
//       "Has the CFPB issued new fair lending guidance this year?",
//       "What are the key requirements for BSA/AML compliance?"
//     ]
//   },
//   'relationship_manager': {
//     title: 'Lending & Credit',
//     questions: [
//       "What's our minimum FICO score for FHA mortgages?",
//       "Which documents are needed for small business loans?",
//       "What's the maximum DTI ratio for conventional loans?",
//       "How do we calculate loan-to-value ratios?"
//     ]
//   },
//   'branch_teller': {
//     title: 'Customer Service & Operations',
//     questions: [
//       "What is the wire transfer fee for consumer checking accounts?",
//       "What's the daily ATM withdrawal limit for our Platinum debit card?",
//       "How many business days for check deposit holds?",
//       "What are our required timelines for Reg E disputes?"
//     ]
//   },
//   'fraud_analyst': {
//     title: 'Fraud Detection & AML',
//     questions: [
//       "Is frequent cash structuring under $10,000 reportable?",
//       "How do I escalate a suspected synthetic identity case?",
//       "What's our procedure for filing a SAR?",
//       "What are the red flags for money laundering?"
//     ]
//   },
//   'training_lead': {
//     title: 'Training & Market Intelligence',
//     questions: [
//       "What are the major updates in the 2024 FFIEC cybersecurity handbook?",
//       "List top US banking certifications for AML professionals",
//       "Summarize the OCC's latest bulletin on overdraft practices",
//       "What training is required for new compliance staff?"
//     ]
//   },
//   'it_support': {
//     title: 'IT Support & Systems',
//     questions: [
//       "How do I reset my password for the core banking platform?",
//       "What's the process for requesting access to customer information systems?",
//       "How do we handle system outages during business hours?",
//       "What are our cybersecurity protocols for remote access?"
//     ]
//   }
// };

const footnoteProps = {
  label: 'ChatBot uses AI. Check for mistakes.',
  popover: {
    title: 'Verify information',
    description: `While ChatBot strives for accuracy, AI is experimental and can make mistakes. We cannot guarantee that all information provided by ChatBot is up to date or without error. You should always verify responses using reliable sources, especially for crucial information and decision making.`,
    bannerImage: {
      src: 'https://cdn.dribbble.com/userupload/10651749/file/original-8a07b8e39d9e8bf002358c66fce1223e.gif',
      alt: 'Example image for footnote popover',
    },
    cta: {
      label: 'Dismiss',
      onClick: () => {
        alert('Do something!');
      },
    },
    link: {
      label: 'View AI policy',
      url: 'https://www.redhat.com/',
    },
  },
};

export function Chat() {
  const search = useSearch({ from: '/' });
  const navigate = useNavigate();
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [conversations, setConversations] = useState<
    Conversation[] | { [key: string]: Conversation[] }
  >([]);
  const [announcement, setAnnouncement] = useState<string>('');
  const [chatSessions, setChatSessions] = useState<ChatSessionSummary[]>([]);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState<boolean>(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const scrollToBottomRef = React.useRef<HTMLDivElement>(null);
  const historyRef = React.useRef<HTMLButtonElement>(null);

  // Add the missing useChat hook with safety check
  const chatHook = useChat(selectedAgent || 'default', {
    onError: (error: Error) => {
      console.error('Chat error:', error);
      setAnnouncement(`Error: ${error.message}`);
    },
    onFinish: () => {
      setAnnouncement(`Message from assistant complete`);
      if (scrollToBottomRef.current) {
        scrollToBottomRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    },
  });

  // Destructure with safety check
  const {
    messages: chatMessages = [],
    input = '',
    handleInputChange = () => {},
    append = () => {},
    isLoading = false,
    loadSession = async () => {},
    sessionId = '',
  } = chatHook || {};

  // Add this line to define selectedAgentData
  const selectedAgentData = availableAgents.find((agent) => agent.id === selectedAgent);
  // const selectedAgentPersona = selectedAgent ? personaStorage.getPersona(selectedAgent) : null;
  // const selectedPersonaLabel = selectedAgentPersona ? BANKING_PERSONA_LABELS[selectedAgentPersona] || selectedAgentPersona : null;
  // const currentSampleQuestions = selectedAgentPersona ? BANKING_SAMPLE_QUESTIONS[selectedAgentPersona] : null;

  const messages = React.useMemo(
    () =>
      (chatMessages || []).map(
        (msg): MessageProps => ({
          id: msg.id,
          role: msg.role === 'user' ? 'user' : 'bot',
          content: msg.content,
          name: msg.role === 'user' ? 'You' : selectedAgentData?.name || 'Assistant',
          timestamp: msg.timestamp.toLocaleString(),
          avatar: msg.role === 'user' ? userAvatar : botAvatar,
          avatarProps: { isBordered: true },
          isLoading:
            msg.role === 'assistant' &&
            isLoading &&
            msg.id === (chatMessages || [])[(chatMessages || []).length - 1]?.id,
        })
      ),
    [chatMessages, isLoading, selectedAgentData]
  );

  const displayMode = ChatbotDisplayMode.embedded;

  const onSelectAgent = (
    _event: React.MouseEvent<Element, MouseEvent> | undefined,
    value: string | number | undefined
  ) => {
    if (value) {
      const agentId = value.toString();
      console.log('Agent selected:', agentId);
      setSelectedAgent(agentId);
    }
  };

  const onSelectActiveItem = (
    _e?: React.MouseEvent<Element, MouseEvent>,
    selectedItem?: string | number
  ) => {
    if (!selectedItem || typeof selectedItem !== 'string') return;

    void (async () => {
      try {
        await loadSession(selectedItem);
        setIsDrawerOpen(false);
      } catch (error) {
        console.error('Error loading session:', error);
        setAnnouncement('Failed to load chat session');
      }
    })();
  };

  const onNewChat = () => {
    if (!selectedAgent) return;

    void (async () => {
      try {
        const timestamp = new Date()
          .toISOString()
          .slice(0, 19)
          .replace(/[-:]/g, '')
          .replace('T', '-');
        const randomSuffix = Math.random().toString(36).substring(2, 6);
        const uniqueSessionName = `Chat-${timestamp}-${randomSuffix}`;

        const newSession = await createChatSession(selectedAgent, uniqueSessionName);
        await loadSession(newSession.id);
        await fetchSessionsData(selectedAgent);

        setIsDrawerOpen(false);
      } catch (error) {
        console.error('Error creating new session:', error);
        setAnnouncement('Failed to create new chat session');
      }
    })();
  };

  // const handleSampleQuestionClick = (question: string) => {
  //   if (selectedAgent && question.trim()) {
  //     append({
  //       role: 'user',
  //       content: question,
  //     });
  //   }
  // };

  // const toggleSampleQuestions = () => {
  //   // setShowSampleQuestions(!showSampleQuestions); // This line is removed
  // };

  const handleDeleteSession = useCallback((sessionId: string) => {
    console.log('Delete session clicked:', sessionId); // Add this debug line
    setSessionToDelete(sessionId);
    setIsDeleteModalOpen(true);
  }, []);

  const deleteSessionMutation = useMutation<void, Error, string>({
    mutationFn: (sessionId: string) => {
      if (!selectedAgent) throw new Error('No agent selected');
      console.log('Deleting session:', sessionId, 'for agent:', selectedAgent);
      return deleteChatSession(sessionId, selectedAgent);
    },
    onSuccess: async () => {
      if (!selectedAgent) return;
      console.log('Session deleted successfully, refreshing sessions...');
      setAnnouncement('Session deleted successfully');
      
      // Let fetchSessionsData handle the session switching logic
      await fetchSessionsData(selectedAgent);
    },
    onError: (error) => {
      console.error('Error deleting session:', error);
      setAnnouncement(`Failed to delete session: ${error.message}`);
    },
    onSettled: () => {
      console.log('Delete session mutation settled');
      setIsDeleteModalOpen(false);
      setSessionToDelete(null);
    },
  });

  const confirmDeleteSession = () => {
    console.log('Confirming delete for session:', sessionToDelete); // Add this debug line
    if (!sessionToDelete) return;
    deleteSessionMutation.mutate(sessionToDelete);
  };

  const cancelDeleteSession = () => {
    setIsDeleteModalOpen(false);
    setSessionToDelete(null);
  };

  const createSessionMenuItems = useCallback(
    (sessionId: string) => [
      <DropdownList key="session-actions">
        <DropdownItem
          value="Delete"
          id={`delete-${sessionId}`}
          onClick={() => handleDeleteSession(sessionId)}
        >
          Delete
        </DropdownItem>
      </DropdownList>,
    ],
    [handleDeleteSession]
  );

  const findMatchingItems = (targetValue: string) => {
    const filteredConversations = chatSessions.filter((session) =>
      session.title.toLowerCase().includes(targetValue.toLowerCase())
    );

    const conversations = filteredConversations.map((session) => ({
      id: session.id,
      text: session.title,
      description: session.agent_name,
      timestamp: new Date(session.updated_at).toLocaleDateString(),
      menuItems: createSessionMenuItems(session.id),
    }));

    if (conversations.length === 0) {
      conversations.push({
        id: '13',
        text: 'No results found',
        description: '',
        timestamp: '',
        menuItems: [],
      });
    }
    return conversations;
  };

  // Revert the fetchSessionsData to the original working version:

  const fetchSessionsData = useCallback(
    async (agentId?: string) => {
      try {
        const sessions = await fetchChatSessions(agentId);
        setChatSessions(sessions);

        const conversations = sessions.map((session) => ({
          id: session.id,
          text: session.title,
          description: session.agent_name,
          timestamp: new Date(session.updated_at).toLocaleDateString(),
          menuItems: createSessionMenuItems(session.id),
        }));

        setConversations(conversations);

        const currentSessionExists =
          sessionId && sessions.some((session) => session.id === sessionId);

        if ((!sessionId || !currentSessionExists) && sessions.length > 0) {
          const firstSession = sessions[0];
          await loadSession(firstSession.id);
        } else if (sessions.length === 0 && agentId && !sessionId) {
          // Only create a new session if there's no current session (first time loading)
          try {
            const timestamp = new Date()
              .toISOString()
              .slice(0, 19)
              .replace(/[-:]/g, '')
              .replace('T', '-');
            const randomSuffix = Math.random().toString(36).substring(2, 6);
            const uniqueSessionName = `Chat-${timestamp}-${randomSuffix}`;

            const newSession = await createChatSession(agentId, uniqueSessionName);
            await loadSession(newSession.id);

            const newSessionSummary: ChatSessionSummary = {
              id: newSession.id,
              title: newSession.title,
              agent_name: newSession.agent_name,
              updated_at: newSession.updated_at,
              created_at: newSession.created_at,
            };
            setChatSessions([newSessionSummary]);

            const conversationObj = {
              id: newSession.id,
              text: newSession.title,
              description: newSession.agent_name,
              timestamp: new Date(newSession.updated_at).toLocaleDateString(),
              menuItems: createSessionMenuItems(newSession.id),
            };
            setConversations([conversationObj]);
          } catch (error) {
            console.error('Error creating initial session:', error);
            setAnnouncement('Failed to create initial session');
          }
        }
      } catch (error) {
        console.error('Error fetching chat sessions:', error);
        setAnnouncement(
          `Failed to fetch sessions: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
      }
    },
    [sessionId, loadSession, createSessionMenuItems]
  );

  // Revert the useEffect to exclude fetchSessionsData:
  useEffect(() => {
    if (selectedAgent) {
      void fetchSessionsData(selectedAgent);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAgent]); // ONLY selectedAgent dependency - fetchSessionsData intentionally excluded

  useEffect(() => {
    const fetchAgentsData = async () => {
      try {
        const agents = await fetchAgents();
        setAvailableAgents(agents);
        
        // Check if agentId is provided in URL search params
        console.log('Search params:', search);
        console.log('AgentId from URL:', search.agentId);
        
        if (search.agentId && agents.some(agent => agent.id === search.agentId)) {
          console.log('Setting selected agent from URL:', search.agentId);
          setSelectedAgent(search.agentId);
        } else if (agents.length > 0) {
          const firstAgent = agents[0].id;
          console.log('Setting first agent as default:', firstAgent);
          setSelectedAgent(firstAgent);
        }
      } catch (err) {
        console.error('Error fetching agents:', err);
        setAnnouncement('Failed to load agents');
      }
    };

    void fetchAgentsData();
  }, [search.agentId]); // Add search.agentId as dependency

  const handleSendMessage = (message: string | number) => {
    if (typeof message === 'string' && message.trim() && selectedAgent) {
      append({
        role: 'user',
        content: message.toString(),
      });
      
      // Add a small delay to ensure the message is added to the DOM
      setTimeout(() => {
        if (scrollToBottomRef.current) {
          scrollToBottomRef.current.scrollIntoView({ behavior: 'smooth' });
        }
      }, 100);
    }
  };

  const handleBackToAgents = () => {
    navigate({ to: '/config/agents', search: { tab: 'my-agents' } });
  };

  return (
    <Chatbot displayMode={displayMode}>
      <ChatbotConversationHistoryNav
        displayMode={displayMode}
        onDrawerToggle={() => {
          setIsDrawerOpen(!isDrawerOpen);
        }}
        isDrawerOpen={isDrawerOpen}
        setIsDrawerOpen={setIsDrawerOpen}
        activeItemId={sessionId || undefined}
        onSelectActiveItem={onSelectActiveItem}
        conversations={conversations}
        onNewChat={onNewChat}
        handleTextInputChange={(value: string) => {
          if (value === '') {
            const conversations = chatSessions.map((session) => ({
              id: session.id,
              text: session.title,
              description: session.agent_name,
              timestamp: new Date(session.updated_at).toLocaleDateString(),
              menuItems: createSessionMenuItems(session.id),
            }));
            setConversations(conversations);
          }
          const newConversations = findMatchingItems(value);
          setConversations(newConversations);
        }}
        drawerContent={
          <Fragment>
            <ChatbotHeader>
              <ChatbotHeaderMain>
                <ChatbotHeaderMenu
                  ref={historyRef}
                  aria-expanded={isDrawerOpen}
                  onMenuToggle={() => setIsDrawerOpen(!isDrawerOpen)}
                />
                <ChatbotHeaderTitle>
                  <Flex direction={{ default: 'column' }} gap={{ default: 'gapSm' }}>
                    <Breadcrumb style={{ marginBottom: '0.5rem' }}>
                      <BreadcrumbItem>
                        <Button
                          variant="link"
                          icon={<AngleLeftIcon />}
                          onClick={handleBackToAgents}
                          style={{ 
                            color: 'var(--text-primary)', 
                            padding: '0',
                            fontSize: '0.9rem'
                          }}
                        >
                          Back to Agents
                        </Button>
                      </BreadcrumbItem>
                    </Breadcrumb>
                    <span>Chat with {selectedAgentData?.name || 'Agent'}</span>
                  </Flex>
                </ChatbotHeaderTitle>
              </ChatbotHeaderMain>
              <ChatbotHeaderActions>
                <ChatbotHeaderSelectorDropdown
                  value={
                    (() => {
                      const selectedAgentData = availableAgents.find((agent) => agent.id === selectedAgent);
                      if (!selectedAgentData) return 'Select Agent';
                      
                      const persona = personaStorage.getPersona(selectedAgentData.id);
                      const personaLabel = persona ? personaService.getPersona(persona)?.label || persona : '';
                      
                      return personaLabel 
                        ? `${selectedAgentData.name} (${personaLabel})`
                        : selectedAgentData.name;
                    })()
                  }
                  onSelect={onSelectAgent}
                  tooltipContent="Select Agent"
                >
                  <DropdownList>
                    {availableAgents.map((agent) => {
                      const persona = personaStorage.getPersona(agent.id);
                      const personaLabel = persona ? personaService.getPersona(persona)?.label || persona : '';
                      const displayText = personaLabel 
                        ? `${agent.name} (${personaLabel})`
                        : agent.name;
                      
                      return (
                        <DropdownItem value={agent.id} key={agent.id}>
                          {displayText}
                        </DropdownItem>
                      );
                    })}
                  </DropdownList>
                </ChatbotHeaderSelectorDropdown>
              </ChatbotHeaderActions>
            </ChatbotHeader>
            <ChatbotContent>
              <MessageBox announcement={announcement}>
                {selectedAgent && (
                  <div style={{ marginBottom: '1rem' }}>
                    <DemoQuestions
                      agentId={selectedAgent}
                      agentName={selectedAgentData?.name}
                      onQuestionClick={(question) => {
                        handleSendMessage(question);
                      }}
                      maxQuestions={4}
                    />
                  </div>
                )}

                {messages.map((message, index) => {
                  if (index === messages.length - 1) {
                    return (
                      <Fragment key={message.id}>
                        <div ref={scrollToBottomRef}></div>
                        <Message key={message.id} {...message} />
                      </Fragment>
                    );
                  }
                  return <Message key={message.id} {...message} />;
                })}
              </MessageBox>
            </ChatbotContent>
            <ChatbotFooter>
              <MessageBar
                onSendMessage={handleSendMessage as (message: string | number) => void}
                hasMicrophoneButton
                isSendButtonDisabled={isLoading || !selectedAgent}
                value={input}
                onChange={handleInputChange}
              />
              <ChatbotFootnote {...footnoteProps} />
            </ChatbotFooter>
          </Fragment>
        }
      ></ChatbotConversationHistoryNav>
      <Modal
        variant={ModalVariant.small}
        title="Confirm Delete"
        isOpen={isDeleteModalOpen}
        onClose={cancelDeleteSession}
      >
        <ModalHeader title="Delete Session" labelId="delete-session-modal-title" />
        <ModalBody id="delete-session-modal-desc">
          Are you sure you want to delete this session?
        </ModalBody>
        <ModalFooter>
          <Button variant="link" onClick={cancelDeleteSession}>
            Cancel
          </Button>
          <Button
            variant="danger"
            isLoading={deleteSessionMutation.isPending}
            onClick={confirmDeleteSession}
          >
            Delete
          </Button>
        </ModalFooter>
      </Modal>
    </Chatbot>
  );
}