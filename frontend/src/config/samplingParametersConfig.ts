export const parameterFields = [
  {
    name: 'temperature',
    label: 'Temperature',
    helperText:
      'Controls the randomness of the output. Lower values make the model more deterministic, while higher values increase creativity.',
    min: 0.0,
    max: 2.0,
    step: 0.1,
    showWhen: (strategy: string) => ['top-p', 'top-k'].includes(strategy),
  },
  {
    name: 'top_p',
    label: 'Top-P',
    helperText:
      'Selects the next token from the smallest set of tokens whose cumulative probability exceeds the Top-P value.',
    min: 0.0,
    max: 1.0,
    step: 0.05,
    showWhen: (strategy: string) => strategy === 'top-p',
  },
  {
    name: 'top_k',
    label: 'Top-K',
    helperText: "Restricts the model's choices to the K most likely next tokens at each step.",
    min: 0,
    max: 100,
    step: 1,
    showWhen: (strategy: string) => strategy === 'top-k',
  },
  {
    name: 'max_tokens',
    label: 'Max Tokens',
    helperText: 'The maximum number of tokens to generate in the response.',
    min: 0,
    max: 4096,
    step: 64,
  },
  {
    name: 'repetition_penalty',
    label: 'Repetition Penalty',
    helperText:
      'Penalizes tokens based on whether they have already appeared in the text, encouraging the model to introduce new topics. A value of 0 means no penalty.',
    min: -2.0,
    max: 2.0,
    step: 0.1,
    showWhen: () => false,
  },
];
