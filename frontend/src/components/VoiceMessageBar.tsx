import React, { useCallback, useState, useRef, useEffect } from 'react';
import { MessageBar } from '@patternfly/chatbot';
import { Button, Tooltip } from '@patternfly/react-core';
import { MicrophoneIcon, MicrophoneSlashIcon } from '@patternfly/react-icons';
import { useVoiceInput, Sentence } from '@/hooks/useVoiceInput';

export interface VoiceMessageBarProps {
  onSendMessage: (message: string | number) => void;
  isSendButtonDisabled?: boolean;
  value?: string;
  onChange?: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>, value?: string | number) => void;
  handleAttach?: (files: File[]) => void;
  sessionId?: string | null;
  placeholder?: string;
  language?: string;
  onSentences?: (sentences: Sentence[]) => void;
}

/**
 * Enhanced MessageBar component with voice input capabilities
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
  onSentences
}: VoiceMessageBarProps) {
  // Remove local state - use prop value directly
  const [voiceInputActive, setVoiceInputActive] = useState(false);
  const [justTranscribed, setJustTranscribed] = useState(false);
  const messageBarRef = useRef<HTMLDivElement>(null);

  const handleInputChange = useCallback((
    event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>,
    newValue?: string | number
  ) => {
    // Simply pass through to parent - no local state
    onChange?.(event, newValue);
  }, [onChange]);

  // Voice input hook
  const {
    isRecording,
    isProcessing,
    error: voiceError,
    isSupported: voiceSupported,
    toggleRecording,
    clearError,
    useWebSpeech
  } = useVoiceInput({
    onTranscript: (text: string) => {
      // When we get a transcript, add it to the input field
      const newValue = value ? `${value} ${text}` : text;
      // Trigger onChange to update parent component
      if (onChange) {
        const event = {
          target: { value: newValue }
        } as React.ChangeEvent<HTMLInputElement>;
        onChange(event, newValue);
      }
      setVoiceInputActive(false);
      setJustTranscribed(true);
    },
    onSentences: (sentenceData: Sentence[]) => {
      // Pass sentences to parent component for display
      onSentences?.(sentenceData);
    },
    onError: (error: Error) => {
      console.error('Voice input error:', error);
      setVoiceInputActive(false);
    },
    language,
    sessionId
  });

  // Focus and update the input after voice transcription
  useEffect(() => {
    if (justTranscribed && messageBarRef.current) {
      // Find the input element within the MessageBar
      const inputElement = messageBarRef.current.querySelector('input, textarea') as HTMLInputElement | HTMLTextAreaElement;
      if (inputElement) {
        // Small delay to ensure DOM is updated
        setTimeout(() => {
          // Directly set the value to force update
          inputElement.value = value || '';

          // Trigger the React onChange event properly
          const changeEvent = {
            target: inputElement,
            currentTarget: inputElement,
            type: 'change',
            bubbles: true
          } as React.ChangeEvent<HTMLInputElement>;

          // Call our handleInputChange directly to update React state
          handleInputChange(changeEvent, value);

          // Also dispatch native event for good measure
          const nativeEvent = new Event('input', { bubbles: true });
          inputElement.dispatchEvent(nativeEvent);

          // Focus and position cursor at the end
          inputElement.focus();
          if (inputElement.setSelectionRange) {
            const length = inputElement.value.length;
            inputElement.setSelectionRange(length, length);
          }
        }, 50);
      }
      setJustTranscribed(false);
    }
  }, [justTranscribed, value, handleInputChange]);

  const handleVoiceToggle = useCallback(() => {
    if (voiceError) {
      clearError();
    }

    if (!voiceSupported && !useWebSpeech) {
      alert('Voice input is not supported in your browser. Please try using Chrome, Firefox, or Safari.');
      return;
    }

    if (!sessionId) {
      alert('Please start a chat session before using voice input.');
      return;
    }

    setVoiceInputActive(!voiceInputActive);
    toggleRecording();
  }, [voiceError, clearError, voiceSupported, useWebSpeech, sessionId, voiceInputActive, toggleRecording]);

  const handleSendMessage = useCallback((message: string | number) => {
    // Send the message and clear voice input state
    onSendMessage(message);
    setVoiceInputActive(false);
  }, [onSendMessage]);

  // Voice status indicator
  const getVoiceStatus = () => {
    if (isProcessing) return 'Processing...';
    if (isRecording) return 'Listening...';
    if (voiceError) return `Error: ${voiceError}`;
    if (!voiceSupported && !useWebSpeech) return 'Voice not supported';
    return voiceSupported ? 'Click to start voice input' : 'Using browser speech recognition';
  };

  const getVoiceIcon = () => {
    if (isRecording || voiceInputActive) {
      return <MicrophoneSlashIcon />;
    }
    return <MicrophoneIcon />;
  };

  const isVoiceButtonDisabled = () => {
    return isProcessing || (!voiceSupported && !useWebSpeech) || !sessionId;
  };

  // Enhanced placeholder text
  const getPlaceholder = () => {
    if (isRecording) return 'Listening... Click microphone to stop';
    if (isProcessing) return 'Processing speech...';
    return placeholder;
  };

  return (
    <div style={{ position: 'relative' }}>
      {/* Voice input status indicator */}
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

      {/* Simple MessageBar to restore send button functionality */}
      <div ref={messageBarRef}>
        <MessageBar
          onSendMessage={handleSendMessage}
          isSendButtonDisabled={isSendButtonDisabled || isProcessing}
          value={value}
          onChange={handleInputChange}
          handleAttach={handleAttach}
          placeholder={getPlaceholder()}
          hasMicrophoneButton
        />
      </div>

      {/* Voice capability indicator */}
      {voiceSupported || useWebSpeech ? (
        <div
          style={{
            position: 'absolute',
            bottom: '-20px',
            right: '0',
            fontSize: '10px',
            color: '#666',
            fontStyle: 'italic'
          }}
        >
          {useWebSpeech ? '🎤 Browser speech' : '🎤 Voice enabled'}
        </div>
      ) : null}
    </div>
  );
}