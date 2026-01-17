/**
 * Search API - Search operations
 */
import { client } from './client'
import type { FileSearchResult, SearchResult } from '@/types'

export const searchApi = {
  async searchFiles(keyword: string): Promise<FileSearchResult[]> {
    const response = await client.get<FileSearchResult[]>('/search/files', {
      params: { keyword }
    })
    return response.data
  },

  async searchContent(
    keyword: string,
    regex: boolean = false,
    caseSensitive: boolean = false
  ): Promise<SearchResult[]> {
    const response = await client.get<SearchResult[]>('/search/content', {
      params: {
        keyword,
        regex,
        case_sensitive: caseSensitive
      }
    })
    return response.data
  }
}
