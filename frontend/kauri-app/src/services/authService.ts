import apiClient from './api';
import type { LoginCredentials, RegisterData, AuthResponse, User } from '../types';

const USER_SERVICE_URL = import.meta.env.VITE_USER_SERVICE_URL || 'http://localhost:8001';

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await apiClient.post<any>(
      `${USER_SERVICE_URL}/api/v1/auth/login`,
      {
        email: credentials.email,
        password: credentials.password,
      }
    );

    // Adapter le format du backend au format frontend
    const adaptedUser: User = {
      id: response.data.user.user_id,
      email: response.data.user.email,
      first_name: response.data.user.first_name || '',
      last_name: response.data.user.last_name || '',
      full_name: `${response.data.user.first_name || ''} ${response.data.user.last_name || ''}`.trim(),
      is_active: response.data.user.is_active,
      created_at: response.data.user.created_at,
    };

    const adaptedResponse: AuthResponse = {
      access_token: response.data.access_token,
      token_type: response.data.token_type,
      user: adaptedUser,
    };

    // Store token and user data
    if (adaptedResponse.access_token) {
      localStorage.setItem('access_token', adaptedResponse.access_token);
      localStorage.setItem('user', JSON.stringify(adaptedResponse.user));
    }

    return adaptedResponse;
  },

  async register(data: RegisterData): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>(
      `${USER_SERVICE_URL}/api/v1/auth/register`,
      data
    );

    // Store token and user data
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
    }

    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>(
      `${USER_SERVICE_URL}/api/v1/auth/me`
    );
    return response.data;
  },

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
  },

  getStoredUser(): User | null {
    const userStr = localStorage.getItem('user');
    if (!userStr || userStr === 'undefined' || userStr === 'null') {
      return null;
    }
    try {
      return JSON.parse(userStr);
    } catch (error) {
      console.error('Error parsing stored user:', error);
      localStorage.removeItem('user');
      return null;
    }
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  },
};
