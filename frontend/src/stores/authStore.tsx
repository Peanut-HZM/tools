/**
 * Authentication Store - Manages user authentication state using React Context
 * Note: Using React Context instead of Zustand to avoid adding new dependencies
 */
import { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
import * as authApi from '../api/authApi';
import { syncTokenUsage as apiSyncTokenUsage } from '../api/tokenUsageApi';

export interface User {
  user_id: string;
  username: string;
  email: string;
  role: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  /** 认证状态代际：登录/登出/401 时递增，页面据此自动重载数据 */
  authVersion: number;
}

export interface AuthActions {
  login: (username: string, password: string) => Promise<void>;
  register: (
    username: string,
    email: string,
    password: string,
    phone?: string,
    emailCode?: string,
    phoneCode?: string
  ) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
  clearError: () => void;
  /** 401 失效处理：清除 token 与用户态；仅在"已登录→未登录"转变时递增 authVersion */
  markUnauthorized: () => void;
}

export type AuthContextType = AuthState & AuthActions;

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [authVersion, setAuthVersion] = useState(0);

  // 同步追踪 isAuthenticated 的真实值，避免同一渲染内连续 markUnauthorized
  // 重复递增 authVersion（setState 是异步批处理的）
  const isAuthenticatedRef = useRef(false);

  // Check authentication status on mount
  useEffect(() => {
    checkAuth();
  }, []);

  // 登录/已认证后触发 Token 数据同步（fire-and-forget，不阻塞主流程）
  const syncInProgressRef = useRef(false);

  const triggerTokenSync = () => {
    if (syncInProgressRef.current) return;
    syncInProgressRef.current = true;
    // 不等待返回，后台同步不影响首页加载
    apiSyncTokenUsage()
      .then(() => {
        console.log('[TokenSync] 后台同步已触发');
      })
      .catch(() => {
        // 同步失败不影响认证流程，用户可手动点击"同步数据"
      })
      .finally(() => {
        syncInProgressRef.current = false;
      });
  };

  const checkAuth = async () => {
    setIsLoading(true);
    try {
      const isValid = await authApi.verifyToken();
      if (isValid) {
        const userData = await authApi.getCurrentUser();
        setUser({
          user_id: userData.user_id,
          username: userData.username,
          email: userData.email,
          role: userData.role || 'user'
        });
        setIsAuthenticated(true);
        isAuthenticatedRef.current = true;
        triggerTokenSync();
      } else {
        setUser(null);
        setIsAuthenticated(false);
        isAuthenticatedRef.current = false;
        authApi.removeAuthToken();
      }
    } catch (e) {
      setUser(null);
      setIsAuthenticated(false);
      isAuthenticatedRef.current = false;
      authApi.removeAuthToken();
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (username: string, password: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await authApi.login({ username, password });
      setUser({
        user_id: response.user_id,
        username: response.username,
        email: response.email,
        role: response.role || 'user'
      });
      setIsAuthenticated(true);
      isAuthenticatedRef.current = true;
      setAuthVersion(v => v + 1);
      triggerTokenSync();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Login failed');
      throw e;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (
    username: string,
    email: string,
    password: string,
    phone?: string,
    emailCode?: string,
    phoneCode?: string
  ) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await authApi.register({
        username,
        email,
        password,
        phone: phone || undefined,
        email_code: emailCode || undefined,
        phone_code: phoneCode || undefined,
      });
      setUser({
        user_id: response.user_id,
        username: response.username,
        email: response.email,
        role: response.role || 'user'
      });
      setIsAuthenticated(true);
      isAuthenticatedRef.current = true;
      setAuthVersion(v => v + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Registration failed');
      throw e;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      setIsAuthenticated(false);
      isAuthenticatedRef.current = false;
      setAuthVersion(v => v + 1);
      setIsLoading(false);
    }
  };

  const clearError = () => {
    setError(null);
  };

  const markUnauthorized = () => {
    authApi.removeAuthToken();
    setUser(null);
    // 基于 ref 判断：同一渲染内连续 401 只递增一次 authVersion
    if (isAuthenticatedRef.current) {
      setAuthVersion(v => v + 1);
    }
    isAuthenticatedRef.current = false;
    setIsAuthenticated(false);
  };

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    error,
    authVersion,
    login,
    register,
    logout,
    checkAuth,
    clearError,
    markUnauthorized
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export { AuthContext };
