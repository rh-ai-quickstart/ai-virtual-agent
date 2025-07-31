export interface User {
  id: string;
  email: string;
  username: string;
  role?: string;
  agent_ids?: string[];
  created_at: string;
  updated_at: string;
}

export interface Shield {
  identifier: string;
  name?: string;
}

export interface UserContextType {
  user: User | null;
  setUser: (user: User | null) => void;
  logout: () => void;
  loading: boolean;
}

export interface UserProviderProps {
  children: React.ReactNode;
}
