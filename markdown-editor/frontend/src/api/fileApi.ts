/**
 * File API - File operations
 */
import { client } from './client'
import type { FileNode, FileContent, SaveResult } from '@/types'

export interface RootPathResponse {
  path: string
  exists: boolean
}

export const fileApi = {
  async getRootPath(): Promise<RootPathResponse> {
    const response = await client.get<RootPathResponse>('/files/root')
    return response.data
  },

  async setRootPath(path: string): Promise<RootPathResponse> {
    const response = await client.post<RootPathResponse>('/files/root', { path })
    return response.data
  },

  async getDirectoryTree(root: string = ''): Promise<FileNode> {
    const response = await client.get<FileNode>('/files/tree', {
      params: { root }
    })
    return response.data
  },

  async readFile(path: string): Promise<FileContent> {
    const response = await client.get<FileContent>('/files/read', {
      params: { path }
    })
    return response.data
  },

  async saveFile(path: string, content: string): Promise<SaveResult> {
    const response = await client.post<SaveResult>('/files/save', {
      path,
      content
    })
    return response.data
  },

  async createFile(path: string, content: string = ''): Promise<void> {
    await client.post('/files/create', {
      path,
      content
    })
  },

  async deleteFile(path: string): Promise<void> {
    await client.delete('/files/delete', {
      params: { path }
    })
  },

  async renameFile(oldPath: string, newPath: string): Promise<void> {
    await client.post('/files/rename', {
      old_path: oldPath,
      new_path: newPath
    })
  },

  async createDirectory(path: string): Promise<void> {
    await client.post('/files/directory/create', null, {
      params: { path }
    })
  },

  async deleteDirectory(path: string, recursive: boolean = false): Promise<void> {
    await client.delete('/files/directory/delete', {
      params: { path, recursive }
    })
  }
}
