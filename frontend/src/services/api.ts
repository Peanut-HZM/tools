import { Tool, ToolCategory } from '../types';
import { API_BASE_URL } from '../config/api';

export async function fetchCategories(): Promise<ToolCategory[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/categories`);
    if (!response.ok) {
      throw new Error('Failed to fetch categories');
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching categories:', error);
    throw error;
  }
}

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

export async function loadToolsByCategory(category: string): Promise<Tool[]> {
    return fetchToolsByCategory(category);
}
