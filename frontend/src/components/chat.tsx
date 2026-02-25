import React, { Fragment, useEffect, useState, useCallback } from 'react';
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
  FileDetailsLabel,
  Message,
  MessageBar,
  MessageBox,
} from '@patternfly/chatbot';
import {
  DropdownItem,
  DropdownList,
  Modal,
  ModalVariant,
  Button,
  Alert,
  AlertActionCloseButton,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Panel,
  PanelMain,
  PanelMainBody,
} from '@patternfly/react-core';
import { Agent } from '@/types/agent';
import { fetchUserAgents } from '@/services/agents';
import { useChat } from '@/hooks/useChat';
import { useCurrentUser } from '@/contexts/UserContext';
import {
  fetchChatSessions,
  createChatSession,
  deleteChatSession,
  ChatSessionSummary,
} from '@/services/chat-sessions';
import { useMutation } from '@tanstack/react-query';
import botAvatar from '../assets/img/bot-avatar.svg';
import userAvatar from '../assets/img/user-avatar.svg';
import { ATTACHMENTS_API_ENDPOINT } from '@/config/api';
import { SimpleContentItem } from '@/types/chat';
import { getTemplateDetails } from '@/services/agent-templates';
import {
  ReasoningSection,
  ToolCallSection,
  GraphNodeOutputSection,
} from './ExpandableContent';

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

interface ChatProps {
  preSelectedAgentId?: string;
}

