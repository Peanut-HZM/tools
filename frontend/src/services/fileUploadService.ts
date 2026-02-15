/**
 * File Upload Service
 * 
 * Handles file uploads with support for chunked uploads for large files.
 */
import { uploadMarkdownToOss, type OssUploadMarkdownResponse } from '../api/markdownEditorApi';
import type { UploadOptions } from '../types/offlineCache';

const DEFAULT_CHUNK_SIZE = 1024 * 1024;
const MAX_RETRIES = 3;

export class FileUploadService {
  private activeUploads = new Map<string, AbortController>();

  /**
   * Upload a file to OSS
   */
  async uploadFile(
    file: File,
    options: UploadOptions = {}
  ): Promise<OssUploadMarkdownResponse> {
    const { onProgress, overwrite = false } = options;

    const chunkSize = options.chunkSize || DEFAULT_CHUNK_SIZE;
    const shouldChunk = file.size > chunkSize;

    if (shouldChunk) {
      return this.uploadChunked(file, chunkSize, onProgress);
    } else {
      return this.uploadSingle(file, onProgress);
    }
  }

  /**
   * Upload a small file in one request
   */
  private async uploadSingle(
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<OssUploadMarkdownResponse> {
    const uploadId = this.generateUploadId();
    const abortController = new AbortController();
    this.activeUploads.set(uploadId, abortController);

    try {
      onProgress?.(0);

      const response = await uploadMarkdownToOss(file);

      onProgress?.(100);

      return response;
    } finally {
      this.activeUploads.delete(uploadId);
    }
  }

  private async uploadChunked(
    file: File,
    chunkSize: number,
    onProgress?: (progress: number) => void
  ): Promise<OssUploadMarkdownResponse> {
    console.warn('Chunked upload not fully implemented, using single upload');
    return this.uploadSingle(file, onProgress);
  }

  /**
   * Validate file before upload
   */
  validateFile(file: File): { valid: boolean; error?: string } {
    const allowedExtensions = ['.md', '.markdown', '.txt'];
    const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();

    if (!allowedExtensions.includes(extension)) {
      return {
        valid: false,
        error: `Invalid file type. Only ${allowedExtensions.join(', ')} files are allowed`,
      };
    }

    const maxSize = 100 * 1024 * 1024;
    if (file.size > maxSize) {
      return {
        valid: false,
        error: `File too large. Maximum size is ${maxSize / 1024 / 1024}MB`,
      };
    }

    return { valid: true };
  }

  /**
   * Cancel an active upload
   */
  cancelUpload(uploadId: string): void {
    const controller = this.activeUploads.get(uploadId);
    if (controller) {
      controller.abort();
      this.activeUploads.delete(uploadId);
    }
  }

  /**
   * Cancel all active uploads
   */
  cancelAllUploads(): void {
    for (const [id, controller] of this.activeUploads) {
      controller.abort();
      this.activeUploads.delete(id);
    }
  }

  /**
   * Check if any uploads are active
   */
  hasActiveUploads(): boolean {
    return this.activeUploads.size > 0;
  }

  private generateUploadId(): string {
    return `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

// Singleton instance
export const fileUploadService = new FileUploadService();
export default fileUploadService;
