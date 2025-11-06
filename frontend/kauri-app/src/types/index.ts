// User types
export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name?: string;
  company_name?: string;
  role?: string;
  is_active?: boolean;
  created_at?: string;
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
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  created_at?: string;
  sources?: Array<{
    title: string;
    score: number;
  }>;
  metadata?: Record<string, any>;
  user_feedback?: {
    rating: 'positive' | 'negative';
    comment?: string;
    feedback_at: string;
  };
}

export interface Conversation {
  id: string;
  user_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  is_archived: boolean;
  metadata?: Record<string, any>;
  message_count?: number;
  messages?: ChatMessage[];
}

export interface ConversationTag {
  id: string;
  conversation_id: string;
  tag: string;
  created_at: string;
}

export interface ConversationListResponse {
  conversations: Conversation[];
  total: number;
}

export interface ConversationStatsResponse {
  total_conversations: number;
  active_conversations: number;
  archived_conversations: number;
  total_messages: number;
}

export interface ChatQueryRequest {
  query: string;
  conversation_id?: string;
  user_settings?: Record<string, any>;
}

export interface ChatQueryResponse {
  response: string;
  conversation_id: string;
  message_id?: string;
  sources?: Array<{
    title: string;
    score: number;
  }>;
  metadata?: {
    model?: string;
    tokens?: number;
    latency_ms?: number;
    intent?: string;
  };
}

export interface CreateConversationRequest {
  title?: string;
  metadata?: Record<string, any>;
}

export interface UpdateConversationRequest {
  title?: string;
  is_archived?: boolean;
  metadata?: Record<string, any>;
}

// Message Feedback types
export interface MessageFeedbackRequest {
  rating: 'positive' | 'negative';
  comment?: string;
}

// Conversation Context Info types
export interface ConversationContextInfo {
  total_tokens: number;
  max_tokens: number;
  warning_threshold_tokens: number;
  is_over_limit: boolean;
  is_near_limit: boolean;
  usage_percentage: number;
  messages_included: number;
}