export function Chat({ preSelectedAgentId }: ChatProps = {}) {
  const [availableAgents, setAvailableAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [conversations, setConversations] = useState<
    Conversation[] | { [key: string]: Conversation[] }
  >([]);
  const [announcement, setAnnouncement] = useState<string>('');
  const [noAgentsWarning, setNoAgentsWarning] = useState<string | null>(null);
  const [historyWarning, setHistoryWarning] = useState<string | null>(null);
  const [chatSessions, setChatSessions] = useState<ChatSessionSummary[]>([]);
  const [demoQuestions, setDemoQuestions] = useState<string[]>([]);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const composerRef = React.useRef<HTMLDivElement>(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState<boolean>(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const [isSwitchWarningOpen, setIsSwitchWarningOpen] = useState<boolean>(false);
  const [pendingSessionSwitch, setPendingSessionSwitch] = useState<string | null>(null);
  const scrollToBottomRef = React.useRef<HTMLDivElement>(null);
  const historyRef = React.useRef<HTMLButtonElement>(null);
  const previousMessageCountRef = React.useRef<number>(0);

  // Get current user context
  const {
    currentUser,
    isLoading: isUserLoading,
    error: userError,
    refetch: refetchUser,
  } = useCurrentUser();

  // Get the selected agent object
  const selectedAgentObj = availableAgents.find((agent) => agent.id === selectedAgent);

  // Use our custom hook for chat functionality - only when we have a valid agent
  const {
    messages: chatMessages,
    input,
    handleInputChange,
    append,
    isLoading,
    loadSession,
    sessionId,
    setSessionId,
    attachedFiles,
    handleAttach,
    clearAttachedFiles,
    setAttachedFiles,
    flushPendingUpdates,
  } = useChat(selectedAgent || 'default', {
    onError: (error: Error) => {
      console.error('Chat error:', error);
      setAnnouncement(`Error: ${error.message}`);
    },
    onFinish: () => {
      setAnnouncement(`Message from assistant complete`);
      // No auto-scroll on completion - user scrolls manually
      // Session list will be refreshed when user opens the drawer (on-demand)
    },
  });
  // Separate content into markdown strings and expandable React components
  const separateContent = React.useCallback((content: SimpleContentItem[] | undefined) => {
    if (!content || !Array.isArray(content) || content.length === 0) {
      return { markdownContent: '', expandableComponents: [] as React.ReactNode[] };
    }

    const textParts: string[] = [];
    const expandableComponents: React.ReactNode[] = [];

    // Collect graph node items to detect graph agent responses
    const graphNodes = content.filter(
      (item): item is import('@/types/chat').GraphNodeContentItem => item.type === 'graph_node'
    );
    const graphNodeIds = new Set(graphNodes.map((n) => n.node_id));

    // Build a map of node_id -> accumulated output text for graph responses
    const nodeOutputMap = new Map<string, string>();
    if (graphNodes.length > 0) {
      content.forEach((item) => {
        if (item.type === 'output_text' && item.id && graphNodeIds.has(item.id)) {
          const existing = nodeOutputMap.get(item.id) || '';
          nodeOutputMap.set(item.id, existing + item.text);
        }
      });
    }

    if (graphNodes.length > 0) {
      graphNodes.forEach((node) => {
        const outputText = nodeOutputMap.get(node.node_id) || '';
        expandableComponents.push(
          <GraphNodeOutputSection
            key={`graph-node-${node.node_id}`}
            nodeId={node.node_id}
            label={node.label}
            status={node.status}
            outputText={outputText}
          />
        );
      });
    }

    content.forEach((item, index) => {
      if (item.type === 'input_text') {
        textParts.push(item.text);
      } else if (item.type === 'output_text') {
        // Skip output_text items that belong to graph nodes (rendered in sections above)
        if (item.id && graphNodeIds.has(item.id)) return;
        textParts.push(item.text);
      } else if (item.type === 'input_image') {
        const imageUrl = item.image_url.startsWith('/')
          ? `${window.location.origin}${item.image_url}`
          : item.image_url;
        textParts.push(`![Image](${imageUrl})`);
      } else if (item.type === 'reasoning') {
        expandableComponents.push(
          <ReasoningSection
            key={`reasoning-${index}`}
            text={item.text}
            isComplete={item.isComplete}
          />
        );
      } else if (item.type === 'tool_call') {
        expandableComponents.push(
          <ToolCallSection
            key={`tool-${index}`}
            name={item.name}
            serverLabel={item.server_label}
            status={item.status}
            arguments={item.arguments}
            output={item.output}
            error={item.error}
          />
        );
      }
      // graph_node items are handled above
    });

    return {
      markdownContent: textParts.join('\n\n'),
      expandableComponents,
    };
  }, []);

  // Convert our chat messages to PatternFly format
  const messages = React.useMemo(() => {
    const lastMessageId = chatMessages[chatMessages.length - 1]?.id;
    return chatMessages.map((msg) => {
      // Merge tool_calls into content for display
      const allContent = [...msg.content];
      if (msg.tool_calls && msg.tool_calls.length > 0) {
        // Add tool calls before the text content
        allContent.unshift(...msg.tool_calls);
      }

      const { markdownContent, expandableComponents } = separateContent(allContent);

      const role: 'user' | 'bot' = msg.role === 'user' ? 'user' : 'bot';

      return {
        id: msg.id,
        role,
        content: markdownContent,
        extraContent:
          expandableComponents.length > 0
            ? {
                beforeMainContent: <>{expandableComponents}</>,
              }
            : undefined,
        name: msg.role === 'user' ? 'You' : 'Agent',
        timestamp: msg.timestamp.toLocaleString(),
        avatar: msg.role === 'user' ? userAvatar : botAvatar,
        avatarProps: { isBordered: true },
        isLoading: msg.role === 'assistant' && isLoading && msg.id === lastMessageId,
      };
    });
  }, [chatMessages, isLoading, separateContent]);

  // Memoize the message list to prevent re-rendering when only input changes
  const MemoizedMessageBox = React.useMemo(
    () => (
      <MessageBox
        announcement={announcement}
        style={{ maxWidth: '85%', width: '85%', margin: '0 auto' }}
      >
        {historyWarning && (
          <Alert
            variant="info"
            isInline
            isPlain
            title={historyWarning}
            actionClose={<AlertActionCloseButton onClose={() => setHistoryWarning(null)} />}
            style={{
              margin: '8px 0',
              fontSize: '0.875rem',
              padding: '8px 12px',
              border: '1px solid var(--pf-v6-global--BorderColor--100, #d2d2d2)',
              borderRadius: '4px',
            }}
          />
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
    ),
    [messages, announcement, historyWarning]
  );

  const displayMode = ChatbotDisplayMode.embedded;

  // Scroll to last message when user sends a message
  useEffect(() => {
    const currentCount = chatMessages.length;
    const previousCount = previousMessageCountRef.current;

    // Only scroll when messages are added (user sent a message)
    if (currentCount > previousCount) {
      if (scrollToBottomRef.current) {
        scrollToBottomRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    }

    previousMessageCountRef.current = currentCount;
  }, [chatMessages]);

  // Load demo questions for the selected agent (if template-backed)
  useEffect(() => {
    const loadDemoQuestions = async () => {
      try {
        const templateName = selectedAgentObj?.template_id || selectedAgentObj?.template_name;
        if (!templateName) {
          setDemoQuestions([]);
          return;
        }
        const details = await getTemplateDetails(templateName);
        const questions = Array.isArray(details.demo_questions) ? details.demo_questions : [];
        setDemoQuestions(questions);
      } catch (e) {
        console.warn('Failed to load demo questions:', e);
        setDemoQuestions([]);
      }
    };
    void loadDemoQuestions();
  }, [selectedAgentObj]);

  // Hide demo questions after the first message is present, but restore them for empty sessions
  useEffect(() => {
    if (chatMessages.length > 0 && demoQuestions.length > 0) {
      setDemoQuestions([]);
    } else if (chatMessages.length === 0 && selectedAgentObj && demoQuestions.length === 0) {
      // Restore demo questions when starting a new empty session and demo questions are not already loaded
      const loadDemoQuestions = async () => {
        try {
          const templateName = selectedAgentObj?.template_id || selectedAgentObj?.template_name;
          if (!templateName) {
            return;
          }
          const details = await getTemplateDetails(templateName);
          const questions = Array.isArray(details.demo_questions) ? details.demo_questions : [];
          setDemoQuestions(questions);
        } catch (e) {
          console.warn('Failed to load demo questions:', e);
        }
      };
      void loadDemoQuestions();
    }
  }, [chatMessages.length, selectedAgentObj, demoQuestions.length]);

  const onSelectAgent = (
    _event: React.MouseEvent<Element, MouseEvent> | undefined,
    value: string | number | undefined
  ) => {
    if (value) {
      const agentId = value.toString();
      setSelectedAgent(agentId);
      if (noAgentsWarning) setNoAgentsWarning(null);
    }
  };

  const onSelectActiveItem = (
    _e?: React.MouseEvent<Element, MouseEvent>,
    selectedItem?: string | number
  ) => {
    if (!selectedItem || typeof selectedItem !== 'string') return;

    // Check if currently loading - show warning
    if (isLoading) {
      setPendingSessionSwitch(selectedItem);
      setIsSwitchWarningOpen(true);
      return;
    }

    // Set session ID immediately on click to prevent race condition
    setSessionId(selectedItem);

    void (async () => {
      try {
        await loadSession(selectedItem);
        setIsDrawerOpen(false); // Close sidebar after selection
        // Always show warning when switching to a different session
        // User will manually dismiss it if not needed
        setHistoryWarning(
          'Note: Some messages may not be displayed due to conversation history limitations.'
        );
      } catch (error) {
        console.error('Error loading session:', error);
        setAnnouncement('Failed to load chat session');
      }
    })();
  };

  const confirmSessionSwitch = () => {
    if (!pendingSessionSwitch) return;

    // Flush any pending batched updates before switching
    flushPendingUpdates();

    setSessionId(pendingSessionSwitch);

    void (async () => {
      try {
        await loadSession(pendingSessionSwitch);
        setIsDrawerOpen(false);
        setIsSwitchWarningOpen(false);
        setPendingSessionSwitch(null);
        // Always show warning when switching to a different session
        // User will manually dismiss it if not needed
        setHistoryWarning(
          'Note: Some messages may not be displayed due to conversation history limitations.'
        );
      } catch (error) {
        console.error('Error loading session:', error);
        setAnnouncement('Failed to load chat session');
      }
    })();
  };

  const cancelSessionSwitch = () => {
    setIsSwitchWarningOpen(false);
    setPendingSessionSwitch(null);
  };

  const onNewChat = () => {
    if (!selectedAgent) return;

    void (async () => {
      try {
        // Generate unique session name with timestamp
        const timestamp = new Date()
          .toISOString()
          .slice(0, 19)
          .replace(/[-:]/g, '')
          .replace('T', '-');
        const randomSuffix = Math.random().toString(36).substring(2, 6);
        const uniqueSessionName = `Chat-${timestamp}-${randomSuffix}`;

        // Create a new session for the current agent with unique name
        const newSession = await createChatSession(selectedAgent, uniqueSessionName);

        // Load the new session
        await loadSession(newSession.id);

        // Refresh sessions list to include the new session
        await fetchSessionsData(selectedAgent);

        setIsDrawerOpen(false);
        // Clear warning for new chat
        setHistoryWarning(null);
      } catch (error) {
        console.error('Error creating new session:', error);
        setAnnouncement('Failed to create new chat session');
      }
    })();
  };

  const handleDeleteSession = useCallback((sessionId: string) => {
    setSessionToDelete(sessionId);
    setIsDeleteModalOpen(true);
  }, []);

  const deleteSessionMutation = useMutation<void, Error, string>({
    mutationFn: (sessionId: string) => {
      if (!selectedAgent) throw new Error('No agent selected');
      return deleteChatSession(sessionId, selectedAgent);
    },
    onSuccess: async () => {
      if (!selectedAgent) return;

      setAnnouncement('Session deleted successfully');
      // Simply refresh sessions data - fetchSessionsData handles everything:
      // - If sessions remain: updates UI and loads first session if current was deleted
      // - If no sessions remain: creates new session, loads it, and updates UI
      await fetchSessionsData(selectedAgent);
    },
    onError: (error) => {
      console.error('Error deleting session:', error);
      setAnnouncement(`Failed to delete session: ${error.message}`);
    },
    onSettled: () => {
      // Always clean up modal state when mutation completes
      setIsDeleteModalOpen(false);
      setSessionToDelete(null);
    },
  });

  const confirmDeleteSession = () => {
    if (!sessionToDelete) return;

    // Trigger the mutation
    deleteSessionMutation.mutate(sessionToDelete);
  };

  const cancelDeleteSession = () => {
    setIsDeleteModalOpen(false);
    setSessionToDelete(null);
  };

  // Create menu items for session actions
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

    // Convert to PatternFly conversation format
    const conversations = filteredConversations.map((session) => ({
      id: session.id,
      text: session.title,
      description: session.agent_name,
      timestamp: new Date(session.updated_at).toLocaleDateString(),
      menuItems: createSessionMenuItems(session.id),
    }));

    // append message if no items are found
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

  const fetchSessionsData = useCallback(
    async (agentId?: string) => {
      try {
        const sessions = await fetchChatSessions(agentId);
        setChatSessions(sessions);

        // Convert to PatternFly conversation format
        const conversations = sessions.map((session) => ({
          id: session.id,
          text: session.title,
          description: session.agent_name,
          timestamp: new Date(session.updated_at).toLocaleDateString(),
          menuItems: createSessionMenuItems(session.id),
        }));

        setConversations(conversations);

        // Auto-select first session if no session is currently selected and sessions exist
        // OR if the current sessionId doesn't exist in the fetched sessions (i.e., from different agent)
        const currentSessionExists =
          sessionId && sessions.some((session) => session.id === sessionId);

        if ((!sessionId || !currentSessionExists) && sessions.length > 0) {
          const firstSession = sessions[0]; // Sessions should be ordered by updated_at desc (most recent first)
          await loadSession(firstSession.id);
          // Always show warning when loading a session
          // User will manually dismiss it if not needed
          setHistoryWarning(
            'Note: Some messages may not be displayed due to conversation history limitations.'
          );
        } else if (sessions.length === 0 && agentId) {
          // Create a new session if agent has no sessions
          try {
            // Generate unique session name with timestamp
            const timestamp = new Date()
              .toISOString()
              .slice(0, 19)
              .replace(/[-:]/g, '')
              .replace('T', '-');
            const randomSuffix = Math.random().toString(36).substring(2, 6);
            const uniqueSessionName = `Chat-${timestamp}-${randomSuffix}`;

            const newSession = await createChatSession(agentId, uniqueSessionName);
            await loadSession(newSession.id);

            // Update UI state with the new session
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
    [sessionId, loadSession, setAnnouncement, createSessionMenuItems]
  );

  // Fetch available agents on mount - only when user is loaded
  useEffect(() => {
    const fetchAgentsData = async () => {
      // TODO: This currently fetches agents for the first user in the database.
      // Once proper authentication is implemented, this should fetch agents for the authenticated user.
      if (!currentUser) return;

      try {
        const agents = await fetchUserAgents(currentUser.id);
        setAvailableAgents(agents);

        if (agents.length > 0) {
          let agentToSelect: string;

          // Pre-select agent if requested and available; otherwise use first available
          if (preSelectedAgentId && agents.some((a) => a.id === preSelectedAgentId)) {
            agentToSelect = preSelectedAgentId;
          } else {
            // No specific agent requested, use first available
            agentToSelect = agents[0].id;
          }

          setSelectedAgent(agentToSelect);
          // Don't fetch sessions here - let the selectedAgent useEffect handle it
        } else {
          setAnnouncement('No agents assigned to this user');
          setNoAgentsWarning('No agents are assigned to your account. Please contact an admin.');
        }
      } catch (err) {
        console.error('Error fetching user agents:', err);
        setAnnouncement('Failed to load user agents');
      }
    };

    void fetchAgentsData();
  }, [currentUser, preSelectedAgentId]);

  // Handle selectedAgent changes - fetch sessions for the new agent
  useEffect(() => {
    if (selectedAgent) {
      void fetchSessionsData(selectedAgent);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAgent]); // fetchSessionsData intentionally excluded to prevent infinite loop

  // Handle message sending
  const handleSendMessage = async (message: string | number) => {
    if (typeof message === 'string' && message.trim() && selectedAgent) {
      // Clear history warning when user sends a message
      setHistoryWarning(null);

      const contents: SimpleContentItem[] = [];
      contents.push({ type: 'input_text', text: message });
      for (const file of attachedFiles) {
        const attachmentUrl = await handleUploadAttachment(file, sessionId);
        // Pass relative URL - backend will expand to full URL for LlamaStack
        contents.push({ type: 'input_image', image_url: attachmentUrl });
      }
      // Add the message to the chat
      append({
        role: 'user',
        content: contents,
      });
      clearAttachedFiles();
    }
  };

  const handleUploadAttachment = async (file: File, sessionId: string | null): Promise<string> => {
    if (!sessionId) {
      throw new Error('Session ID is required');
    }

    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);

    const response = await fetch(ATTACHMENTS_API_ENDPOINT, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Failed to upload attachment');
    }

    const data = (await response.json()) as { filename: string };

    // NOTE: The frontend is not aware of its own base URL,
    // so the URL returned here is only the path portion, e.g. /api/attachments/...
    return `${ATTACHMENTS_API_ENDPOINT}${sessionId}/${data.filename}`;
  };

  // Handle loading and error states for user context
  if (isUserLoading) {
    return (
      <div>
        <p>Loading user information...</p>
      </div>
    );
  }

  if (userError || !currentUser) {
    return (
      <div>
        <p>Error loading user: {userError || 'User not found'}</p>
        <p>Please check your authentication or try logging in again.</p>
        <Button variant="primary" onClick={() => void refetchUser()}>
          Retry
        </Button>
      </div>
    );
  }

  return (
    <Fragment>
      {noAgentsWarning && (
        <Alert
          variant="warning"
          isInline
          title={noAgentsWarning}
          actionClose={<AlertActionCloseButton onClose={() => setNoAgentsWarning(null)} />}
          style={{ marginBottom: '8px' }}
        />
      )}
      <Chatbot displayMode={displayMode} isCompact={true}>
        <ChatbotConversationHistoryNav
          displayMode={displayMode}
          onDrawerToggle={() => {
            const newDrawerState = !isDrawerOpen;
            setIsDrawerOpen(newDrawerState);
            // Fetch fresh session data when opening the drawer
            if (newDrawerState && selectedAgent) {
              void fetchSessionsData(selectedAgent);
            }
          }}
          isDrawerOpen={isDrawerOpen}
          setIsDrawerOpen={setIsDrawerOpen}
          activeItemId={sessionId || undefined}
          onSelectActiveItem={onSelectActiveItem}
          conversations={conversations}
          onNewChat={onNewChat}
          isCompact={true}
          handleTextInputChange={(value: string) => {
            if (value === '') {
              // Convert sessions to conversations format
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
                    onMenuToggle={() => {
                      const newDrawerState = !isDrawerOpen;
                      setIsDrawerOpen(newDrawerState);
                      // Fetch fresh session data when opening the drawer
                      if (newDrawerState && selectedAgent) {
                        void fetchSessionsData(selectedAgent);
                      }
                    }}
                  />
                  <ChatbotHeaderTitle>Chat</ChatbotHeaderTitle>
                </ChatbotHeaderMain>
                <ChatbotHeaderActions>
                  <ChatbotHeaderSelectorDropdown
                    value={
                      availableAgents.find((agent) => agent.id === selectedAgent)?.name ||
                      'Select Agent'
                    }
                    onSelect={onSelectAgent}
                    tooltipContent="Select Agent"
                  >
                    <DropdownList>
                      {availableAgents.map((agent) => (
                        <DropdownItem
                          value={agent.id}
                          key={agent.id}
                          isSelected={agent.id === selectedAgent}
                        >
                          {agent.name}
                        </DropdownItem>
                      ))}
                    </DropdownList>
                  </ChatbotHeaderSelectorDropdown>
                </ChatbotHeaderActions>
              </ChatbotHeader>
              <ChatbotContent style={{ maxWidth: '85%', width: '85%', margin: '0 auto' }}>
                {demoQuestions.length > 0 && (
                  <div style={{ padding: '8px 16px' }}>
                    <div style={{ margin: '0 auto', maxWidth: '85%' }}>
                      <div
                        style={{
                          marginBottom: '8px',
                          color: 'var(--pf-v6-global--Color--200, #6A6E73)',
                          textAlign: 'left',
                        }}
                      >
                        Suggested questions
                      </div>
                      <div
                        style={{
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '8px',
                          alignItems: 'flex-start',
                        }}
                      >
                        {demoQuestions.map((q, idx) => (
                          <Button
                            key={`demo-q-${idx}`}
                            variant="plain"
                            onClick={() => {
                              void handleSendMessage(q);
                              setDemoQuestions([]);
                            }}
                            isDisabled={!selectedAgent}
                            size="sm"
                            style={{
                              backgroundColor: 'var(--pf-v6-global--BackgroundColor--100, #ffffff)',
                              color: 'var(--pf-v6-global--Color--100, #151515)',
                              border:
                                hoveredIdx === idx
                                  ? '1px solid var(--pf-v6-global--BorderColor--200, #8a8d90)'
                                  : '1px solid var(--pf-v6-global--BorderColor--100, #d2d2d2)',
                              borderRadius: '9999px',
                              padding: '6px 12px',
                              boxShadow:
                                hoveredIdx === idx
                                  ? '0 1px 3px rgba(0,0,0,0.2)'
                                  : '0 1px 2px rgba(0,0,0,0.06)',
                              transitionProperty: 'background-color, border-color, box-shadow',
                              transitionDuration: '120ms',
                              transitionTimingFunction: 'ease',
                              cursor: 'pointer',
                            }}
                            onMouseEnter={() => setHoveredIdx(idx)}
                            onMouseLeave={() => setHoveredIdx(null)}
                            aria-label={`Suggested question: ${q}`}
                          >
                            {q}
                          </Button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
                {MemoizedMessageBox}
              </ChatbotContent>
              <ChatbotFooter>
                <Panel variant="secondary" ref={composerRef}>
                  <PanelMain>
                    <PanelMainBody>
                      <div
                        style={{
                          display: 'flex',
                          flexWrap: 'wrap',
                          paddingTop: '0.5em',
                          paddingBottom: '0.5em',
                        }}
                      >
                        {attachedFiles.map((file, index) => (
                          <div key={file.name} style={{ margin: '0.5em' }}>
                            <FileDetailsLabel
                              fileName={file.name}
                              onClose={() => {
                                setAttachedFiles(attachedFiles.filter((_, i) => i !== index));
                              }}
                            />
                          </div>
                        ))}
                      </div>
                      <MessageBar
                        onSendMessage={handleSendMessage as (message: string | number) => void}
                        hasMicrophoneButton
                        isSendButtonDisabled={isLoading || !selectedAgent}
                        value={input}
                        onChange={handleInputChange}
                        handleAttach={handleAttach}
                      />
                    </PanelMainBody>
                  </PanelMain>
                </Panel>
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
        <Modal
          variant={ModalVariant.small}
          title="Message in Progress"
          isOpen={isSwitchWarningOpen}
          onClose={cancelSessionSwitch}
        >
          <ModalHeader title="Message in Progress" labelId="switch-session-modal-title" />
          <ModalBody id="switch-session-modal-desc">
            A message is currently being generated. If you switch sessions now, you can view the
            completed message by switching back later. Do you want to continue?
          </ModalBody>
          <ModalFooter>
            <Button variant="link" onClick={cancelSessionSwitch}>
              Cancel
            </Button>
            <Button variant="primary" onClick={confirmSessionSwitch}>
              Switch Session
            </Button>
          </ModalFooter>
        </Modal>
      </Chatbot>
    </Fragment>
  );
}
