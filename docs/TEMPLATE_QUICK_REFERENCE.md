# Template Quick Reference

## Quick Start
1. Create `templates/your_template.yaml`
2. Follow the YAML structure below
3. Test with: `curl -s http://localhost:8000/api/templates/`
4. Refresh frontend to see your template

## Basic Template Structure

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

personas:
  persona_key:
    label: "Persona Label"
    description: "Description of this persona"
    icon: "IconName"
    color: "blue"
    className: "persona-custom"
    avatarBg: "#2563eb"
    avatarIcon: "🔧"
    gradient: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)"
    borderColor: "#2563eb"
    demo_questions:
      - "Demo question 1"
      - "Demo question 2"
      - "Demo question 3"
      - "Demo question 4"
    agents:
      - name: "Agent Name"
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
          - "Agent-specific question 1"
          - "Agent-specific question 2"
          - "Agent-specific question 3"
          - "Agent-specific question 4"
```

## Required Fields

| Field | Required | Example |
|-------|----------|---------|
| `id` |  | `"fsi_banking"` |
| `name` |  | `"Financial Services & Banking"` |
| `description` |  | `"Complete banking foundation..."` |
| `category` |  | `"banking"` |
| `metadata.success_rate` |  | `95` |
| `metadata.deployment_time` |  | `"2 minutes"` |
| `metadata.agent_count` |  | `6` |
| `metadata.features` |  | `["Feature 1", "Feature 2"]` |

## Available Icons
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

## Available Colors
- `red` - Compliance, Security
- `blue` - Customer Service, Documentation
- `green` - Finance, Lending
- `orange` - Operations, Support
- `purple` - Provider Relations, Specialized
- `grey` - IT Support, General

## Testing Commands

```bash
# List all templates
curl -s http://localhost:8000/api/templates/ | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Found {len(data)} templates:'); [print(f'  - {t[\"id\"]}: {t[\"name\"]}') for t in data]"

# Test specific template
curl -s http://localhost:8000/api/templates/your_template_id | python3 -m json.tool

# Debug template loading
curl -s http://localhost:8000/api/templates/debug | python3 -m json.tool
```

## Troubleshooting

### Template Not Appearing
1. Check file is in `templates/` directory
2. Verify YAML syntax
3. Restart backend: `pkill -f uvicorn && cd backend && python -m uvicorn backend.main:app --reload`
4. Hard refresh frontend: `Ctrl+F5`

### Common Errors
- **Missing required fields**: Ensure all required fields are present
- **Invalid YAML**: Check indentation and syntax
- **Duplicate ID**: Ensure template ID is unique
- **Cache issues**: Clear browser cache and React Query cache

## Best Practices

### Naming
- Use lowercase with underscores: `fsi_banking`
- Clear, professional names: `"Financial Services & Banking"`

### Prompts
- Start with "You are a [role] for [organization]"
- Include specific responsibilities
- Mention relevant regulations/tools

### Questions
- Make questions realistic and industry-specific
- Use proper terminology
- Provide 4 questions per persona/agent

### Configuration
- Temperature: 0.1 (consistent responses)
- Max tokens: 4096 (comprehensive responses)
- Top-p: 0.95 (balanced creativity)

## What Happens Automatically

 Template appears in UI
 Demo questions load from template
 Agents can be deployed from template
 Personas are mapped when deployed
 No code changes required

## File Location
```
templates/your_template.yaml
```

That's it! Just one file to add a complete template with agents and demo questions. 