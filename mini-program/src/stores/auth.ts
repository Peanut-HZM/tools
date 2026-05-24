import { create } from 'zustand';
import Taro from '@tarojs/taro';

interface AuthStore {
  isAuthenticated: boolean;
  token: string | null;
  user: { id: string; username: string; role: string } | null;
  login: (token: string, user: any) => void;
  logout: () => void;
  updateUser: (user: Partial<any>) => void;
}

/**
 * 惰性读取 Storage，避免小程序启动时 WebView 未初始化导致 "too early" 错误
 */
function getStoredAuth(): { isAuthenticated: boolean; token: string | null; user: any } {
  try {
    const token = Taro.getStorageSync('auth_token');
    const userInfo = Taro.getStorageSync('user_info');
    let user = null;
    if (userInfo) {
      try {
        user = JSON.parse(userInfo);
      } catch {
        // ignore parse errors
      }
    }
    return { isAuthenticated: !!token, token: token || null, user };
  } catch {
    return { isAuthenticated: false, token: null, user: null };
  }
}

// 惰性初始化
const { isAuthenticated: initAuth, token: initToken, user: initUser } = getStoredAuth();

export const useAuthStore = create<AuthStore>((set) => ({
  isAuthenticated: initAuth,
  token: initToken,
  user: initUser,

  login: (token, user) => {
    set({ isAuthenticated: true, token, user });
  },

  logout: () => {
    set({ isAuthenticated: false, token: null, user: null });
  },

  updateUser: (userData) => {
    set((state) => ({
      user: state.user ? { ...state.user, ...userData } : null
    }));
  }
}));
