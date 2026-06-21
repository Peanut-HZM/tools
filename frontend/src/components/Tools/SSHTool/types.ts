export interface SSHSessionTab {
  tabId: string;
  configId: string;
  configSnapshot: {
    alias: string;
    host: string;
    port: number;
    username: string;
  };
  createdAt: number;
}

export type ConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'error';

export const MAX_TABS = 20;

/** 前端心跳判活阈值:90s 内未收到任何 WS 数据 → 判定死亡 */
export const HEARTBEAT_TIMEOUT_MS = 90_000;

/** 生成一个足够唯一的 tab id;浏览器原生,不依赖外部库 */
export function generateTabId(): string {
  return `tab-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}
