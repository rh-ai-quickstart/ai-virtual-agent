import { TemplateSuite } from '@/types/templates';
import { apiClient } from '@/config/api';

// Add request deduplication to prevent multiple simultaneous calls
let templatesPromise: Promise<TemplateSuite[]> | null = null;

// Production logging utility
const logger = {
  info: (message: string, ...args: unknown[]) => {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[INFO] ${message}`, ...args);
    }
  },
  error: (message: string, error?: unknown) => {
    if (process.env.NODE_ENV === 'development') {
      console.error(`[ERROR] ${message}`, error);
    }
    // In production, send to error tracking service
  },
  warn: (message: string, ...args: unknown[]) => {
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[WARN] ${message}`, ...args);
    }
  },
};

export const templateService = {
  async getTemplates(): Promise<TemplateSuite[]> {
    // If there's already a request in progress, return that promise
    if (templatesPromise) {
      return templatesPromise;
    }

    templatesPromise = (async () => {
      try {
        logger.info('Fetching templates from API');

        const response = (await apiClient.get('/api/templates/')) as TemplateSuite[];
        logger.info(`Retrieved ${response?.length || 0} templates`);
        return response || [];
      } catch (error) {
        logger.error('Error fetching templates:', error);

        // Add retry logic for network errors
        if (
          error instanceof Error &&
          (error.message?.includes('message channel closed') || error.name === 'TypeError')
        ) {
          logger.warn('Network interruption detected, retrying...');
          // Retry once after a short delay
          await new Promise((resolve) => setTimeout(resolve, 2000));
          try {
            const retryResponse = (await apiClient.get('/api/templates/')) as TemplateSuite[];
            return retryResponse || [];
          } catch (retryError) {
            logger.error('Retry failed:', retryError);
            return [];
          }
        }
        return [];
      } finally {
        templatesPromise = null; // Clear the promise when done
      }
    })();

    return templatesPromise;
  },

  async getCategories(): Promise<string[]> {
    try {
      const templates = await this.getTemplates();
      const categories = new Set<string>();

      templates.forEach((template) => {
        if (template.category) {
          categories.add(template.category);
        }
      });

      return Array.from(categories);
    } catch (error) {
      logger.error('Error fetching categories:', error);
      return [];
    }
  },

  async deployTemplate(
    templateId: string,
    selectedAgents?: string[]
  ): Promise<{
    success: boolean;
    agent_ids?: string[];
    deployed_agents?: Array<{ id: string; name: string; metadata?: { persona?: string } }>;
    error?: string;
  }> {
    try {
      logger.info(
        `Deploying template ${templateId} with ${selectedAgents?.length || 'all'} agents`
      );

      const response = (await apiClient.post(`/api/templates/${templateId}/deploy`, {
        selected_agents: selectedAgents,
      })) as {
        deployed_agents: Array<{ id: string; name: string; metadata?: { persona?: string } }>;
        failed_agents: Array<{ name: string; error: string }>;
        template_id: string;
        deployment_summary: {
          template_id: string;
          template_name: string;
          total_agents: number;
          successful_deployments: number;
          failed_deployments: number;
          deployment_time: string;
          success_rate: number;
        };
      };

      // Convert backend response to frontend expected format
      const success = response.failed_agents.length === 0;
      const agent_ids = response.deployed_agents.map((agent) => agent.id);

      logger.info(`Template deployment ${success ? 'succeeded' : 'failed'}`);

      return {
        success,
        agent_ids,
        deployed_agents: response.deployed_agents,
        error: success ? undefined : `Failed to deploy ${response.failed_agents.length} agents`,
      };
    } catch (error) {
      logger.error('Error deploying template:', error);
      throw error;
    }
  },
};
