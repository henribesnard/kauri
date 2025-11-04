// User types
export interface User {
  id: string;
  email: string;
  full_name: string;
  company_name?: string;
  role?: string;
  is_active: boolean;
  created_at: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  company_name?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// Transaction types
export interface Transaction {
  id: string;
  type: 'vente' | 'achat';
  client: string;
  amount: number;
  status: 'validé' | 'en attente';
  date: string;
}

// KPI types
export interface KPI {
  title: string;
  value: string;
  change: string;
  trend: 'up' | 'down';
}

// Task types
export interface Task {
  id: string;
  title: string;
  priority: 'urgent' | 'moyen' | 'faible';
  urgentCount?: number;
}

// Chatbot types
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export interface ChatQueryRequest {
  query: string;
  session_id?: string;
}

export interface ChatQueryResponse {
  response: string;
  session_id: string;
  sources?: string[];
}
