import { templateService } from './templates';

/**
 * Service for managing demo questions from deployed templates
 */
class DemoQuestionsService {
  /**
   * Get demo questions for a specific agent by its ID
   * @param _agentId The agent ID (currently unused, but kept for future implementation)
   * @returns Array of demo questions
   */
  async getQuestionsForAgent(_agentId: string): Promise<string[]> {
    try {
      // Get all templates to find which one contains this agent
      const templates = await templateService.getTemplates();

      for (const template of templates) {
        if (template.personas) {
          for (const [_personaKey, persona] of Object.entries(template.personas)) {
            for (const agent of persona.agents) {
              // Check if this agent matches the deployed agent
              // We can match by name since that's what we use in deployment
              if (agent.name) {
                // This is a simplified match - in a real implementation,
                // you might want to store the template ID in agent metadata
                return agent.demo_questions || [];
              }
            }
          }
        }
      }

      return [];
    } catch (error) {
      console.error('Error loading demo questions for agent:', error);
      return [];
    }
  }

  /**
   * Get demo questions for a specific template and persona
   * @param templateId The template ID
   * @param personaKey The persona key
   * @returns Array of demo questions
   */
  async getQuestionsForTemplateAndPersona(templateId: string, personaKey: string): Promise<string[]> {
    try {
      const templates = await templateService.getTemplates();
      const template = templates.find(t => t.id === templateId);
      
      if (template?.personas?.[personaKey]?.demo_questions) {
        return template.personas[personaKey].demo_questions;
      }
      
      return [];
    } catch (error) {
      console.error('Error loading demo questions for template and persona:', error);
      return [];
    }
  }

  /**
   * Get all demo questions for a template
   * @param templateId The template ID
   * @returns Object with persona keys and their demo questions
   */
  async getAllQuestionsForTemplate(templateId: string): Promise<Record<string, string[]>> {
    try {
      const templates = await templateService.getTemplates();
      const template = templates.find(t => t.id === templateId);
      
      if (!template?.personas) {
        return {};
      }
      
      const questions: Record<string, string[]> = {};
      for (const [personaKey, persona] of Object.entries(template.personas)) {
        if (persona.demo_questions) {
          questions[personaKey] = persona.demo_questions;
        }
      }
      
      return questions;
    } catch (error) {
      console.error('Error loading all demo questions for template:', error);
      return {};
    }
  }
}

// Export singleton instance
export const demoQuestionsService = new DemoQuestionsService(); 