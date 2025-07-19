# Adding New Templates to AI Virtual Agent

This guide explains how to add new templates with agents and demo questions to the AI Virtual Agent system.

## Overview

Templates are YAML configuration files that define pre-configured agent suites for different business domains. Each template contains:
- Template metadata (name, description, category)
- Personas with their configurations
- Agents with their prompts, tools, and settings
- Demo questions for each persona and agent

## Quick Start

To add a new template, you only need to create **one file**:
```
templates/your_template_name.yaml
```

## Step-by-Step Guide

### 1. Create the Template YAML File

Create a new file in the `templates/` directory following this structure:

```yaml
id: "your_template_id"
name: "Your Template Name"
description: "Description of what this template provides"
category: "your_category"
metadata:
  success_rate: 95
  deployment_time: "2 minutes"
  agent_count: 5
  features:
    - "Feature 1"
    - "Feature 2"
    - "Feature 3"

personas:
  persona_key_1:
    label: "Persona Label 1"
    description: "Description of this persona"
    icon: "IconName"
    color: "blue"
    className: "persona-custom"
    avatarBg: "#2563eb"
    avatarIcon: "🔧"
    gradient: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)"
    borderColor: "#2563eb"
    demo_questions:
      - "What is the first demo question for this persona?"
      - "What is the second demo question for this persona?"
      - "What is the third demo question for this persona?"
      - "What is the fourth demo question for this persona?"
    agents:
      - name: "Agent Name 1"
        description: "Description of this agent"
        prompt: "You are a [role] for [organization]. You help with [specific tasks]..."
        model_name: "meta-llama/Llama-3.1-8B-Instruct"
        tools:
          - toolgroup_id: "builtin::websearch"
        knowledge_base_ids: []
        temperature: 0.1
        repetition_penalty: 1.0
        max_tokens: 4096
        top_p: 0.95
        max_infer_iters: 10
        input_shields: []
        output_shields: []
        demo_questions:
          - "Agent-specific demo question 1"
          - "Agent-specific demo question 2"
          - "Agent-specific demo question 3"
          - "Agent-specific demo question 4"

  persona_key_2:
    label: "Persona Label 2"
    description: "Description of this persona"
    icon: "IconName"
    color: "green"
    className: "persona-custom"
    avatarBg: "#059669"
    avatarIcon: "💰"
    gradient: "linear-gradient(135deg, #059669 0%, #047857 100%)"
    borderColor: "#059669"
    demo_questions:
      - "Demo question for persona 2"
      - "Another demo question for persona 2"
      - "Third demo question for persona 2"
      - "Fourth demo question for persona 2"
    agents:
      - name: "Agent Name 2"
        description: "Description of this agent"
        prompt: "You are a [role] for [organization]. You help with [specific tasks]..."
        model_name: "meta-llama/Llama-3.1-8B-Instruct"
        tools:
          - toolgroup_id: "builtin::websearch"
        knowledge_base_ids: []
        temperature: 0.1
        repetition_penalty: 1.0
        max_tokens: 4096
        top_p: 0.95
        max_infer_iters: 10
        input_shields: []
        output_shields: []
        demo_questions:
          - "Agent 2 specific demo question 1"
          - "Agent 2 specific demo question 2"
          - "Agent 2 specific demo question 3"
          - "Agent 2 specific demo question 4"
```

### 2. Template Configuration Details

#### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | string | Unique template identifier | `"fsi_banking"` |
| `name` | string | Display name for the template | `"Financial Services & Banking"` |
| `description` | string | Template description | `"Complete banking foundation..."` |
| `category` | string | Template category | `"banking"`, `"healthcare"`, `"insurance"` |
| `metadata.success_rate` | number | Success rate percentage | `95` |
| `metadata.deployment_time` | string | Estimated deployment time | `"2 minutes"` |
| `metadata.agent_count` | number | Total number of agents | `6` |
| `metadata.features` | array | List of key features | `["Customer Support", "Compliance"]` |

#### Persona Configuration

