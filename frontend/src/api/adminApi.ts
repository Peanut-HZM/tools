import { getAuthHeaders } from './authApi';
import { UserResponse } from './authApi';
import { AUTH_API_BASE_URL } from '../config/api';

const API_BASE_URL = AUTH_API_BASE_URL.replace('/auth', '/admin');
const PUBLIC_API_BASE_URL = AUTH_API_BASE_URL.replace('/auth', '');

export interface ToolCategory {
    id: string;
    name: string;
    description?: string;
    icon?: string;
    sort_order: number;
}

export async function listCategories(): Promise<ToolCategory[]> {
    const response = await fetch(`${PUBLIC_API_BASE_URL}/categories`);
    if (!response.ok) throw new Error('Failed to list categories');
    return response.json();
}

export async function createCategory(data: Partial<ToolCategory>): Promise<ToolCategory> {
    const response = await fetch(`${PUBLIC_API_BASE_URL}/categories`, {
        method: 'POST',
        headers: {
            ...getAuthHeaders(),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to create category');
    return response.json();
}

export async function updateCategory(id: string, data: Partial<ToolCategory>): Promise<ToolCategory> {
    const response = await fetch(`${PUBLIC_API_BASE_URL}/categories/${id}`, {
        method: 'PUT',
        headers: {
            ...getAuthHeaders(),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update category');
    return response.json();
}

export async function deleteCategory(id: string): Promise<boolean> {
    const response = await fetch(`${PUBLIC_API_BASE_URL}/categories/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to delete category');
    return response.json();
}

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
    custom_icon_url?: string;
    show_pc?: boolean;
    show_mobile?: boolean;
}

export interface ToolsPaginatedResponse {
    tools: Tool[];
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
}

export interface ToolsListParams {
    page?: number;
    page_size?: number;
    search?: string;
    status?: string;
    category?: string;
    sort_by?: string;
    sort_order?: string;
    show_pc?: boolean;
    show_mobile?: boolean;
}

export async function listToolsPaginated(params?: ToolsListParams): Promise<ToolsPaginatedResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    if (params?.search) searchParams.append('search', params.search);
    if (params?.status) searchParams.append('status', params.status);
    if (params?.category) searchParams.append('category', params.category);
    if (params?.sort_by) searchParams.append('sort_by', params.sort_by);
    if (params?.sort_order) searchParams.append('sort_order', params.sort_order);
    if (params?.show_pc !== undefined) searchParams.append('show_pc', String(params.show_pc));
    if (params?.show_mobile !== undefined) searchParams.append('show_mobile', String(params.show_mobile));

    const queryString = searchParams.toString();
    const url = queryString ? `${API_BASE_URL}/tools?${queryString}` : `${API_BASE_URL}/tools`;

    const response = await fetch(url, {
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to list tools');
    return response.json();
}

export async function updateTool(toolId: string, data: Partial<Tool>): Promise<Tool> {
    const response = await fetch(`${API_BASE_URL}/tools/${toolId}`, {
        method: 'PUT',
        headers: {
            ...getAuthHeaders(),
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to update tool');
    return response.json();
}

export async function uploadToolIcon(toolId: string, file: File): Promise<{ url: string }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/tools/${toolId}/icon`, {
        method: 'POST',
        headers: {
            'Authorization': getAuthHeaders()['Authorization'] || ''
        },
        body: formData
    });
    if (!response.ok) throw new Error('Failed to upload icon');
    return response.json();
}

export async function deleteToolIcon(toolId: string): Promise<boolean> {
    const response = await fetch(`${API_BASE_URL}/tools/${toolId}/icon`, {
        method: 'DELETE',
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to delete icon');
    return response.json();
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

export interface UserListResponse {
    total: number;
    page: number;
    page_size: number;
    total_pages: number;
    users: UserResponse[];
}

export interface AdminPasswordResetRequest {
    mode: 'direct' | 'random';
    new_password?: string;
}

export interface AdminPasswordResetResponse {
    success: boolean;
    new_password: string;
    message: string;
}

export async function resetUserPassword(userId: string, data: AdminPasswordResetRequest): Promise<AdminPasswordResetResponse> {
    const response = await fetch(`${API_BASE_URL}/users/${userId}/reset-password`, {
        method: 'POST',
        headers: {
            ...getAuthHeaders() as Record<string, string>,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to reset password');
    }
    return response.json();
}

export interface UserListParams {
    page?: number;
    page_size?: number;
    search?: string;
    role?: string;
}

export async function listUsers(params?: UserListParams): Promise<UserListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.page_size) searchParams.append('page_size', params.page_size.toString());
    if (params?.search) searchParams.append('search', params.search);
    if (params?.role) searchParams.append('role', params.role);

    const queryString = searchParams.toString();
    const url = queryString ? `${API_BASE_URL}/users?${queryString}` : `${API_BASE_URL}/users`;

    const response = await fetch(url, {
        headers: getAuthHeaders()
    });
    if (!response.ok) throw new Error('Failed to list users');
    return response.json();
}

export async function batchDeleteUsers(userIds: string[]): Promise<{ success_count: number; failed_count: number; errors: string[] }> {
    const response = await fetch(`${API_BASE_URL}/users/batch-delete`, {
        method: 'POST',
        headers: {
            ...getAuthHeaders() as Record<string, string>,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ user_ids: userIds })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to batch delete users');
    }
    return response.json();
}

export async function batchUpdateUserRole(userIds: string[], role: string): Promise<{ success_count: number; failed_count: number; errors: string[] }> {
    const response = await fetch(`${API_BASE_URL}/users/batch-update-role`, {
        method: 'POST',
        headers: {
            ...getAuthHeaders() as Record<string, string>,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ user_ids: userIds, role })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to batch update user role');
    }
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
