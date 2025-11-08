import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import type { User, RegisterData } from '../types';
import { authService } from '../services/authService';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string, companyName?: string) => Promise<void>;
  oauthLogin: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is already logged in
    const storedUser = authService.getStoredUser();
    if (storedUser && authService.isAuthenticated()) {
      setUser(storedUser);
      // Optionally verify token with backend
      authService.getCurrentUser()
        .then(setUser)
        .catch(() => {
          authService.logout();
          setUser(null);
        });
    }
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await authService.login({ email, password });
      setUser(response.user);
    } catch (error) {
      throw error;
    }
  };

  const register = async (email: string, password: string, fullName: string, companyName?: string) => {
    try {
      const payload: RegisterData = {
        email,
        password,
        full_name: fullName.trim(),
      };

      if (companyName?.trim()) {
        payload.company_name = companyName.trim();
      }

      const response = await authService.register(payload);
      setUser(response.user);
    } catch (error) {
      throw error;
    }
  };

  const oauthLogin = async (token: string) => {
    try {
      // Store the token
      localStorage.setItem('access_token', token);

      // Fetch user info
      const userInfo = await authService.getCurrentUser();
      localStorage.setItem('user', JSON.stringify(userInfo));

      // Update context state
      setUser(userInfo);
    } catch (error) {
      // Clean up on error
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      setUser(null);
      throw error;
    }
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    register,
    oauthLogin,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