Each persona represents a role or department and contains:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `label` | string | Display name for the persona | `"Compliance Officer"` |
| `description` | string | Persona description | `"Ensures regulatory compliance..."` |
| `icon` | string | Icon name (PatternFly icons) | `"ShieldAltIcon"` |
| `color` | string | Color theme | `"red"`, `"blue"`, `"green"`, `"orange"`, `"purple"`, `"grey"` |
| `className` | string | CSS class name | `"persona-compliance"` |
| `avatarBg` | string | Avatar background color | `"#dc2626"` |
| `avatarIcon` | string | Avatar emoji | `"🛡️"` |
| `gradient` | string | CSS gradient | `"linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)"` |
| `borderColor` | string | Border color | `"#dc2626"` |
| `demo_questions` | array | List of demo questions | `["Question 1", "Question 2"]` |

#### Agent Configuration

Each agent within a persona contains:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | string | Agent name | `"BSA/AML Specialist"` |
| `description` | string | Agent description | `"Handles compliance..."` |
| `prompt` | string | Agent system prompt | `"You are a [role]..."` |
| `model_name` | string | LLM model to use | `"meta-llama/Llama-3.1-8B-Instruct"` |
| `tools` | array | List of tools | `[{"toolgroup_id": "builtin::websearch"}]` |
| `knowledge_base_ids` | array | Knowledge base IDs | `[]` |
| `temperature` | number | LLM temperature | `0.1` |
| `repetition_penalty` | number | Repetition penalty | `1.0` |
| `max_tokens` | number | Max response tokens | `4096` |
| `top_p` | number | Top-p sampling | `0.95` |
| `max_infer_iters` | number | Max inference iterations | `10` |
| `input_shields` | array | Input safety filters | `[]` |
| `output_shields` | array | Output safety filters | `[]` |
| `demo_questions` | array | Agent-specific questions | `["Question 1", "Question 2"]` |

### 3. Available Icons

Use PatternFly React icons. Common icons include:
- `ShieldAltIcon` - Security/Compliance
- `UserIcon` - Customer Service
- `DollarSignIcon` - Finance/Lending
- `EyeIcon` - Fraud Detection
- `BookIcon` - Training/Education
- `CogIcon` - IT Support
- `FileTextIcon` - Documentation
- `BuildingIcon` - Provider Relations
- `BriefcaseIcon` - Operations
- `CalculatorIcon` - Underwriting

### 4. Color Schemes

Available colors and their hex values:

| Color | Hex Value | Use Case |
|-------|-----------|----------|
| `red` | `#dc2626` | Compliance, Security |
| `blue` | `#2563eb` | Customer Service, Documentation |
| `green` | `#059669` | Finance, Lending |
| `orange` | `#ea580c` | Operations, Support |
| `purple` | `#7c3aed` | Provider Relations, Specialized |
| `grey` | `#6b7280` | IT Support, General |

### 5. Optional: Add Category Styling

If you want custom styling for your template category, add it to `frontend/src/components/template-card.tsx`:

```typescript
const CATEGORY_STYLES: Record<string, { 
  color: 'red' | 'green' | 'blue' | 'orange' | 'purple' | 'grey';
  bgColor: string;
  borderColor: string;
}> = {
  // ... existing styles ...
  'your_category': { 
    color: 'purple', 
    bgColor: 'var(--pf-v6-global--palette--purple-50)',
    borderColor: 'var(--pf-v6-global--palette--purple-200)'
  },
};
```

## Best Practices

### 1. Template Naming
- Use descriptive, lowercase IDs with underscores: `fsi_banking`, `healthcare_operations`
- Use clear, professional names: `"Financial Services & Banking"`
- Keep descriptions concise but informative

### 2. Agent Prompts
- Start with "You are a [role] for [organization]"
- Include specific responsibilities and knowledge areas
- Mention relevant regulations, tools, or procedures
- Keep prompts focused and professional

### 3. Demo Questions
- Make questions realistic and industry-specific
- Include common scenarios users would encounter
- Use proper terminology and industry language
- Provide 4 questions per persona/agent
- Questions should be actionable and specific

### 4. Persona Organization
- Group related agents under logical personas
- Use consistent naming patterns
- Ensure personas represent real organizational roles
- Keep persona descriptions clear and concise

### 5. Configuration Values
- Use consistent values across similar agents
- Temperature: 0.1 for consistent responses
- Max tokens: 4096 for comprehensive responses
- Top-p: 0.95 for balanced creativity/consistency

## Example: Complete Template

Here's a complete example of a banking template:

