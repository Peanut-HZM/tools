import Taro from '@tarojs/taro';
import { request } from './request';
import type { AuthResponse, User } from '../types';

/**
 * 认证相关 API
 */
export const authApi = {
  /** 用户登录 */
  login: async (username: string, password: string): Promise<AuthResponse> => {
    return request('/auth/login', {
      method: 'POST',
      data: { username, password },
      needAuth: false
    });
  },

  /** 微信一键登录：Taro.login() code → 后端 openid 换 JWT */
  wechatLogin: async (): Promise<AuthResponse> => {
    const loginResult = await Taro.login();
    return request('/auth/wechat-login', {
      method: 'POST',
      data: { code: loginResult.code },
      needAuth: false
    });
  },

  /** 用户注册 */
  register: async (data: {
    username: string;
    password: string;
    email?: string;
    phone?: string;
  }): Promise<AuthResponse> => {
    return request('/auth/register', {
      method: 'POST',
      data,
      needAuth: false
    });
  },

  /** 验证 token 有效性 */
  verifyToken: async (): Promise<{ valid: boolean; user?: User }> => {
    return request('/auth/verify');
  },

  /** 修改密码 */
  changePassword: async (oldPassword: string, newPassword: string): Promise<void> => {
    return request('/auth/change-password', {
      method: 'POST',
      data: { old_password: oldPassword, new_password: newPassword }
    });
  },

  /** 获取用户信息 */
  getUserInfo: async (): Promise<User> => {
    return request('/auth/me');
  },

  /** 更新用户信息 */
  updateUserInfo: async (data: Partial<User>): Promise<User> => {
    return request('/auth/me', {
      method: 'PUT',
      data
    });
  }
};
