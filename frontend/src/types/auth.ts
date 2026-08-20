export interface User {
  keycloak_id: string;
  email: string;
  username: string;
  role?: string;
  agent_ids?: string[];
}

export interface Shield {
  identifier: string;
  name?: string;
}
