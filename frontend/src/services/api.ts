import { Tool } from '../types';

const API_BASE_URL = 'http://localhost:19092/api';

export async function fetchTools(): Promise<Tool[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/tools`);
    if (!response.ok) {
      throw new Error('Failed to fetch tools');
    }
    const data = await response.json();
    return data.tools;
  } catch (error) {
    console.error('Error fetching tools:', error);
    throw error;
  }
}

export async function searchTools(query: string): Promise<Tool[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/tools/search?q=${encodeURIComponent(query)}`);
    if (!response.ok) {
      throw new Error('Failed to search tools');
    }
    const data = await response.json();
    return data.tools;
  } catch (error) {
    console.error('Error searching tools:', error);
    throw error;
  }
}

export async function fetchToolsByCategory(category: string): Promise<Tool[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/tools/category/${encodeURIComponent(category)}`);
    if (!response.ok) {
      throw new Error('Failed to fetch tools by category');
    }
    const data = await response.json();
    return data.tools;
  } catch (error) {
    console.error('Error fetching tools by category:', error);
    throw error;
  }
}
