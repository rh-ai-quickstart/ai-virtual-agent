import { Agent, SamplingStrategy, ParameterFieldName } from './agent';
import { KnowledgeBase } from './knowledge-base';

export interface AgentFormProps {
  defaultAgentProps?: Agent | undefined;
  onSubmit: (values: Agent) => void;
  isSubmitting: boolean;
  onCancel: () => void;
}

// Form interface for internal form state (user-friendly)
export interface AgentFormData {
  name: string;
  model_name: string;
  prompt: string;
  knowledge_base_ids: string[];
  tool_ids: string[]; // Internal form uses tool IDs for easier UI handling
  sampling_strategy: SamplingStrategy;
  temperature: number;
  top_p: number;
  top_k: number;
  max_tokens: number;
  repetition_penalty: number;
  samplingAccordionExpanded: boolean; // Added for accordion state
  input_shields: string; // Single selection for form UI
  output_shields: string; // Single selection for form UI
}

export interface FormFieldProps {
  name: string;
  state: {
    value: number;
  };
  handleChange: (value: number) => void;
  handleBlur: () => void;
}

export interface FormFieldSliderProps {
  form: {
    Field: React.ComponentType<{
      name: ParameterFieldName;
      children: (field: FormFieldProps) => React.ReactNode;
    }>;
  };
  name: ParameterFieldName;
  label: string;
  helperText: string;
  min: number;
  max: number;
  step: number;
  handleSliderChange: (
    event: unknown,
    field: FormFieldProps,
    sliderValue: number,
    inputValue: number | undefined,
    range: { min: number; max: number; step: number },
    setLocalInputValue?: React.Dispatch<React.SetStateAction<number>>
  ) => void;
}

export interface ParameterField {
  name: ParameterFieldName;
  label: string;
  helperText: string;
  min: number;
  max: number;
  step: number;
  showWhen?: (strategy: string) => boolean;
}

export type KnowledgeBaseFormData = KnowledgeBase & {
  accordionExpanded: boolean; // Added for accordion state
};

export interface KnowledgeBaseFormProps {
  defaultKnowledgeBaseProps?: KnowledgeBase | undefined;
  onSubmit: (values: KnowledgeBase) => void;
  onCancel: () => void;
  isSubmitting: boolean;
}
