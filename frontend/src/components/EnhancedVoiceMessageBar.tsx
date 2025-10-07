import React, { useState, useCallback } from 'react';
import { VoiceMessageBar, VoiceMessageBarProps } from './VoiceMessageBar';
import { SentenceDisplay, Sentence } from './SentenceDisplay';
import { Card, CardBody, CardTitle, Button } from '@patternfly/react-core';

export interface EnhancedVoiceMessageBarProps extends VoiceMessageBarProps {
  showSentenceDisplay?: boolean;
  onSentenceClick?: (sentence: Sentence) => void;
}

/**
 * Enhanced VoiceMessageBar with sentence-by-sentence display functionality
 */
export function EnhancedVoiceMessageBar({
  showSentenceDisplay = true,
  onSentenceClick,
  onSendMessage,
  ...voiceMessageBarProps
}: EnhancedVoiceMessageBarProps) {
  const [sentences, setSentences] = useState<Sentence[]>([]);
  const [isVoiceMode, setIsVoiceMode] = useState(false);

  const handleSentences = useCallback((newSentences: Sentence[]) => {
    setSentences(newSentences);
    setIsVoiceMode(true);
  }, []);

  const handleSendMessage = useCallback((message: string | number) => {
    // Clear sentences when message is sent
    setSentences([]);
    setIsVoiceMode(false);
    onSendMessage(message);
  }, [onSendMessage]);

  const handleSentenceClick = useCallback((sentence: Sentence) => {
    // When a sentence is clicked, use it as the message input
    if (voiceMessageBarProps.onChange && typeof sentence.text === 'string') {
      const event = {
        target: { value: sentence.text }
      } as React.ChangeEvent<HTMLInputElement>;
      voiceMessageBarProps.onChange(event, sentence.text);
    }
    onSentenceClick?.(sentence);
  }, [voiceMessageBarProps.onChange, onSentenceClick]);

  return (
    <div style={{ position: 'relative' }}>
      {/* Sentence display panel - shown when we have sentences from voice input */}
      {showSentenceDisplay && sentences.length > 0 && (
        <Card
          style={{
            position: 'absolute',
            bottom: '100%',
            left: 0,
            right: 0,
            marginBottom: '8px',
            maxHeight: '300px',
            overflowY: 'auto',
            backgroundColor: '#fff',
            boxShadow: '0 4px 8px rgba(0,0,0,0.1)',
            border: '1px solid #d2d2d2',
            zIndex: 1000
          }}
        >
          <CardTitle style={{ padding: '12px 16px 8px', fontSize: '14px', fontWeight: '600', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Voice Transcription - {sentences.length} sentence{sentences.length !== 1 ? 's' : ''} detected</span>
            <Button
              variant="link"
              size="sm"
              onClick={() => setSentences([])}
              style={{ fontSize: '12px', padding: '4px 8px' }}
            >
              Clear All
            </Button>
          </CardTitle>
          <CardBody style={{ padding: '0 16px 16px' }}>
            <SentenceDisplay
              sentences={sentences}
              showTimestamp={true}
              showConfidence={true}
              onSentenceClick={handleSentenceClick}
            />
            <div style={{
              marginTop: '12px',
              padding: '8px',
              backgroundColor: '#f1f8ff',
              borderRadius: '4px',
              fontSize: '12px',
              color: '#6a6e73',
              fontStyle: 'italic'
            }}>
              💡 Click on a sentence to use it as your message, or edit the text below and send.
            </div>
          </CardBody>
        </Card>
      )}

      {/* Enhanced VoiceMessageBar with sentence handling */}
      <VoiceMessageBar
        {...voiceMessageBarProps}
        onSendMessage={handleSendMessage}
        // Pass the sentence handler to the voice input hook via a custom prop
        onSentences={handleSentences}
      />
    </div>
  );
}

// Update VoiceMessageBar to accept onSentences prop
declare module './VoiceMessageBar' {
  interface VoiceMessageBarProps {
    onSentences?: (sentences: Sentence[]) => void;
  }
}