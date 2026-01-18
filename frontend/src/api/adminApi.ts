import { getAuthHeaders } from './authApi';
import { UserResponse } from './authApi';
import { AUTH_API_BASE_URL } from '../config/api';

const API_BASE_URL = AUTH_API_BASE_URL.replace('/auth', '/admin');

export interface OssFile {
    id: number;
    name: string;
    path: string;
    url: string;
    type: string;
    size: number;
    uploaded_by: string;
    created_at: string;
}

// ...

export async function listOssFiles(): Promise<OssFile[]> {
    const response = await fetch(`${API_BASE_URL}/oss/files`, {
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to list OSS files');
    return response.json();
}

export async function deleteOssFile(path: string): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/oss/files/${encodeURIComponent(path)}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to delete OSS file');
    return response.json();
}

export interface DashboardStats {
    total_tools: number;
    total_visits: number;
    popular_tools: ToolStat[];
}

export interface ToolStat {
    tool_id: string;
    tool_name: string;
    visit_count: number;
    last_visited: string;
}

export interface Tool {
    id: string;
    title: string;
    description: string;
    icon: string;
    iconColor: string;
    category: string;
    usageCount: string;
    rating: number;
    status: string;
}

export async function listAllTools(): Promise<Tool[]> {
    const response = await fetch(`${API_BASE_URL}/tools`, {
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to list tools');
    return response.json();
}

export async function updateToolStatus(toolId: string, status: string): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/tools/${toolId}/status?status=${status}`, {
        method: 'PUT',
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to update tool status');
    return response.json();
}

export async function getDashboardStats(): Promise<DashboardStats> {
    const response = await fetch(`${API_BASE_URL}/stats`, {
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to get dashboard stats');
    return response.json();
}

export async function recordToolVisit(toolId: string, toolName: string): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/stats/visit`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ tool_id: toolId, tool_name: toolName })
    });
    if (!response.ok) throw new Error('Failed to record tool visit');
    return response.json();
}

export interface SystemSettings {
    allow_registration: boolean;
    enable_email_verify: boolean;
    enable_phone_verify: boolean;
    [key: string]: any;
}

export async function getSystemSettings(): Promise<SystemSettings> {
    const response = await fetch(`${API_BASE_URL}/settings`, {
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to get settings');
    return response.json();
}

export async function updateSystemSettings(settings: Partial<SystemSettings>): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/settings`, {
        method: 'PUT',
        headers: {
            ...getAuthHeaders() as Record<string, string>,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(settings)
    });
    if (!response.ok) throw new Error('Failed to update settings');
    return response.json();
}

export async function createUser(data: { username: string; email: string; role: string }): Promise<{ username: string; password: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/users`, {
        method: 'POST',
        headers: {
            ...getAuthHeaders() as Record<string, string>,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create user');
    }
    return response.json();
}

export async function listUsers(): Promise<UserResponse[]> {
    const response = await fetch(`${API_BASE_URL}/users`, {
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to list users');
    return response.json();
}

export async function updateUserRole(userId: string, role: string): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/users/${userId}/role`, {
        method: 'PUT',
        headers: getAuthHeaders(),
        body: JSON.stringify({ role })
    });
    if (!response.ok) throw new Error('Failed to update user role');
    return response.json();
}

export async function deleteUser(userId: string): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to delete user');
    return response.json();
}
