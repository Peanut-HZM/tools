/**
 * Authentication API Client
 */

import { AUTH_API_BASE_URL } from '../config/api';
import { authedFetch } from './http';

const API_BASE_URL = AUTH_API_BASE_URL;

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  phone?: string;
  email_code?: string;
  phone_code?: string;
}

export interface AuthResponse {
  user_id: string;
  username: string;
  email: string;
  role: string;
  token: string;
}

export interface UserResponse {
  user_id: string;
  username: string;
  email: string;
  role: string;
  created_at: string;
}

export interface ApiError {
  status: number;
  message: string;
  detail?: string;
}

export interface UserPasswordChangeRequest {
  old_password: string;
  new_password: string;
}

export interface UserPasswordChangeResponse {
  success: boolean;
  message: string;
}

/**
 * Get the stored auth token
 */
export function getAuthToken(): string | null {
  return localStorage.getItem('auth_token');
}

/**
 * Set the auth token in storage
 */
export function setAuthToken(token: string): void {
  localStorage.setItem('auth_token', token);
}

/**
 * Remove the auth token from storage
 */
export function removeAuthToken(): void {
  localStorage.removeItem('auth_token');
}

/**
 * Get authorization headers
 */
export function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  if (token) {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }
  return {
    'Content-Type': 'application/json'
  };
}

/**
 * Register a new user
 */
export async function register(data: RegisterRequest): Promise<AuthResponse> {
  const response = await authedFetch(`${API_BASE_URL}/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Registration failed');
  }

  const result = await response.json();
  setAuthToken(result.token);
  return result;
}

/**
 * Send verification code
 */
export async function sendVerificationCode(target: string, type: 'email' | 'phone'): Promise<boolean> {
  const response = await authedFetch(`${API_BASE_URL}/send-code`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ target, type })
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to send verification code');
  }

  return response.json();
}

/**
 * Login a user
 */
export async function login(data: LoginRequest): Promise<AuthResponse> {
  const response = await authedFetch(`${API_BASE_URL}/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }

  const result = await response.json();
  setAuthToken(result.token);
  return result;
}

/**
 * Logout the current user
 */
export async function logout(): Promise<void> {
  const token = getAuthToken();
  if (token) {
    try {
      await authedFetch(`${API_BASE_URL}/logout`, {
        method: 'POST',
        headers: getAuthHeaders()
      });
    } catch (e) {
      // Ignore errors during logout
    }
  }
  removeAuthToken();
}

/**
 * Get the current user's information
 */
export async function getCurrentUser(): Promise<UserResponse> {
  const response = await authedFetch(`${API_BASE_URL}/me`, {
    method: 'GET',
    headers: getAuthHeaders()
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get user info');
  }

  return response.json();
}

/**
 * Verify if the current token is valid
 */
export async function verifyToken(): Promise<boolean> {
  const token = getAuthToken();
  if (!token) {
    return false;
  }

  try {
    const response = await authedFetch(`${API_BASE_URL}/verify`, {
      method: 'GET',
      headers: getAuthHeaders()
    });
    return response.ok;
  } catch (e) {
    return false;
  }
}

/**
 * Change user password
 */
export async function changePassword(data: UserPasswordChangeRequest): Promise<UserPasswordChangeResponse> {
  const response = await authedFetch(`${API_BASE_URL}/password`, {
    method: 'PUT',
    headers: {
      ...getAuthHeaders(),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to change password');
  }

  return response.json();
}
