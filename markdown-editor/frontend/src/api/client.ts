/**
 * API Client - Base HTTP client for API calls
 */
import axios, { AxiosError, type AxiosInstance, type AxiosResponse } from 'axios'
import type { ApiError } from '@/types'

const BASE_URL = '/api'

// Create axios instance
const client: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Response interceptor for error handling
client.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    const apiError: ApiError = {
      status: error.response?.status || 500,
      message: 'An unexpected error occurred',
      details: undefined
    }

    if (error.response?.data) {
      const data = error.response.data as { detail?: string; message?: string }
      apiError.message = data.detail || data.message || apiError.message
    }

    return Promise.reject(apiError)
  }
)

export { client }

/**
 * Handle API errors and show notifications
 */
export function handleApiError(error: ApiError): string {
  switch (error.status) {
    case 400:
      return error.message || 'Invalid request'
    case 404:
      return error.message || 'Resource not found'
    case 403:
      return 'Permission denied'
    case 409:
      return error.message || 'Resource conflict'
    case 500:
      return 'Server error occurred'
    default:
      return error.message || 'An unexpected error occurred'
  }
}
