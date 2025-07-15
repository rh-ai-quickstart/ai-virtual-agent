interface PersonaMapping {
  [agentId: string]: string;
}

const PERSONA_STORAGE_KEY = 'agent-personas';

export const personaStorage = {
  // Save persona for an agent
  setPersona: (agentId: string, persona: string) => {
    const current = personaStorage.getAll();
    current[agentId] = persona;
    localStorage.setItem(PERSONA_STORAGE_KEY, JSON.stringify(current));
    console.log(`Saved persona "${persona}" for agent ${agentId}`);
  },

  // Get persona for an agent
  getPersona: (agentId: string): string | null => {
    const current = personaStorage.getAll();
    const persona = current[agentId] || null;
    console.log(`Retrieved persona "${persona}" for agent ${agentId}`);
    return persona;
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
    console.log(`Removed persona for agent ${agentId}`);
  },

  // Clear all personas (for testing)
  clearAll: () => {
    localStorage.removeItem(PERSONA_STORAGE_KEY);
    console.log('Cleared all persona mappings');
  }
};