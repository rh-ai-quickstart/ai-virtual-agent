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
// Note: Demo questions are now loaded from template YAML files to avoid hard-coding
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
  }
  // Demo questions removed - now loaded from template YAML files
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

  getDemoQuestions(_personaType: string): string[] {
    // Demo questions are now loaded from template YAML files via demoQuestionsService
    // This method is kept for backward compatibility but returns empty array
    // Use demoQuestionsService.getQuestionsForTemplateAndPersona() instead
    console.warn('getDemoQuestions() is deprecated. Use demoQuestionsService instead.');
    return [];
  }
}

export const personaService = new PersonaService(); 