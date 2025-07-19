interface PersonaMapping {
  [agentId: string]: { persona: string; templateId: string };
}

const PERSONA_STORAGE_KEY = 'agent-personas';

// Add caching to prevent redundant persona lookups
const personaCache = new Map<string, string>();
const templateIdCache = new Map<string, string>();

export const personaStorage = {
  // Save persona for an agent
  setPersona: (agentId: string, persona: string, templateId: string) => {
    const current = personaStorage.getAll();
    current[agentId] = { persona, templateId };
    localStorage.setItem(PERSONA_STORAGE_KEY, JSON.stringify(current));
    
    // Update caches
    personaCache.set(agentId, persona);
    templateIdCache.set(agentId, templateId);
    
    console.log(`Saved persona "${persona}" for agent ${agentId} from template ${templateId}`);
  },

  // Get persona for an agent
  getPersona: (agentId: string): string | null => {
    // Check cache first
    if (personaCache.has(agentId)) {
      return personaCache.get(agentId) || null;
    }
    
    // Check localStorage
    const current = personaStorage.getAll();
    const data = current[agentId];
    if (data?.persona) {
      personaCache.set(agentId, data.persona);
      return data.persona;
    }
    
    return null;
  },

  // Get template ID for an agent
  getTemplateId: (agentId: string): string | null => {
    // Check cache first
    if (templateIdCache.has(agentId)) {
      return templateIdCache.get(agentId) || null;
    }
    
    // Check localStorage
    const current = personaStorage.getAll();
    const data = current[agentId];
    if (data?.templateId) {
      templateIdCache.set(agentId, data.templateId);
      return data.templateId;
    }
    
    return null;
  },

  // Get all persona mappings
  getAll: (): PersonaMapping => {
    try {
      const stored = localStorage.getItem(PERSONA_STORAGE_KEY);
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  },

  // Remove persona for an agent
  removePersona: (agentId: string) => {
    const current = personaStorage.getAll();
    delete current[agentId];
    localStorage.setItem(PERSONA_STORAGE_KEY, JSON.stringify(current));
    
    // Clear caches
    personaCache.delete(agentId);
    templateIdCache.delete(agentId);
    
    console.log(`Removed persona for agent ${agentId}`);
  },

  // Clear all personas (for testing)
  clearAll: () => {
    localStorage.removeItem(PERSONA_STORAGE_KEY);
    personaCache.clear();
    templateIdCache.clear();
    console.log('Cleared all persona mappings');
  },

  // Initialize personas from agent metadata (called after deployment)
  initializeFromAgents: (agents: Array<{ id: string; metadata?: { template_id?: string; persona?: string } }>) => {
    agents.forEach(agent => {
      if (agent.metadata?.template_id && agent.metadata?.persona) {
        personaStorage.setPersona(
          agent.id, 
          agent.metadata.persona, 
          agent.metadata.template_id
        );
      }
    });
  }
};