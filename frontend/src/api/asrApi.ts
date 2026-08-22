import { API_BASE_URL } from '../config/api';
import { parseError } from '../utils/errorHandler';
import { getAuthHeaders } from './authApi';
import { authedFetch } from './http';

export interface ASRResult {
    text: string;
    duration: number;
    processing_time: number;
}

export const asrApi = {
    predict: async (file: File, language: string = 'zh'): Promise<ASRResult> => {
        try {
            const headers = getAuthHeaders() as Record<string, string>;
            const formData = new FormData();
            formData.append('file', file);
            formData.append('language', language);
            
            // For FormData, we don't set Content-Type manually
            // But we need to extract Authorization from getAuthHeaders
            const authHeader: Record<string, string> = {};
            if (headers['Authorization']) {
                authHeader['Authorization'] = headers['Authorization'];
            }
            
            const response = await authedFetch(`${API_BASE_URL}/tools/asr/predict`, {
                method: 'POST',
                headers: authHeader,
                body: formData,
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'ASR prediction failed');
            }
            
            return await response.json();
        } catch (error) {
            throw parseError(error);
        }
    }
};
