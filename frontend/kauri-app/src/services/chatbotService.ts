import apiClient from './api';
import { ChatQueryRequest, ChatQueryResponse } from '../types';

const CHATBOT_SERVICE_URL = import.meta.env.VITE_CHATBOT_SERVICE_URL || 'http://localhost:8002';

export const chatbotService = {
  async sendQuery(query: string, sessionId?: string): Promise<ChatQueryResponse> {
    const request: ChatQueryRequest = {
      query,
      session_id: sessionId,
    };

    const response = await apiClient.post<ChatQueryResponse>(
      `${CHATBOT_SERVICE_URL}/api/v1/chat/query`,
      request
    );

    return response.data;
  },

  // For streaming responses (SSE)
  createStreamConnection(query: string, sessionId?: string): EventSource {
    const token = localStorage.getItem('access_token');
    const params = new URLSearchParams({
      query,
      ...(sessionId && { session_id: sessionId }),
      ...(token && { token }),
    });

    return new EventSource(
      `${CHATBOT_SERVICE_URL}/api/v1/chat/stream?${params.toString()}`
    );
  },
};
