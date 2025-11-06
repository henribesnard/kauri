import axios from 'axios';
import type {
  Conversation,
  ConversationListResponse,
  ConversationStatsResponse,
  CreateConversationRequest,
  UpdateConversationRequest,
  ChatMessage,
  MessageFeedbackRequest,
  ConversationContextInfo,
} from '../types';

const CHATBOT_SERVICE_URL = import.meta.env.VITE_CHATBOT_SERVICE_URL || 'http://localhost:3202';

// Create axios instance for chatbot service (different from main API)
const chatbotApiClient = axios.create({
  baseURL: CHATBOT_SERVICE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token interceptor
chatbotApiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
chatbotApiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const conversationService = {
  /**
   * List all conversations for the current user
   */
  async listConversations(
    includeArchived: boolean = false,
    limit: number = 50,
    offset: number = 0
  ): Promise<ConversationListResponse> {
    const params = new URLSearchParams({
      include_archived: includeArchived.toString(),
      limit: limit.toString(),
      offset: offset.toString(),
    });

    const response = await chatbotApiClient.get<ConversationListResponse>(
      `/api/v1/conversations?${params.toString()}`
    );

    return response.data;
  },

  /**
   * Get a specific conversation with its messages
   */
  async getConversation(conversationId: string): Promise<Conversation> {
    const response = await chatbotApiClient.get<Conversation>(
      `/api/v1/conversations/${conversationId}`
    );

    return response.data;
  },

  /**
   * Create a new conversation
   */
  async createConversation(data: CreateConversationRequest = {}): Promise<Conversation> {
    const response = await chatbotApiClient.post<Conversation>(
      `/api/v1/conversations`,
      data
    );

    return response.data;
  },

  /**
   * Update a conversation (title, archive status, metadata)
   */
  async updateConversation(
    conversationId: string,
    data: UpdateConversationRequest
  ): Promise<Conversation> {
    const response = await chatbotApiClient.patch<Conversation>(
      `/api/v1/conversations/${conversationId}`,
      data
    );

    return response.data;
  },

  /**
   * Delete a conversation
   */
  async deleteConversation(conversationId: string): Promise<void> {
    await chatbotApiClient.delete(
      `/api/v1/conversations/${conversationId}`
    );
  },

  /**
   * Get messages from a conversation
   */
  async getMessages(conversationId: string, limit?: number): Promise<ChatMessage[]> {
    const params = limit ? `?limit=${limit}` : '';
    const response = await chatbotApiClient.get<{ messages: ChatMessage[] }>(
      `/api/v1/conversations/${conversationId}/messages${params}`
    );

    // Convert created_at strings to Date objects
    return response.data.messages.map(msg => ({
      ...msg,
      timestamp: new Date(msg.timestamp || new Date()),
    }));
  },

  /**
   * Delete a message (soft delete)
   */
  async deleteMessage(conversationId: string, messageId: string): Promise<void> {
    await chatbotApiClient.delete(
      `/api/v1/conversations/${conversationId}/messages/${messageId}`
    );
  },

  /**
   * Add tags to a conversation
   */
  async addTags(conversationId: string, tags: string[]): Promise<void> {
    await chatbotApiClient.post(
      `/api/v1/conversations/${conversationId}/tags`,
      { tags }
    );
  },

  /**
   * Remove a tag from a conversation
   */
  async removeTag(conversationId: string, tag: string): Promise<void> {
    await chatbotApiClient.delete(
      `/api/v1/conversations/${conversationId}/tags/${tag}`
    );
  },

  /**
   * Auto-generate a title for a conversation
   */
  async generateTitle(conversationId: string): Promise<{ title: string }> {
    const response = await chatbotApiClient.post<{ title: string }>(
      `/api/v1/conversations/${conversationId}/generate-title`
    );

    return response.data;
  },

  /**
   * Get conversation statistics
   */
  async getStats(): Promise<ConversationStatsResponse> {
    const response = await chatbotApiClient.get<ConversationStatsResponse>(
      `/api/v1/conversations/stats`
    );

    return response.data;
  },

  /**
   * Add feedback to a message
   */
  async addMessageFeedback(
    messageId: string,
    feedback: MessageFeedbackRequest
  ): Promise<void> {
    await chatbotApiClient.post(
      `/api/v1/conversations/messages/${messageId}/feedback`,
      feedback
    );
  },

  /**
   * Get context information for a conversation
   */
  async getContextInfo(
    conversationId: string,
    includeCurrentQuery: boolean = false,
    currentQuery?: string
  ): Promise<ConversationContextInfo> {
    const params = new URLSearchParams({
      include_current_query: includeCurrentQuery.toString(),
      ...(currentQuery && { current_query: currentQuery }),
    });

    const response = await chatbotApiClient.get<ConversationContextInfo>(
      `/api/v1/conversations/${conversationId}/context-info?${params.toString()}`
    );

    return response.data;
  },
};
