import React, { useState } from 'react';
import { ExpandableSection, ProgressStep, ProgressStepper, Spinner } from '@patternfly/react-core';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { GraphNodeStatus } from '@/types/chat';

interface ReasoningSectionProps {
  text: string;
  isComplete?: boolean;
}

export const ReasoningSection: React.FC<ReasoningSectionProps> = ({ text, isComplete = true }) => {
  const statusEmoji = isComplete ? '✅' : '⏳';

  return (
    <ExpandableSection toggleText={`${statusEmoji} Reasoning`} isIndented displaySize="default">
      <div
        style={{
          fontStyle: 'italic',
          padding: '8px',
          borderLeft: '2px solid #d2d2d2',
          color: '#6a6e73',
        }}
      >
        {text}
      </div>
    </ExpandableSection>
  );
};

interface ToolCallSectionProps {
  name: string;
  serverLabel?: string;
  status?: 'in_progress' | 'completed' | 'failed';
  arguments?: string;
  output?: string;
  error?: string;
}

export const ToolCallSection: React.FC<ToolCallSectionProps> = ({
  name,
  serverLabel,
  status = 'completed',
  arguments: args,
  output,
  error,
}) => {
  const statusEmoji = status === 'completed' ? '✅' : status === 'failed' ? '❌' : '⏳';
  const toolName = serverLabel ? `${serverLabel}::${name}` : name;

  const codeBlockStyle = {
    background: '#e8e8e8',
    padding: '8px',
    borderRadius: '4px',
    overflowX: 'auto' as const,
    marginTop: '4px',
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-word' as const,
    border: '1px solid #d2d2d2',
  };

  return (
    <ExpandableSection
      toggleText={`${statusEmoji} Tool Call: ${toolName}`}
      isIndented
      displaySize="default"
    >
      <div
        style={{
          fontStyle: 'italic',
          padding: '8px',
          borderLeft: '2px solid #d2d2d2',
          color: '#6a6e73',
        }}
      >
        {args && (
          <div style={{ marginTop: '4px' }}>
            <strong>Arguments:</strong>
            <pre style={codeBlockStyle}>
              <code>
                {(() => {
                  try {
                    return JSON.stringify(JSON.parse(args), null, 2);
                  } catch {
                    return args;
                  }
                })()}
              </code>
            </pre>
          </div>
        )}
        {output && (
          <div style={{ marginTop: '4px' }}>
            <strong>Output:</strong>
            <pre style={codeBlockStyle}>
              <code>{output}</code>
            </pre>
          </div>
        )}
        {error && (
          <div style={{ marginTop: '4px', color: '#c9190b' }}>
            <strong>Error:</strong>
            <pre style={{ ...codeBlockStyle, background: '#ffe6e6' }}>
              <code>{error}</code>
            </pre>
          </div>
        )}
      </div>
    </ExpandableSection>
  );
};

interface TextContentProps {
  text: string;
  isMarkdown?: boolean;
}

export const TextContent: React.FC<TextContentProps> = ({ text, isMarkdown = false }) => {
  if (isMarkdown) {
    return (
      <div className="pf-v6-c-content">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      </div>
    );
  }
  return <div>{text}</div>;
};

interface ImageContentProps {
  imageUrl: string;
  alt?: string;
}

export const ImageContent: React.FC<ImageContentProps> = ({ imageUrl, alt = 'Image' }) => {
  return <img src={imageUrl} alt={alt} style={{ maxWidth: '100%', height: 'auto' }} />;
};

interface GraphNodeInfo {
  node_id: string;
  label: string;
  status: GraphNodeStatus;
}

interface GraphProgressTrackerProps {
  nodes: GraphNodeInfo[];
}

function stepVariant(status: GraphNodeStatus): 'success' | 'info' | 'pending' {
  switch (status) {
    case 'completed':
      return 'success';
    case 'running':
      return 'info';
    default:
      return 'pending';
  }
}

export const GraphProgressTracker: React.FC<GraphProgressTrackerProps> = ({ nodes }) => {
  if (nodes.length === 0) return null;

  return (
    <div style={{ marginBottom: '12px' }}>
      <ProgressStepper isVertical isCompact aria-label="Graph execution progress">
        {nodes.map((node) => (
          <ProgressStep
            key={node.node_id}
            variant={stepVariant(node.status)}
            isCurrent={node.status === 'running'}
            icon={
              node.status === 'running' ? (
                <Spinner size="sm" aria-label={`${node.label} running`} />
              ) : undefined
            }
            titleId={`graph-step-${node.node_id}`}
            aria-label={`${node.label}: ${node.status}`}
          >
            {node.label}
          </ProgressStep>
        ))}
      </ProgressStepper>
    </div>
  );
};

interface GraphNodeOutputSectionProps {
  nodeId: string;
  label: string;
  status: GraphNodeStatus;
  outputText: string;
}

const statusIcon = (s: GraphNodeStatus) => {
  if (s === 'completed')
    return (
      <span
        style={{
          color: 'var(--pf-v6-global--success-color--100, #3e8635)',
          marginRight: 6,
          fontSize: '0.9em',
        }}
      >
        ✓
      </span>
    );
  if (s === 'running') return <Spinner size="sm" style={{ marginRight: 6 }} aria-label="running" />;
  return <span style={{ color: '#d2d2d2', marginRight: 6, fontSize: '0.9em' }}>○</span>;
};

export const GraphNodeOutputSection: React.FC<GraphNodeOutputSectionProps> = ({
  nodeId: _nodeId,
  label,
  status,
  outputText,
}) => {
  const [isExpanded, setIsExpanded] = useState(status === 'running');

  const preview = outputText.length > 120 ? outputText.slice(0, 120).trimEnd() + '...' : outputText;

  const toggle = (
    <span style={{ display: 'inline-flex', alignItems: 'center' }}>
      {statusIcon(status)}
      {label}
    </span>
  );

  return (
    <ExpandableSection
      toggleContent={toggle}
      isExpanded={isExpanded}
      onToggle={(_event, expanded) => setIsExpanded(expanded)}
      isIndented
      displaySize="default"
    >
      <div
        style={{
          padding: '8px',
          borderLeft: '2px solid #d2d2d2',
        }}
      >
        {outputText ? (
          <div className="pf-v6-c-content" style={{ overflowX: 'auto', fontSize: '0.875rem' }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {isExpanded ? outputText : preview}
            </ReactMarkdown>
          </div>
        ) : (
          <div style={{ color: '#6a6e73', fontStyle: 'italic' }}>
            {status === 'running' ? 'Processing...' : 'Waiting...'}
          </div>
        )}
      </div>
    </ExpandableSection>
  );
};
