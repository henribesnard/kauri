import apiClient from './api';
import type { ChatQueryRequest, ChatQueryResponse } from '../types';

const CHATBOT_SERVICE_URL = import.meta.env.VITE_CHATBOT_SERVICE_URL || 'http://localhost:3202';

export const chatbotService = {
  async sendQuery(query: string, conversationId?: string, userSettings?: Record<string, any>): Promise<ChatQueryResponse> {
    const request: ChatQueryRequest = {
      query,
      conversation_id: conversationId,
      user_settings: userSettings,
    };

    const response = await apiClient.post<ChatQueryResponse>(
      `${CHATBOT_SERVICE_URL}/api/v1/chat/query`,
      request
    );

    return response.data;
  },

  // For streaming responses (SSE)
  createStreamConnection(query: string, conversationId?: string, userSettings?: Record<string, any>): EventSource {
    const token = localStorage.getItem('access_token');
    const params = new URLSearchParams({
      query,
      ...(conversationId && { conversation_id: conversationId }),
      ...(token && { token }),
    });

    // Add user_settings if provided
    if (userSettings) {
      params.append('user_settings', JSON.stringify(userSettings));
    }

    return new EventSource(
      `${CHATBOT_SERVICE_URL}/api/v1/chat/stream?${params.toString()}`
    );
  },
};
