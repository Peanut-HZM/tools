/**
 * Config API - Configuration operations
 */
import { client } from './client'
import type { EditorConfig } from '@/types'

export const configApi = {
  async getConfig(): Promise<EditorConfig> {
    const response = await client.get<EditorConfig>('/config')
    return response.data
  },

  async saveConfig(config: EditorConfig): Promise<EditorConfig> {
    const response = await client.post<EditorConfig>('/config', config)
    return response.data
  }
}
