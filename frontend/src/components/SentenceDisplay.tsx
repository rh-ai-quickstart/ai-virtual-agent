import { Label, Tooltip } from '@patternfly/react-core';
import { CheckCircleIcon, ExclamationTriangleIcon } from '@patternfly/react-icons';

export interface Sentence {
  text: string;
  start_time?: number | null;
  end_time?: number | null;
  confidence?: number | null;
  index: number;
}

export interface SentenceDisplayProps {
  sentences: Sentence[];
  showTimestamp?: boolean;
  showConfidence?: boolean;
  onSentenceClick?: (sentence: Sentence) => void;
}

/**
 * Component to display transcribed sentences with visual indicators
 */
export function SentenceDisplay({
  sentences,
  showTimestamp = true,
  showConfidence = true,
  onSentenceClick
}: SentenceDisplayProps) {
  const formatTime = (time: number | null | undefined): string => {
    if (time === null || time === undefined) return '';
    const minutes = Math.floor(time / 60);
    const seconds = (time % 60).toFixed(1);
    return `${minutes}:${seconds.padStart(4, '0')}`;
  };

  const getConfidenceColor = (confidence: number | null | undefined): 'green' | 'orange' | 'red' | 'grey' => {
    if (confidence === null || confidence === undefined) return 'grey';
    if (confidence >= 0.8) return 'green';
    if (confidence >= 0.6) return 'orange';
    return 'red';
  };

  const getConfidenceIcon = (confidence: number | null | undefined) => {
    if (confidence === null || confidence === undefined) return null;
    if (confidence >= 0.6) {
      return <CheckCircleIcon style={{ marginLeft: '4px' }} />;
    }
    return <ExclamationTriangleIcon style={{ marginLeft: '4px' }} />;
  };

  if (!sentences || sentences.length === 0) {
    return (
      <div style={{ fontStyle: 'italic', color: '#6a6e73' }}>
        No sentences detected in transcription
      </div>
    );
  }

  return (
    <div className="sentence-display">
      {sentences.map((sentence, index) => (
        <div
          key={sentence.index || index}
          style={{
            marginBottom: '12px',
            padding: '8px 12px',
            backgroundColor: '#f8f9fa',
            borderLeft: '3px solid #0066cc',
            borderRadius: '4px',
            cursor: onSentenceClick ? 'pointer' : 'default',
            transition: 'background-color 0.2s ease',
          }}
          onClick={() => onSentenceClick?.(sentence)}
          onMouseEnter={(e) => {
            if (onSentenceClick) {
              e.currentTarget.style.backgroundColor = '#e3f2fd';
            }
          }}
          onMouseLeave={(e) => {
            if (onSentenceClick) {
              e.currentTarget.style.backgroundColor = '#f8f9fa';
            }
          }}
        >
          {/* Sentence text */}
          <div style={{ marginBottom: '6px', lineHeight: '1.4' }}>
            <span style={{ fontWeight: '500' }}>
              {sentence.text}
            </span>
            {getConfidenceIcon(sentence.confidence)}
          </div>

          {/* Metadata row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {/* Sentence index */}
            <Label variant="outline" color="blue" isCompact>
              #{sentence.index + 1}
            </Label>

            {/* Timing information */}
            {showTimestamp && (sentence.start_time !== null || sentence.end_time !== null) && (
              <Label variant="outline" color="blue" isCompact>
                {sentence.start_time !== null && sentence.end_time !== null
                  ? `${formatTime(sentence.start_time)} - ${formatTime(sentence.end_time)}`
                  : sentence.start_time !== null
                  ? `Start: ${formatTime(sentence.start_time)}`
                  : `End: ${formatTime(sentence.end_time)}`}
              </Label>
            )}

            {/* Confidence score */}
            {showConfidence && sentence.confidence !== null && sentence.confidence !== undefined && (
              <Tooltip content={`Confidence score: ${(sentence.confidence * 100).toFixed(1)}%`}>
                <Label
                  variant="outline"
                  color={getConfidenceColor(sentence.confidence)}
                  isCompact
                >
                  {(sentence.confidence * 100).toFixed(1)}%
                </Label>
              </Tooltip>
            )}

            {/* Duration */}
            {sentence.start_time !== null && sentence.end_time !== null && (
              <Label variant="outline" color="purple" isCompact>
                {((sentence.end_time! - sentence.start_time!) || 0).toFixed(1)}s
              </Label>
            )}
          </div>
        </div>
      ))}

      {/* Summary */}
      <div style={{
        marginTop: '16px',
        padding: '8px',
        backgroundColor: '#f1f8ff',
        borderRadius: '4px',
        fontSize: '12px',
        color: '#6a6e73'
      }}>
        Total: {sentences.length} sentence{sentences.length !== 1 ? 's' : ''}
        {sentences.some(s => s.start_time !== null && s.end_time !== null) && (
          <span style={{ marginLeft: '16px' }}>
            Duration: {(() => {
              const validSentences = sentences.filter(s => s.start_time !== null && s.end_time !== null);
              if (validSentences.length === 0) return 'Unknown';
              const minStart = Math.min(...validSentences.map(s => s.start_time!));
              const maxEnd = Math.max(...validSentences.map(s => s.end_time!));
              return formatTime(maxEnd - minStart);
            })()}
          </span>
        )}
      </div>
    </div>
  );
}