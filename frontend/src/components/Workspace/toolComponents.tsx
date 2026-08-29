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
import CursorHistory from '../Tools/CursorHistory/CursorHistory';
import HttpApiClient from '../Tools/HttpApiClient/HttpApiClient';
import SystemMonitor from '../Tools/SystemMonitor';
import TokenUsage from '../Tools/TokenUsage';
import OpenClawChat from '../Tools/OpenClawChat/OpenClawChat';
import ImageDownloader from '../Tools/ImageDownloader';
import VideoDownloader from '../Tools/VideoDownloader';

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
  'asr': ASRTool,
  'json-formatter': JsonFormatter,
  'calendar': Calendar,
  'ai-assistant': AIAssistant,
  'key-generator': KeyGenerator,
  'markitdown-converter': MarkItDownConverter,
  'product-manager': ProductManagerAgent,
  'learning-share': LearningSharePlatform,
  'cross-share': CrossShareMain,
  'cursor-history': CursorHistory,
  'http-api-client': HttpApiClient,
  'system-monitor': SystemMonitor,
  'token-usage': TokenUsage,
  'openclaw': OpenClawChat,
  'image-downloader': ImageDownloader,
  'video-downloader': VideoDownloader,
};
