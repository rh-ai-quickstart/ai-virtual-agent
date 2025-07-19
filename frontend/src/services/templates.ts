import { TemplateSuite } from '@/types/templates';
import { apiClient } from '@/config/api';
import baseUrl from '@/config/api'; // Import as default export

// Add request deduplication to prevent multiple simultaneous calls
let templatesPromise: Promise<TemplateSuite[]> | null = null;

export const templateService = {
  async getTemplates(): Promise<TemplateSuite[]> {
    // If there's already a request in progress, return that promise
    if (templatesPromise) {
      return templatesPromise;
    }
    
    templatesPromise = (async () => {
      try {
        console.log('Calling getTemplates...');
        console.log('Base URL:', baseUrl);
        console.log('Full URL:', `${baseUrl}/api/templates/`);
        
        // Test if backend is reachable
        try {
          const testResponse = await fetch(`${baseUrl}/docs`);
          console.log('Backend test response status:', testResponse.status);
          console.log('Backend test response ok:', testResponse.ok);
        } catch (testError) {
          console.error('Backend test failed:', testError);
        }
        
        const response = (await apiClient.get('/api/templates/')) as TemplateSuite[];
        console.log('Templates response:', response);
        console.log('Response type:', typeof response);
        console.log('Response length:', response?.length);
        return response || [];
      } catch (error) {
        console.error('Error fetching templates:', error);
        console.error('Error name:', error.name);
        console.error('Error message:', error.message);
        console.error('Error stack:', error.stack);
        
        // Add retry logic for network errors
        if (error.message?.includes('message channel closed') || error.name === 'TypeError') {
          console.warn('Network interruption detected, retrying...');
          // Retry once after a short delay
          await new Promise(resolve => setTimeout(resolve, 2000));
          try {
            const retryResponse = (await apiClient.get('/api/templates/')) as TemplateSuite[];
            return retryResponse || [];
          } catch (retryError) {
            console.error('Retry failed:', retryError);
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
      const response = await apiClient.get('/api/templates/categories');
      console.log('Categories response:', response);
      return response || [];
    } catch (error) {
      console.error('Error fetching categories:', error);
      return [];
    }
  },

  async deployTemplate(templateId: string, selectedAgents?: string[]): Promise<{ success: boolean; agent_ids?: string[]; deployed_agents?: any[]; error?: string }> {
    try {
      // Send request with selected agents if specified
      const requestBody = selectedAgents ? { selected_agents: selectedAgents } : {};
      const response = await apiClient.post(`/api/templates/${templateId}/deploy`, requestBody);
      return { 
        success: true, 
        agent_ids: response.deployed_agents?.map((agent: any) => agent.id) || [],
        deployed_agents: response.deployed_agents || []
      };
    } catch (error: any) {
      console.error('Error deploying template:', error);
      return { success: false, error: error.message || 'Deployment failed' };
    }
  }
}; 