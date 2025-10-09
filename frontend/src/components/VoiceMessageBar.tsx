import React, { useCallback, useState } from 'react';
import { MessageBar } from '@patternfly/chatbot';
import { useVoiceInput, Sentence } from '@/hooks/useVoiceInput';

export interface VoiceMessageBarProps {
  onSendMessage: (message: string | number) => void;
  isSendButtonDisabled?: boolean;
  value?: string;
  onChange?: (
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    value?: string | number
  ) => void;
  handleAttach?: (files: File[]) => void;
  sessionId?: string | null;
  placeholder?: string;
  language?: string;
  onSentences?: (sentences: Sentence[]) => void;
}

/**
 * Enhanced MessageBar component with voice input capabilities
 * Using PatternFly's native microphone button with privacy-focused override
 */
export function VoiceMessageBar({
  onSendMessage,
  isSendButtonDisabled = false,
  value = '',
  onChange,
  handleAttach,
  sessionId,
  placeholder = 'Type a message or click the microphone to speak...',
  language = 'en',
  onSentences,
}: VoiceMessageBarProps) {
  const [voiceUpdateKey, setVoiceUpdateKey] = useState(0);

  const handleInputChange = useCallback(
    (
      event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
      newValue?: string | number
    ) => {
      onChange?.(event, newValue);
    },
    [onChange]
  );

  // Voice input hook - same as original VoiceMessageBar
  const {
    isRecording,
    isProcessing,
    error: voiceError,
    isSupported: voiceSupported,
    toggleRecording,
    clearError,
    useWebSpeech,
  } = useVoiceInput({
    onTranscript: (text: string) => {
      // When we get a transcript, add it to the input field
      const newValue = value ? `${value} ${text}` : text;
      // Trigger onChange to update parent component
      if (onChange) {
        const event = {
          target: { value: newValue },
        } as React.ChangeEvent<HTMLInputElement>;
        onChange(event, newValue);
      }
      // Force MessageBar re-render with voice content
      setVoiceUpdateKey((prev) => prev + 1);
    },
    onSentences: (sentenceData: Sentence[]) => {
      // Pass sentences to parent component for display
      onSentences?.(sentenceData);
    },
    onError: (error: Error) => {
      console.error('Voice input error:', error);
    },
    language,
    sessionId,
  });

  const handleSendMessage = useCallback(
    (message: string | number) => {
      onSendMessage(message);
    },
    [onSendMessage]
  );

  // Voice toggle handler that uses our privacy-focused implementation
  const handleVoiceToggle = useCallback(() => {
    if (voiceError) {
      clearError();
    }

    if (!voiceSupported && !useWebSpeech) {
      alert(
        'Voice input is not supported in your browser. Please try using Chrome, Firefox, or Safari.'
      );
      return;
    }

    if (!sessionId) {
      alert('Please start a chat session before using voice input.');
      return;
    }

    toggleRecording();
  }, [
    voiceError,
    clearError,
    voiceSupported,
    useWebSpeech,
    sessionId,
    toggleRecording,
  ]);

  // Voice status and UI functions - same as original
  const getVoiceStatus = () => {
    if (isProcessing) return 'Processing...';
    if (isRecording) return 'Listening...';
    if (voiceError) return `Error: ${voiceError}`;
    if (!voiceSupported && !useWebSpeech) return 'Voice not supported';
    return voiceSupported ? 'Click to start voice input' : 'Using browser speech recognition';
  };

  const getPlaceholder = () => {
    if (isRecording) return 'Listening... Click microphone to stop';
    if (isProcessing) return 'Processing speech...';
    return placeholder;
  };

  return (
    <div style={{ position: 'relative' }}>
      {/* Voice input status indicator - same as original VoiceMessageBar */}
      {(isRecording || isProcessing || voiceError) && (
        <div
          style={{
            position: 'absolute',
            top: '-30px',
            left: '0',
            right: '0',
            background: isRecording ? '#e3f2fd' : isProcessing ? '#fff3e0' : '#ffebee',
            color: isRecording ? '#1976d2' : isProcessing ? '#f57c00' : '#d32f2f',
            padding: '4px 8px',
            borderRadius: '4px',
            fontSize: '12px',
            zIndex: 10,
            textAlign: 'center',
            border: `1px solid ${isRecording ? '#1976d2' : isProcessing ? '#f57c00' : '#d32f2f'}`,
          }}
        >
          {getVoiceStatus()}
        </div>
      )}

      {/* Clean PatternFly MessageBar with overridden microphone behavior */}
      <MessageBar
        key={`voice-${voiceUpdateKey}`}
        onSendMessage={handleSendMessage}
        isSendButtonDisabled={isSendButtonDisabled || isProcessing}
        value={value}
        onChange={handleInputChange}
        handleAttach={handleAttach}
        placeholder={getPlaceholder()}
        hasMicrophoneButton={true} // Use PatternFly's native microphone UI
        buttonProps={{
          attach: {
            tooltipContent: 'Attach files',
          },
          microphone: {
            language: language,
            tooltipContent: {
              active: 'Stop listening',
              inactive: 'Use microphone'
            },
            props: {
              // Override PatternFly's onClick with our privacy-focused implementation
              onClick: (e: React.MouseEvent) => {
                e.preventDefault();
                handleVoiceToggle();
              },
              // Override the disabled state to respect our sessionId check
              isDisabled: isProcessing || !sessionId,
              // Override visual state to reflect our recording state
              'aria-pressed': isRecording,
              className: `pf-chatbot__button--microphone ${
                isRecording ? 'pf-chatbot__button--microphone--active' : ''
              }`,
              style: {
                ...(isRecording && {
                  color: '#ffffff',
                  backgroundColor: '#1976d2',
                  border: '1px solid #1976d2',
                }),
                ...(voiceError && !isRecording && {
                  color: '#d32f2f',
                }),
              }
            }
          },
          send: {
            tooltipContent: 'Send message',
          },
        }}
      />

      {/* Voice capability indicator - same as original */}
      {voiceSupported || useWebSpeech ? (
        <div
          style={{
            position: 'absolute',
            bottom: '-20px',
            right: '0',
            fontSize: '10px',
            color: '#666',
            fontStyle: 'italic',
          }}
        >
          {useWebSpeech ? '🎤 Browser speech' : '🎤 Voice enabled'}
        </div>
      ) : null}
    </div>
  );
}