```yaml
id: "fsi_banking"
name: "Financial Services & Banking"
description: "Complete banking foundation with customer service, lending, and fraud prevention capabilities"
category: "banking"
metadata:
  success_rate: 95
  deployment_time: "2 minutes"
  agent_count: 6
  features:
    - "Customer Support"
    - "Loan Processing"
    - "Fraud Detection"
    - "Account Management"
    - "Compliance"
    - "IT Support"

personas:
  compliance_officer:
    label: "Compliance Officer"
    description: "Ensures adherence to banking regulations and compliance procedures"
    icon: "ShieldAltIcon"
    color: "red"
    className: "persona-compliance"
    avatarBg: "#dc2626"
    avatarIcon: "🛡️"
    gradient: "linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)"
    borderColor: "#dc2626"
    demo_questions:
      - "What are the current BSA/AML reporting requirements for cash transactions over $10,000?"
      - "How do I handle a customer who appears on the OFAC sanctions list?"
      - "What are the CFPB requirements for mortgage loan disclosures?"
      - "What's the process for filing a Suspicious Activity Report (SAR)?"
    agents:
      - name: "BSA/AML Specialist"
        description: "Handles Bank Secrecy Act and Anti-Money Laundering compliance"
        prompt: "You are a BSA/AML Specialist for a US bank. You help ensure compliance with Bank Secrecy Act regulations, including CTR filing, SAR reporting, and customer due diligence. You provide guidance on suspicious activity detection and regulatory reporting requirements."
        model_name: "meta-llama/Llama-3.1-8B-Instruct"
        tools:
          - toolgroup_id: "builtin::websearch"
        knowledge_base_ids: []
        temperature: 0.1
        repetition_penalty: 1.0
        max_tokens: 4096
        top_p: 0.95
        max_infer_iters: 10
        input_shields: []
        output_shields: []
        demo_questions:
          - "What are the current BSA/AML reporting requirements for cash transactions over $10,000?"
          - "How do I handle a customer who appears on the OFAC sanctions list?"
          - "What's the process for filing a Suspicious Activity Report (SAR)?"
          - "What are the red flags for suspicious activity in customer transactions?"
```

## Testing Your Template

### 1. Backend Testing
```bash
# Test template loading
curl -s http://localhost:8000/api/templates/ | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Found {len(data)} templates:'); [print(f'  - {t[\"id\"]}: {t[\"name\"]}') for t in data]"

# Test specific template
curl -s http://localhost:8000/api/templates/your_template_id | python3 -m json.tool
```

### 2. Frontend Testing
1. Hard refresh your browser (`Ctrl+F5` or `Cmd+Shift+R`)
2. Navigate to the Templates page
3. Verify your template appears with correct styling
4. Test deploying agents from your template

### 3. Debug Endpoint
```bash
# Get detailed template loading information
curl -s http://localhost:8000/api/templates/debug | python3 -m json.tool
```

## Troubleshooting

### Template Not Appearing
1. **Check file location**: Ensure file is in `templates/` directory
2. **Verify YAML syntax**: Use a YAML validator
3. **Check backend logs**: Look for validation errors
4. **Restart backend**: `pkill -f uvicorn && cd backend && python -m uvicorn backend.main:app --reload`
5. **Clear frontend cache**: Hard refresh browser or clear React Query cache

### Validation Errors
1. **Missing required fields**: Ensure all required fields are present
2. **Invalid YAML syntax**: Check for indentation and formatting issues
3. **Invalid agent configuration**: Verify all agent fields are correct
4. **Duplicate IDs**: Ensure template ID is unique

### Frontend Issues
1. **Cache issues**: Clear browser cache and React Query cache
2. **Styling issues**: Check if category styling is added correctly
3. **API errors**: Verify backend is running and accessible

## File Structure

```
templates/
├── fsi_banking.yaml              # Banking template
├── healthcare_operations.yaml     # Healthcare template
├── insurance_operations.yaml      # Insurance template
└── your_new_template.yaml        # Your new template
```

## What Happens Automatically

Once you create a template YAML file:

 **Template Discovery**: Backend automatically discovers new templates
 **API Endpoints**: `/api/templates/` includes your template
 **Frontend Display**: Template appears in UI automatically
 **Demo Questions**: Questions load from template personas
 **Agent Deployment**: Users can deploy agents from your template
 **Persona Mapping**: Personas are mapped when agents are deployed

## Summary

To add a new template:
1. **Create one file**: `templates/your_template.yaml`
2. **Follow the YAML structure** shown above
3. **Test the template** using the provided commands
4. **Refresh the frontend** to see your template

The system is fully template-driven with zero hard-coded configurations! 