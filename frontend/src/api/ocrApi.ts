import { API_BASE_URL } from '../config/api';
import { parseError } from '../utils/errorHandler';
import { getAuthHeaders } from './authApi';

export interface OCRResult {
    text: string;
    blocks: Array<{
        text: string;
        confidence: number;
        box: number[][];
    }>;
    processing_time: number;
}

export interface QRCodeResult {
    text: string;
    type: string;
    processing_time: number;
}

export const ocrApi = {
    predict: async (image: string, lang: string = 'ch'): Promise<OCRResult> => {
        try {
            const headers = getAuthHeaders() as Record<string, string>;
            const response = await fetch(`${API_BASE_URL}/tools/ocr/predict`, {
                method: 'POST',
                headers: {
                    ...headers,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image, lang }),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'OCR prediction failed');
            }
            
            return await response.json();
        } catch (error) {
            throw parseError(error);
        }
    },

    predictPdf: async (file: File): Promise<OCRResult> => {
        try {
            const headers = getAuthHeaders() as Record<string, string>;
            const formData = new FormData();
            formData.append('file', file);

            const authHeader: Record<string, string> = {};
            if (headers['Authorization']) {
                authHeader['Authorization'] = headers['Authorization'];
            }

            const response = await fetch(`${API_BASE_URL}/tools/ocr/pdf`, {
                method: 'POST',
                headers: authHeader,
                body: formData,
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'PDF OCR prediction failed');
            }
            
            return await response.json();
        } catch (error) {
            throw parseError(error);
        }
    },

    scanQrcode: async (image: string): Promise<QRCodeResult> => {
        try {
            const headers = getAuthHeaders() as Record<string, string>;
            const response = await fetch(`${API_BASE_URL}/tools/ocr/qrcode`, {
                method: 'POST',
                headers: {
                    ...headers,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ image }),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'QR Code scanning failed');
            }
            
            return await response.json();
        } catch (error) {
            throw parseError(error);
        }
    }
};
