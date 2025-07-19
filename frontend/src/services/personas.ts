import { 
  ShieldAltIcon,
  DollarSignIcon,
  UserIcon,
  EyeIcon,
  BookIcon,
  CogIcon,
  ChatIcon
} from '@patternfly/react-icons';

// Icon mapping for dynamic imports
const ICON_MAP: Record<string, React.ComponentType> = {
  ShieldAltIcon,
  DollarSignIcon,
  UserIcon,
  EyeIcon,
  BookIcon,
  CogIcon,
  ChatIcon
};

export interface PersonaConfig {
  label: string;
  description: string;
  icon: string;
  color: 'red' | 'green' | 'blue' | 'orange' | 'purple' | 'grey';
  className: string;
  avatarBg: string;
  avatarIcon: string;
  gradient: string;
  borderColor: string;
}

export interface PersonasConfig {
  personas: Record<string, PersonaConfig>;
  default: PersonaConfig;
  demo_questions?: Record<string, string[]>;
}

// Default persona configuration (fallback if YAML loading fails)
const DEFAULT_PERSONAS_CONFIG: PersonasConfig = {
  personas: {
    compliance_officer: {
      label: "Compliance Officer",
      description: "Ensures adherence to banking regulations and compliance procedures",
      icon: "ShieldAltIcon",
      color: "red",
      className: "persona-compliance",
      avatarBg: "#dc2626",
      avatarIcon: "🛡️",
      gradient: "linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)",
      borderColor: "#dc2626"
    },
    relationship_manager: {
      label: "Relationship Manager",
      description: "Handles lending requests and credit assessment",
      icon: "DollarSignIcon",
      color: "green",
      className: "persona-lending",
      avatarBg: "#059669",
      avatarIcon: "💰",
      gradient: "linear-gradient(135deg, #059669 0%, #047857 100%)",
      borderColor: "#059669"
    },
    branch_teller: {
      label: "Customer Service",
      description: "Assists with customer queries and account services",
      icon: "UserIcon",
      color: "blue",
      className: "persona-customer",
      avatarBg: "#2563eb",
      avatarIcon: "👥",
      gradient: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
      borderColor: "#2563eb"
    },
    fraud_analyst: {
      label: "Fraud Analyst",
      description: "Reviews alerts and investigates suspicious activities",
      icon: "EyeIcon",
      color: "orange",
      className: "persona-fraud",
      avatarBg: "#ea580c",
      avatarIcon: "🔍",
      gradient: "linear-gradient(135deg, #ea580c 0%, #c2410c 100%)",
      borderColor: "#ea580c"
    },
    training_lead: {
      label: "Training Lead",
      description: "Keeps staff current on regulations and certifications",
      icon: "BookIcon",
      color: "purple",
      className: "persona-training",
      avatarBg: "#7c3aed",
      avatarIcon: "📚",
      gradient: "linear-gradient(135deg, #7c3aed 0%, #6d28d9 100%)",
      borderColor: "#7c3aed"
    },
    it_support: {
      label: "IT Support",
      description: "Provides technical support for banking operations",
      icon: "CogIcon",
      color: "grey",
      className: "persona-it",
      avatarBg: "#6b7280",
      avatarIcon: "⚙️",
      gradient: "linear-gradient(135deg, #6b7280 0%, #4b5563 100%)",
      borderColor: "#6b7280"
    }
  },
  default: {
    label: "AI Assistant",
    description: "General purpose AI assistant",
    icon: "CogIcon",
    color: "grey",
    className: "persona-default",
    avatarBg: "#6b7280",
    avatarIcon: "🤖",
    gradient: "linear-gradient(135deg, #6b7280 0%, #4b5563 100%)",
    borderColor: "#6b7280"
  },
  demo_questions: {
    default: [
      "What can you help me with today?",
      "How do I get started with this assistant?",
      "What are your capabilities?",
      "Can you explain your role and responsibilities?"
    ],
    compliance_officer: [
      "What are the current BSA/AML reporting requirements for cash transactions over $10,000?",
      "How do I handle a customer who appears on the OFAC sanctions list?",
      "What are the CFPB requirements for mortgage loan disclosures?",
      "What's the process for filing a Suspicious Activity Report (SAR)?"
    ],
    relationship_manager: [
      "What documentation is required for a small business loan application?",
      "How do I assess credit risk for a new commercial client?",
      "What are the current FHA loan limits and requirements?",
      "How do I calculate debt-to-income ratios for loan approval?"
    ],
    branch_teller: [
      "What are the daily withdrawal limits for different account types?",
      "How do I handle a customer reporting a lost or stolen card?",
      "What's the process for opening a new business account?",
      "How do I verify customer identity for large transactions?"
    ],
    fraud_analyst: [
      "What are the red flags for potential money laundering?",
      "How do I investigate suspicious transaction patterns?",
      "What's the escalation process for high-risk alerts?",
      "How do I determine if a transaction requires CTR filing?"
    ],
    training_lead: [
      "What are the latest regulatory changes affecting our operations?",
      "What certifications are required for compliance officers?",
      "How do I stay updated on industry best practices?",
      "What training is required for new AML regulations?"
    ],
    it_support: [
      "How do I reset a user's password in the banking system?",
      "What's the process for granting system access to new employees?",
      "How do I troubleshoot login issues with the core banking platform?",
      "What security protocols should I follow for remote access?"
    ]
  }
};

class PersonaService {
  private config: PersonasConfig = DEFAULT_PERSONAS_CONFIG;
  private loaded = false;

  async loadConfig(): Promise<void> {
    try {
      // In a real implementation, you'd fetch this from an API endpoint
      // For now, we'll use the default config
      this.config = DEFAULT_PERSONAS_CONFIG;
      this.loaded = true;
    } catch (error) {
      console.warn('Failed to load persona config, using defaults:', error);
      this.config = DEFAULT_PERSONAS_CONFIG;
      this.loaded = true;
    }
  }

  getPersona(personaId: string): PersonaConfig {
    if (!this.loaded) {
      this.loadConfig();
    }
    return this.config.personas[personaId] || this.config.default;
  }

  getAllPersonas(): Record<string, PersonaConfig> {
    if (!this.loaded) {
      this.loadConfig();
    }
    return this.config.personas;
  }

  getIcon(iconName: string): React.ComponentType {
    return ICON_MAP[iconName] || CogIcon;
  }

  isLoaded(): boolean {
    return this.loaded;
  }

  getDemoQuestions(personaType: string): string[] {
    try {
      const personas = this.config.personas as Record<string, any>;
      const demoQuestions = this.config.demo_questions as Record<string, string[]>;
      
      if (demoQuestions && demoQuestions[personaType]) {
        return demoQuestions[personaType];
      }
      
      return [];
    } catch (error) {
      console.error('Error loading demo questions:', error);
      return [];
    }
  }
}

export const personaService = new PersonaService(); 