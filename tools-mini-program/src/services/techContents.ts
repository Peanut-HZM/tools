import { request } from './request';

export interface TechContent {
  id: number;
  title: string;
  slug: string;
  content?: string;
  excerpt?: string;
  content_type: string;
  content_type_label: string;
  category?: string;
  tags?: string[];
  cover_image?: string;
  author?: string;
  description?: string;
  reading_time?: number;
  views?: number;
  view_count: number;
  like_count: number;
  published_at?: string;
  created_at: string;
  updated_at: string;
}

export interface ContentType {
  value: string;
  label: string;
}

export interface TechContentListResponse {
  contents: TechContent[];
  total: number;
  page: number;
  limit: number;
  types: ContentType[];
}

export interface TechContentDetail extends TechContent {
  content: string;
}

export const techContentsApi = {
  getContents: async (params: {
    content_type?: string;
    category?: string;
    search?: string;
    page?: number;
    limit?: number;
  } = {}): Promise<TechContentListResponse> => {
    const qs = new URLSearchParams();
    if (params.content_type) qs.append('content_type', params.content_type);
    if (params.category) qs.append('category', params.category);
    if (params.search) qs.append('search', params.search);
    if (params.page) qs.append('page', String(params.page));
    if (params.limit) qs.append('limit', String(params.limit));
    return request(`/tech-contents?${qs.toString()}`, { needAuth: false });
  },

  getContentDetail: async (slug: string): Promise<TechContentDetail> => {
    return request(`/tech-contents/${slug}`, { needAuth: false });
  },

  getContentTypes: async (): Promise<{ types: ContentType[] }> => {
    return request('/tech-contents/types', { needAuth: false });
  },

  likeContent: async (contentId: number): Promise<any> => {
    return request(`/tech-contents/${contentId}/like`, {
      method: 'POST',
      needAuth: true,
    });
  },
};
