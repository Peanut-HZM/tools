import { getAuthHeaders } from './authApi';

const API_BASE_URL = 'http://localhost:19092/api/converter';

export interface ConvertResponse {
  content: string;
  history_item?: HistoryItem;
}

export interface HistoryItem {
  id: string;
  file_name: string;
  file_size: number;
  content: string;
  created_at: number;
}

/**
 * Convert document to Markdown
 */
export async function convertDocument(file: File): Promise<ConvertResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const headers = getAuthHeaders() as Record<string, string>;
  delete headers['Content-Type'];

  const response = await fetch(`${API_BASE_URL}/convert`, {
    method: 'POST',
    headers: {
      ...headers,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Conversion failed' }));
    let errorMessage = error.detail || `HTTP error ${response.status}`;
    if (typeof errorMessage === 'object') {
      errorMessage = JSON.stringify(errorMessage);
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

/**
 * Get conversion history
 */
export async function getHistory(): Promise<HistoryItem[]> {
  const headers = getAuthHeaders() as Record<string, string>;
  
  const response = await fetch(`${API_BASE_URL}/history`, {
    method: 'GET',
    headers: {
      ...headers,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to fetch history' }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }

  return response.json();
}

/**
 * Delete history item
 */
export async function deleteHistory(id: string): Promise<void> {
  const headers = getAuthHeaders() as Record<string, string>;
  
  const response = await fetch(`${API_BASE_URL}/history/${id}`, {
    method: 'DELETE',
    headers: {
      ...headers,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete history item' }));
    throw new Error(error.detail || `HTTP error ${response.status}`);
  }
}
