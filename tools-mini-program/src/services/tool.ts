import { request } from './request';
import type { Tool, ToolCategory, ApiResponse } from '../types';

/**
 * 工具相关 API
 */

// 小程序端工具路径映射（根据后端返回的 id 映射到小程序页面）
const TOOL_PATH_MAP: Record<string, string | null> = {
  'json-formatter': '/pages/json-formatter/index',
  'calendar': '/pages/calendar/index',
  'key-generator': '/pages/key-generator/index',
  'cross-share': '/pages/cross-share/message/index',
  'ocr-tool': '/pages/ocr/index',
  'asr-tool': '/pages/asr/index',
  'http-api-client': '/pages/http-client/index',
  'openclaw': '/pages/openclaw/index',
  // 第一批：媒体与文档
  'image-downloader': '/package-media/pages/image-downloader/index',
  'video-downloader': '/package-media/pages/video-downloader/index',
  'markitdown-converter': '/package-docs/pages/markitdown-converter/index',
  'markdown-editor': '/package-docs/pages/markdown-editor/index',
  // 第二批：学习
  'course-platform': '/package-learning/pages/course-platform/index',
  'tech-contents': '/package-learning/pages/tech-contents/index',
  // 第三批：统计
  'token-usage': '/package-stats/pages/token-usage/index',
  // 隐藏工具（保持 null）
  'database-tool': null,
  'redis-tool': null,
  'ssh-tool': null,
  'cursor-history': null,
  'openspec-course': null,
  'ai-assistant': null,
  'product-manager': null,
  'learning-share': null,
  'system-monitor': null,
}

export const toolApi = {
  /** 获取所有工具列表 */
  getTools: async (category?: ToolCategory): Promise<Tool[]> => {
    const params = new URLSearchParams();
    params.append('platform', 'mobile');
    if (category && category !== 'all') params.append('category', category);
    const res = await request<{ tools: Tool[] }>(`/tools?${params.toString()}`, {
      needAuth: false
    });
    // 为每个工具补充小程序端 path，过滤掉移动端不适用的工具和离线工具
    const tools = res.tools || [];
    return tools
      .filter(t => t.status === 'online')  // 只显示在线工具
      .map(tool => ({
        ...tool,
        path: tool.path || TOOL_PATH_MAP[tool.id] || null
      }))
      .filter(t => t.path !== null);  // 过滤掉没有小程序页面的工具
  },

  /** 获取工具详情 */
  getTool: async (toolId: string): Promise<Tool> => {
    return request(`/tools/${toolId}`, { needAuth: false });
  },

  /** 记录工具访问 */
  trackVisit: async (toolId: string): Promise<void> => {
    return request(`/tools/${toolId}/visit`, {
      method: 'POST',
      needAuth: false
    });
  },

  /** 搜索工具 */
  searchTools: async (keyword: string): Promise<Tool[]> => {
    const res = await request<{ tools: Tool[] }>(`/tools?search=${encodeURIComponent(keyword)}`, {
      needAuth: false
    });
    return res.tools || [];
  }
};
