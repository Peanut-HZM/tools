import React from 'react';
import K8sTool from '../Tools/K8sTool/K8sTool';
import SSHTool from '../Tools/SSHTool/SSHTool';
import DatabaseTool from '../Tools/DatabaseTool/DatabaseTool';
import RedisTool from '../Tools/RedisTool/RedisTool';
import MarkdownEditorTool from '../Tools/MarkdownEditorTool';
import OCRTool from '../Tools/OCR/OCRTool';
import ASRTool from '../Tools/ASR/ASRTool';
import JsonFormatter from '../Tools/JsonFormatter';
import Calendar from '../Tools/Calendar';
import AIAssistant from '../Tools/AIAssistant';
import KeyGenerator from '../Tools/KeyGenerator';
import MarkItDownConverter from '../Tools/MarkItDownConverter';
import ProductManagerAgent from '../Tools/ProductManagerAgent';
import LearningSharePlatform from '../Tools/LearningSharePlatform';
import CrossShareMain from '../Tools/CrossShare/CrossShareMain';
import HttpApiClient from '../Tools/HttpApiClient/HttpApiClient';
import SystemMonitor from '../Tools/SystemMonitor';
import TokenUsage from '../Tools/TokenUsage';
import SubscriptionQuotaTool from '../Tools/SubscriptionQuota';
import ImageDownloader from '../Tools/ImageDownloader';
import VideoDownloader from '../Tools/VideoDownloader';
import ImageGenerationTool from '../Tools/ImageGeneration/ImageGenerationTool';
import VideoGenerationTool from '../Tools/VideoGeneration/VideoGenerationTool';
import Neo4jExplorer from '../Tools/Neo4jExplorer/Neo4jExplorer';

/**
 * 工具 ID → 组件映射
 * 工作区通过此映射渲染标签面板
 */
export const toolComponentMap: Record<string, React.ComponentType> = {
  'k8s-tool': K8sTool,
  'ssh-tool': SSHTool,
  'database-tool': DatabaseTool,
  'redis-tool': RedisTool,
  'markdown-editor': MarkdownEditorTool,
  'ocr': OCRTool,
  'ocr-tool': OCRTool,
  'asr': ASRTool,
  'asr-tool': ASRTool,
  'json-formatter': JsonFormatter,
  'calendar': Calendar,
  'ai-assistant': AIAssistant,
  'key-generator': KeyGenerator,
  'markitdown-converter': MarkItDownConverter,
  'product-manager': ProductManagerAgent,
  'learning-share': LearningSharePlatform,
  'course-platform': LearningSharePlatform,
  'cross-share': CrossShareMain,
  'http-api-client': HttpApiClient,
  'system-monitor': SystemMonitor,
  // 合并后：agent-hub 是唯一入口
  'agent-hub': SubscriptionQuotaTool,
  // 「订阅套餐额度」工具已下线，但用户本地可能还留着旧标签页（store 持久化）：
  // 旧 id 直接映射到合并后的统一页面，避免出现「未知工具」报错。
  'subscription-quota': SubscriptionQuotaTool,
  'token-usage': TokenUsage,
  'image-downloader': ImageDownloader,
  'video-downloader': VideoDownloader,
  'image-generation': ImageGenerationTool,
  'video-generation': VideoGenerationTool,
  'neo4j-explorer': Neo4jExplorer,
};
