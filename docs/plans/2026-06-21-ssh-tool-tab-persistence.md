---
author: peanut
created_at: 2026-06-21
purpose: SSH 工具 Tab 化与会话持久化实现计划(对应设计文档 2026-06-21-ssh-tool-tab-persistence-design.md)
---

# SSH 工具 Tab 化与会话持久化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 SSH 工具页面从"左列表 + 右单例终端"重构为 Tab 化多会话架构,每个 SSH 连接开一个独立 tab,会话保活、后台接收输出、20 个 tab 上限,并修复后端心跳与忙等待问题。

**Architecture:**
- 前端 `SSHTool` 维护 `tabs: SSHSessionTab[]` + `activeTabId`,渲染一组常驻 DOM 的 `TerminalPanel`(激活的显示、其余 `display: none`),每个 panel 各自持有一个 WebSocket + xterm 实例,生命周期对齐 tab。新增 `TabBar` 组件负责切换、关闭、计数、状态点。
- 后端 `handle_ssh_session` 增加 `pong` 心跳协程、改用 `run_in_executor + channel.settimeout` 替换 10ms 忙等待,连接失败时先发 `{"type": "error"}`、服务端 SSH 关闭时先发 `{"type": "exit"}` 再 close,并在 `ssh.connect` 后设置 `transport.set_keepalive(30)`。

**Tech Stack:** React 18 + TypeScript + Vite + Vitest + React Testing Library + Zustand(无,仅 useState)+ xterm + Tailwind;FastAPI WebSocket + paramiko + asyncio.run_in_executor。

---

## 文件结构一览

**新建**:
- `frontend/src/components/Tools/SSHTool/types.ts` — `SSHSessionTab`、`ConnectionStatus`、`MAX_TABS`。
- `frontend/src/components/Tools/SSHTool/TabBar.tsx` — 横向 tab 栏组件。
- `frontend/src/components/Tools/SSHTool/TabBar.test.tsx` — TabBar 单元测试。
- `frontend/src/components/Tools/SSHTool/EmptyState.tsx` — 空态引导(无 tab 时展示)。
- `backend/tests/test_ssh_session_heartbeat.py` — 后端心跳 / 错误推送 / 清理单元测试。

**修改**:
- `frontend/src/i18n/locales/zh-CN.ts` — 新增 8 个 ssh 文案。
- `frontend/src/i18n/locales/en-US.ts` — 新增 8 个 ssh 文案。
- `frontend/src/components/Tools/SSHTool/SSHTool.tsx` — 重构为 tab 列表管理。
- `frontend/src/components/Tools/SSHTool/SSHTool.test.tsx`(新建)— SSHTool 单元测试。
- `frontend/src/components/Tools/SSHTool/TerminalPanel.tsx` — 去除单例/自动重连,新增心跳判活、exit/error 消息处理、retry 能力、hidden 支持、onStatusChange 回调。
- `frontend/src/components/Tools/SSHTool/TerminalPanel.test.tsx` — 同步更新 mock 与用例。
- `frontend/src/components/Tools/SSHTool/ConnectionList.tsx` — `onSelect` 改为语义化"打开新 tab"。
- `backend/app/services/ssh_tool_service.py` — `handle_ssh_session` 重写为心跳 + executor 读取 + 错误推送。

---

## Task 1: 定义 `SSHSessionTab` 类型与 `MAX_TABS` 常量

**Files:**
- Create: `frontend/src/components/Tools/SSHTool/types.ts`

- [ ] **Step 1: 编写类型文件**

创建 `frontend/src/components/Tools/SSHTool/types.ts`,写入以下内容:

```typescript
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
```

- [ ] **Step 2: 验证 TypeScript 编译**

Run: `cd frontend && npx tsc --noEmit -p tsconfig.json`
Expected: 0 错误(新文件未引入任何类型错误)。

- [ ] **Step 3: 提交**

```bash
git add frontend/src/components/Tools/SSHTool/types.ts
git commit -m "feat(ssh-tool): 新增 SSHSessionTab 类型与 MAX_TABS 常量"
```

---

## Task 2: 补充 i18n 文案

**Files:**
- Modify: `frontend/src/i18n/locales/zh-CN.ts:574-603` (ssh 块)
- Modify: `frontend/src/i18n/locales/en-US.ts:573-602` (ssh 块)

- [ ] **Step 1: 在 `zh-CN.ts` ssh 块末尾追加**

在 `frontend/src/i18n/locales/zh-CN.ts` 中定位到 `testFailed: '连接失败',`(ssh 块最后一行),在其下方、`},` 之前追加:

```typescript
    tabLimitReached: '最多保留 20 个 SSH 会话,请先关闭其他会话',
    confirmCloseTab: '确定要断开此 SSH 会话并关闭标签页吗?',
    retryConnection: '重试',
    closeTab: '关闭标签',
    connectionTimeout: '连接超时,请重试',
    sessionDisconnected: '会话已断开',
    connectionError: '连接失败: {reason}',
    tabCount: '{count} / {max}',
```

- [ ] **Step 2: 在 `en-US.ts` ssh 块末尾追加同样内容**

在 `frontend/src/i18n/locales/en-US.ts` 中定位到 `testFailed: 'Connection failed',`(ssh 块最后一行),在其下方、`},` 之前追加:

```typescript
    tabLimitReached: 'Maximum 20 SSH sessions, close others first',
    confirmCloseTab: 'Disconnect this SSH session and close the tab?',
    retryConnection: 'Retry',
    closeTab: 'Close tab',
    connectionTimeout: 'Connection timed out, please retry',
    sessionDisconnected: 'Session disconnected',
    connectionError: 'Connection failed: {reason}',
    tabCount: '{count} / {max}',
```

- [ ] **Step 3: 编译 + 提交**

```bash
cd frontend && npx tsc --noEmit -p tsconfig.json
git add frontend/src/i18n/locales/zh-CN.ts frontend/src/i18n/locales/en-US.ts
git commit -m "feat(ssh-tool): 新增 Tab 化相关 i18n 文案(中英)"
```

---

## Task 3: 实现 `TabBar` 组件(含单元测试)

**Files:**
- Create: `frontend/src/components/Tools/SSHTool/TabBar.tsx`
- Create: `frontend/src/components/Tools/SSHTool/TabBar.test.tsx`

- [ ] **Step 1: 编写失败的 TabBar 测试**

创建 `frontend/src/components/Tools/SSHTool/TabBar.test.tsx`:

```typescript
import React from 'react';
import { render, fireEvent, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { TabBar } from './TabBar';
import { SSHSessionTab } from './types';

vi.mock('../../../../i18n', () => ({
  useI18n: () => ({
    t: {
      ssh: {
        confirmCloseTab: '确认断开?',
        tabCount: '{count} / {max}',
        closeTab: '关闭',
        connected: '已连接',
        connecting: '连接中',
        disconnected: '未连接',
        connectionFailed: '连接失败',
      },
      common: { cancel: '取消', confirm: '确认' },
    },
  }),
  interpolate: (s: string, vars: Record<string, string>) =>
    s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? ''),
}));

const makeTab = (tabId: string, status: 'disconnected' | 'connecting' | 'connected' | 'error' = 'connected'): { tab: SSHSessionTab; status: 'disconnected' | 'connecting' | 'connected' | 'error' } => ({
  tab: {
    tabId,
    configId: `cfg-${tabId}`,
    configSnapshot: { alias: `srv-${tabId}`, host: '127.0.0.1', port: 22, username: 'root' },
    createdAt: Date.now(),
  },
  status,
});

describe('TabBar', () => {
  it('渲染 tab 数量与标题', () => {
    const tabs = [makeTab('a'), makeTab('b')];
    render(
      <TabBar
        tabs={tabs.map(t => t.tab)}
        statuses={Object.fromEntries(tabs.map(t => [t.tab.tabId, t.status]))}
        activeTabId="a"
        onActivate={() => {}}
        onClose={() => {}}
      />
    );
    expect(screen.getByText(/srv-a/)).toBeInTheDocument();
    expect(screen.getByText(/srv-b/)).toBeInTheDocument();
    expect(screen.getByText('2 / 20')).toBeInTheDocument();
  });

  it('点击 tab 触发 onActivate', () => {
    const onActivate = vi.fn();
    const tabs = [makeTab('a'), makeTab('b')];
    render(
      <TabBar
        tabs={tabs.map(t => t.tab)}
        statuses={Object.fromEntries(tabs.map(t => [t.tab.tabId, t.status]))}
        activeTabId="a"
        onActivate={onActivate}
        onClose={() => {}}
      />
    );
    fireEvent.click(screen.getByText(/srv-b/));
    expect(onActivate).toHaveBeenCalledWith('b');
  });

  it('connected 状态点击 × 触发 confirm,取消则不调用 onClose', () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    const onClose = vi.fn();
    const tabs = [makeTab('a')];
    render(
      <TabBar
        tabs={tabs.map(t => t.tab)}
        statuses={{ a: 'connected' }}
        activeTabId="a"
        onActivate={() => {}}
        onClose={onClose}
      />
    );
    fireEvent.click(screen.getByTitle(/关闭/));
    expect(confirmSpy).toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it('connected 状态点击 × 触发 confirm,确认后调用 onClose', () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
    const onClose = vi.fn();
    const tabs = [makeTab('a')];
    render(
      <TabBar
        tabs={tabs.map(t => t.tab)}
        statuses={{ a: 'connected' }}
        activeTabId="a"
        onActivate={() => {}}
        onClose={onClose}
      />
    );
    fireEvent.click(screen.getByTitle(/关闭/));
    expect(onClose).toHaveBeenCalledWith('a');
    confirmSpy.mockRestore();
  });

  it('disconnected 状态点击 × 不弹 confirm,直接调用 onClose', () => {
    const confirmSpy = vi.spyOn(window, 'confirm');
    const onClose = vi.fn();
    const tabs = [makeTab('a')];
    render(
      <TabBar
        tabs={tabs.map(t => t.tab)}
        statuses={{ a: 'disconnected' }}
        activeTabId="a"
        onActivate={() => {}}
        onClose={onClose}
      />
    );
    fireEvent.click(screen.getByTitle(/关闭/));
    expect(confirmSpy).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalledWith('a');
    confirmSpy.mockRestore();
  });

  it('状态点颜色按 status 渲染', () => {
    const tabs = [makeTab('a'), makeTab('b'), makeTab('c'), makeTab('d')];
    render(
      <TabBar
        tabs={tabs.map(t => t.tab)}
        statuses={{
          a: 'connected',
          b: 'connecting',
          c: 'error',
          d: 'disconnected',
        }}
        activeTabId="a"
        onActivate={() => {}}
        onClose={() => {}}
      />
    );
    const dot = (tabId: string) => screen.getByTestId(`tab-dot-${tabId}`);
    expect(dot('a').className).toContain('bg-green');
    expect(dot('b').className).toContain('bg-yellow');
    expect(dot('c').className).toContain('bg-red');
    expect(dot('d').className).toContain('bg-slate');
  });
});
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `cd frontend && npx vitest run src/components/Tools/SSHTool/TabBar.test.tsx`
Expected: FAIL — `Cannot find module './TabBar'`。

- [ ] **Step 3: 实现 `TabBar.tsx`**

创建 `frontend/src/components/Tools/SSHTool/TabBar.tsx`:

```tsx
import React from 'react';
import { SSHSessionTab, ConnectionStatus, MAX_TABS } from './types';
import { useI18n, interpolate } from '../../../i18n';

interface Props {
  tabs: SSHSessionTab[];
  /** tabId -> 该 tab 当前的连接状态(TerminalPanel 上报) */
  statuses: Record<string, ConnectionStatus>;
  activeTabId: string | null;
  onActivate: (tabId: string) => void;
  onClose: (tabId: string) => void;
}

const DOT_COLORS: Record<ConnectionStatus, string> = {
  connected: 'bg-green-400',
  connecting: 'bg-yellow-400 animate-pulse',
  error: 'bg-red-500',
  disconnected: 'bg-slate-500',
};

export const TabBar: React.FC<Props> = ({ tabs, statuses, activeTabId, onActivate, onClose }) => {
  const { t } = useI18n();

  const handleClose = (tab: SSHSessionTab) => {
    const status = statuses[tab.tabId];
    // 只有 connected 状态才需要确认,避免误关
    if (status === 'connected') {
      if (!window.confirm(t.ssh.confirmCloseTab)) return;
    }
    onClose(tab.tabId);
  };

  const handleAuxClick = (e: React.MouseEvent, tab: SSHSessionTab) => {
    // 中键或 Ctrl/Cmd + 左键:关闭 tab
    if (e.button === 1 || (e.button === 0 && (e.ctrlKey || e.metaKey))) {
      e.preventDefault();
      handleClose(tab);
    }
  };

  return (
    <div className="flex items-center border-b border-slate-800 bg-slate-900">
      <div className="flex-1 flex overflow-x-auto" role="tablist">
        {tabs.map(tab => {
          const active = activeTabId === tab.tabId;
          const status = statuses[tab.tabId] || 'disconnected';
          return (
            <div
              key={tab.tabId}
              role="tab"
              aria-selected={active}
              className={`flex items-center gap-2 px-3 py-2 text-xs border-r border-slate-800 cursor-pointer select-none shrink-0 ${
                active ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-800/60'
              }`}
              onClick={() => onActivate(tab.tabId)}
              onAuxClick={e => handleAuxClick(e, tab)}
              title={
                status === 'error'
                  ? interpolate(t.ssh.connectionError, { reason: t.ssh.connectionFailed })
                  : `${tab.configSnapshot.alias} · ${tab.configSnapshot.username}@${tab.configSnapshot.host}:${tab.configSnapshot.port}`
              }
            >
              <span data-testid={`tab-dot-${tab.tabId}`} className={`inline-block w-1.5 h-1.5 rounded-full ${DOT_COLORS[status]}`} />
              <span className="max-w-[12rem] truncate">
                {tab.configSnapshot.alias}
              </span>
              <span className="text-slate-500 text-[10px] truncate">
                {tab.configSnapshot.username}@{tab.configSnapshot.host}:{tab.configSnapshot.port}
              </span>
              <button
                type="button"
                title={t.ssh.closeTab}
                className="ml-1 text-slate-400 hover:text-white"
                onClick={e => {
                  e.stopPropagation();
                  handleClose(tab);
                }}
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
      <div className="px-3 text-[11px] text-slate-500 shrink-0">
        {interpolate(t.ssh.tabCount, { count: String(tabs.length), max: String(MAX_TABS) })}
      </div>
    </div>
  );
};
```

- [ ] **Step 4: 运行测试,确认全部通过**

Run: `cd frontend && npx vitest run src/components/Tools/SSHTool/TabBar.test.tsx`
Expected: 6 tests PASS。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/Tools/SSHTool/TabBar.tsx frontend/src/components/Tools/SSHTool/TabBar.test.tsx
git commit -m "feat(ssh-tool): 新增 TabBar 组件与单元测试"
```

---

## Task 4: 重构 `SSHTool` — Tab 列表管理 + `ConnectionList` 语义化

**Files:**
- Modify: `frontend/src/components/Tools/SSHTool/SSHTool.tsx`
- Create: `frontend/src/components/Tools/SSHTool/EmptyState.tsx`
- Create: `frontend/src/components/Tools/SSHTool/SSHTool.test.tsx`
- Modify: `frontend/src/components/Tools/SSHTool/ConnectionList.tsx`(可选 — 保持签名不变,只在 `SSHTool` 里把 `onSelect` 重新绑定为"开新 tab")

- [ ] **Step 1: 编写 `SSHTool.test.tsx` 失败用例**

创建 `frontend/src/components/Tools/SSHTool/SSHTool.test.tsx`:

```typescript
import React from 'react';
import { render, fireEvent, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import SSHTool from './SSHTool';

// mock API 层
vi.mock('../../../api/sshToolApi', () => ({
  getSSHConfigs: vi.fn().mockResolvedValue([
    { id: 'cfg-1', alias: 'srv-1', host: '127.0.0.1', port: 22, username: 'root', is_active: true, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
  ]),
  createSSHConfig: vi.fn(),
  updateSSHConfig: vi.fn(),
  deleteSSHConfig: vi.fn(),
  buildSSHWebSocketUrl: () => 'ws://example.com/ssh',
}));
vi.mock('../../../api/authApi', () => ({ getAuthToken: () => 'token' }));
vi.mock('../../../hooks/useToast', () => ({ useToast: () => ({ addToast: vi.fn() }) }));
vi.mock('../../../i18n', () => ({
  useI18n: () => ({
    t: {
      ssh: {
        connections: 'SSH 连接',
        addConnection: '新增',
        editConnection: '编辑',
        alias: '别名',
        host: '主机',
        port: '端口',
        username: '用户名',
        password: '密码',
        privateKey: '私钥',
        passphrase: '口令',
        group: '分组',
        connect: '连接',
        disconnect: '断开',
        connected: '已连接',
        connecting: '连接中',
        disconnected: '未连接',
        selectConnection: '选连接',
        emptyConnections: '无连接',
        confirmDeleteConnection: '删除 {alias}?',
        saveSuccess: '保存成功',
        deleteSuccess: '删除成功',
        connectionFailed: '连接失败',
        authRequired: '请先登录',
        readyForConnection: '等待连接',
        testConnection: '测试',
        testing: '测试中',
        testSuccess: '连接成功',
        testFailed: '测试失败',
        tabLimitReached: '最多保留 20 个 SSH 会话,请先关闭其他会话',
        confirmCloseTab: '断开并关闭?',
        retryConnection: '重试',
        closeTab: '关闭',
        connectionTimeout: '超时',
        sessionDisconnected: '会话已断开',
        connectionError: '连接失败: {reason}',
        tabCount: '{count} / {max}',
      },
      common: { error: '错误', cancel: '取消', confirm: '确认', save: '保存', delete: '删除', leaveBlankToKeep: '留空保持' },
    },
  }),
  interpolate: (s: string, vars: Record<string, string>) => s.replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? ''),
}));

// mock xterm,见 TerminalPanel.test.tsx
vi.mock('xterm', () => ({
  Terminal: class {
    cols = 80; rows = 24;
    open = vi.fn(); loadAddon = vi.fn();
    onData = () => ({ dispose: vi.fn() });
    write = vi.fn(); writeln = vi.fn(); clear = vi.fn();
    dispose = vi.fn(); focus = vi.fn();
  },
}));
vi.mock('xterm-addon-fit', () => ({ FitAddon: class { fit = vi.fn(); } }));
vi.mock('xterm-addon-web-links', () => ({ WebLinksAddon: class {} }));

describe('SSHTool - Tab 管理', () => {
  beforeEach(() => {
    const ws = vi.fn().mockImplementation(() => ({
      readyState: 1, send: vi.fn(), close: vi.fn(),
      onopen: null, onmessage: null, onclose: null, onerror: null,
    }));
    vi.stubGlobal('WebSocket', ws);
  });

  it('点击侧边栏连接新增一个 tab', async () => {
    render(<SSHTool />);
    await waitFor(() => expect(screen.getByText('srv-1')).toBeInTheDocument());
    fireEvent.click(screen.getByText('srv-1'));
    expect(screen.getByText(/srv-1/)).toBeInTheDocument();
    // TabBar 计数
    expect(screen.getByText('1 / 20')).toBeInTheDocument();
  });

  it('重复点击同一连接每次都新增独立 tab', async () => {
    render(<SSHTool />);
    await waitFor(() => expect(screen.getByText('srv-1')).toBeInTheDocument());
    fireEvent.click(screen.getByText('srv-1'));
    fireEvent.click(screen.getByText('srv-1'));
    expect(screen.getByText('2 / 20')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `cd frontend && npx vitest run src/components/Tools/SSHTool/SSHTool.test.tsx`
Expected: FAIL — `TabBar` 尚未渲染、计数不显示。

- [ ] **Step 3: 创建 `EmptyState.tsx`**

```tsx
import React from 'react';
import { useI18n } from '../../../i18n';

export const EmptyState: React.FC = () => {
  const { t } = useI18n();
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-slate-500 bg-slate-900">
      <i className="fas fa-terminal text-6xl mb-4 opacity-20"></i>
      <p className="text-lg">{t.ssh.selectConnection}</p>
    </div>
  );
};
```

- [ ] **Step 4: 重写 `SSHTool.tsx`**

```tsx
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { ConnectionList } from './ConnectionList';
import { ConnectionModal } from './ConnectionModal';
import { EmptyState } from './EmptyState';
import { TabBar } from './TabBar';
import { TerminalPanel } from './TerminalPanel';
import {
  CreateSSHRequest, SSHConfig, UpdateSSHRequest,
  createSSHConfig, deleteSSHConfig, getSSHConfigs, updateSSHConfig,
} from '../../../api/sshToolApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n } from '../../../i18n';
import { ConnectionStatus, MAX_TABS, SSHSessionTab, generateTabId } from './types';

const SSHTool: React.FC = () => {
  const { addToast } = useToast();
  const { t } = useI18n();

  const [configs, setConfigs] = useState<SSHConfig[]>([]);
  const [tabs, setTabs] = useState<SSHSessionTab[]>([]);
  const [activeTabId, setActiveTabId] = useState<string | null>(null);
  const [tabStatuses, setTabStatuses] = useState<Record<string, ConnectionStatus>>({});
  const [showConnectionModal, setShowConnectionModal] = useState(false);
  const [editingConfig, setEditingConfig] = useState<SSHConfig | undefined>(undefined);

  const loadConfigs = async () => {
    try {
      const data = await getSSHConfigs();
      setConfigs(data);
    } catch {
      addToast(t.common.error, 'error');
    }
  };

  useEffect(() => { loadConfigs(); }, []);

  const handleAddConfig = () => { setEditingConfig(undefined); setShowConnectionModal(true); };
  const handleEditConfig = (config: SSHConfig) => { setEditingConfig(config); setShowConnectionModal(true); };

  const handleSaveConfig = async (data: CreateSSHRequest | UpdateSSHRequest) => {
    try {
      if ('id' in data) await updateSSHConfig(data);
      else await createSSHConfig(data);
      addToast(t.ssh.saveSuccess, 'success');
      loadConfigs();
    } catch {
      addToast(t.common.error, 'error');
    }
  };

  const handleDeleteConfig = async (id: string) => {
    try {
      await deleteSSHConfig(id);
      addToast(t.ssh.deleteSuccess, 'success');
      loadConfigs();
    } catch {
      addToast(t.common.error, 'error');
    }
  };

  /** 侧边栏点击 → 新增 tab;达到上限 toast 提示 */
  const handleSelectConnection = useCallback((configId: string) => {
    if (tabs.length >= MAX_TABS) {
      addToast(t.ssh.tabLimitReached, 'error');
      return;
    }
    const config = configs.find(c => c.id === configId);
    if (!config) return;
    const tabId = generateTabId();
    const newTab: SSHSessionTab = {
      tabId,
      configId: config.id,
      configSnapshot: {
        alias: config.alias,
        host: config.host,
        port: config.port,
        username: config.username,
      },
      createdAt: Date.now(),
    };
    setTabs(prev => [...prev, newTab]);
    setActiveTabId(tabId);
  }, [tabs.length, configs, addToast, t.ssh.tabLimitReached]);

  /** 关闭指定 tab;若为 active,自动激活相邻 */
  const handleCloseTab = useCallback((tabId: string) => {
    setTabs(prev => {
      const idx = prev.findIndex(t => t.tabId === tabId);
      const next = prev.filter(t => t.tabId !== tabId);
      setActiveTabId(current => {
        if (current !== tabId) return current;
        if (next.length === 0) return null;
        // 优先右侧相邻;否则左侧
        return prev[Math.min(idx + 1, next.length)]?.tabId ?? next[next.length - 1].tabId;
      });
      return next;
    });
    setTabStatuses(prev => {
      const { [tabId]: _removed, ...rest } = prev;
      return rest;
    });
  }, []);

  const handleActivateTab = useCallback((tabId: string) => setActiveTabId(tabId), []);

  const handleStatusChange = useCallback((tabId: string, status: ConnectionStatus) => {
    setTabStatuses(prev => ({ ...prev, [tabId]: status }));
  }, []);

  const handleRetryTab = useCallback((tabId: string) => {
    // 通过强制重渲染 TerminalPanel 触发重连:更新 createdAt
    setTabs(prev => prev.map(t => t.tabId === tabId ? { ...t, createdAt: Date.now() } : t));
  }, []);

  const activeTab = useMemo(() => tabs.find(t => t.tabId === activeTabId) ?? null, [tabs, activeTabId]);

  return (
    <div className="flex h-[calc(100vh-64px)] bg-slate-900 overflow-hidden">
      <ConnectionList
        configs={configs}
        selectedId={null}
        onSelect={handleSelectConnection}
        onAdd={handleAddConfig}
        onEdit={handleEditConfig}
        onDelete={handleDeleteConfig}
      />
      <div className="flex-1 flex flex-col overflow-hidden bg-slate-900">
        {tabs.length === 0 ? (
          <EmptyState />
        ) : (
          <>
            <TabBar
              tabs={tabs}
              statuses={tabStatuses}
              activeTabId={activeTabId}
              onActivate={handleActivateTab}
              onClose={handleCloseTab}
            />
            <div className="flex-1 relative overflow-hidden">
              {tabs.map(tab => (
                <div
                  key={tab.tabId}
                  className="absolute inset-0"
                  style={{ display: tab.tabId === activeTabId ? 'block' : 'none' }}
                >
                  <TerminalPanel
                    tabId={tab.tabId}
                    configId={tab.configId}
                    createdAt={tab.createdAt}
                    isActive={tab.tabId === activeTabId}
                    onStatusChange={handleStatusChange}
                    onRetry={handleRetryTab}
                  />
                </div>
              ))}
            </div>
          </>
        )}
      </div>
      <ConnectionModal
        isOpen={showConnectionModal}
        onClose={() => setShowConnectionModal(false)}
        onSave={handleSaveConfig}
        initialData={editingConfig}
      />
    </div>
  );
};

export default SSHTool;
```

**关键设计点**:
- `handleCloseTab` 在 `setTabs` 的更新回调内决定新的 `activeTabId`,避免 stale state。
- `TerminalPanel` 常驻 DOM,用 `display: none` 切显隐,保证 xterm 实例不被卸载。
- `handleRetryTab` 通过更新 `createdAt` 触发 `TerminalPanel` 的 `useEffect` 重建 WebSocket。
- `ConnectionList` 的 `onSelect` 现在语义是"打开新 tab",`selectedId` 传 `null`(不再有"选中"概念)。

- [ ] **Step 5: 运行测试,确认全部通过**

Run: `cd frontend && npx vitest run src/components/Tools/SSHTool/SSHTool.test.tsx`
Expected: 2 tests PASS。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/Tools/SSHTool/SSHTool.tsx frontend/src/components/Tools/SSHTool/SSHTool.test.tsx frontend/src/components/Tools/SSHTool/EmptyState.tsx
git commit -m "feat(ssh-tool): SSHTool 重构为 Tab 列表管理 + EmptyState"
```

---

## Task 5: 重构 `TerminalPanel` — 常驻 DOM、心跳判活、exit/error 消息、retry

**Files:**
- Modify: `frontend/src/components/Tools/SSHTool/TerminalPanel.tsx`
- Modify: `frontend/src/components/Tools/SSHTool/TerminalPanel.test.tsx`

- [ ] **Step 1: 改写 `TerminalPanel.test.tsx` 以匹配新签名**

完全替换 `frontend/src/components/Tools/SSHTool/TerminalPanel.test.tsx` 内容:

```typescript
import React from 'react';
import { render, waitFor, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { TerminalPanel } from './TerminalPanel';

vi.mock('../../../api/authApi', () => ({ getAuthToken: () => 'token' }));
vi.mock('../../../api/sshToolApi', () => ({
  buildSSHWebSocketUrl: () => 'ws://example.com/ssh',
}));
vi.mock('../../../hooks/useToast', () => ({ useToast: () => ({ addToast: vi.fn() }) }));
vi.mock('../../../i18n', () => ({
  useI18n: () => ({
    t: {
      ssh: {
        authRequired: 'authRequired',
        connectionFailed: 'connectionFailed',
        connected: 'connected',
        connecting: 'connecting',
        disconnected: 'disconnected',
        connect: 'connect',
        disconnect: 'disconnect',
        selectConnection: 'selectConnection',
      },
    },
  }),
}));

let lastWsInstance: any;
vi.mock('xterm', () => ({
  Terminal: class {
    cols = 80; rows = 24;
    open = vi.fn(); loadAddon = vi.fn();
    onData = () => ({ dispose: vi.fn() });
    write = vi.fn(); writeln = vi.fn(); clear = vi.fn();
    dispose = vi.fn(); focus = vi.fn();
  },
}));
vi.mock('xterm-addon-fit', () => ({ FitAddon: class { fit = vi.fn(); } }));
vi.mock('xterm-addon-web-links', () => ({ WebLinksAddon: class {} }));

const setupWs = () => {
  const ws = vi.fn().mockImplementation(() => {
    const inst = {
      readyState: 1,
      send: vi.fn(),
      close: vi.fn(),
      onopen: null as any, onmessage: null as any, onclose: null as any, onerror: null as any,
    };
    lastWsInstance = inst;
    return inst;
  });
  vi.stubGlobal('WebSocket', ws);
  return ws;
};

const DEFAULT_PROPS = {
  tabId: 'tab-1',
  configId: 'cfg-1',
  createdAt: 1000,
  isActive: true,
  onStatusChange: vi.fn(),
  onRetry: vi.fn(),
};

describe('TerminalPanel', () => {
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });

  it('挂载后建立 WebSocket 连接', async () => {
    const wsCtor = setupWs();
    render(<TerminalPanel {...DEFAULT_PROPS} />);
    await waitFor(() => expect(wsCtor).toHaveBeenCalled());
  });

  it('收到后端 {"type": "error"} 后 status 变 error', async () => {
    setupWs();
    const onStatusChange = vi.fn();
    render(<TerminalPanel {...DEFAULT_PROPS} onStatusChange={onStatusChange} />);
    await waitFor(() => expect(lastWsInstance).toBeTruthy());
    act(() => { lastWsInstance.onopen?.({}); });
    act(() => {
      lastWsInstance.onmessage?.({ data: JSON.stringify({ type: 'error', message: 'auth failed' }) });
    });
    const errorCalls = onStatusChange.mock.calls.filter(c => c[1] === 'error');
    expect(errorCalls.length).toBeGreaterThan(0);
  });

  it('收到后端 {"type": "exit"} 后 status 变 disconnected', async () => {
    setupWs();
    const onStatusChange = vi.fn();
    render(<TerminalPanel {...DEFAULT_PROPS} onStatusChange={onStatusChange} />);
    await waitFor(() => expect(lastWsInstance).toBeTruthy());
    act(() => { lastWsInstance.onopen?.({}); });
    act(() => { lastWsInstance.onmessage?.({ data: JSON.stringify({ type: 'exit' }) }); });
    const dcCalls = onStatusChange.mock.calls.filter(c => c[1] === 'disconnected');
    expect(dcCalls.length).toBeGreaterThan(0);
  });

  it('90s 无任何数据 → 判死 → 主动 close + status error', async () => {
    setupWs();
    const onStatusChange = vi.fn();
    render(<TerminalPanel {...DEFAULT_PROPS} onStatusChange={onStatusChange} />);
    await waitFor(() => expect(lastWsInstance).toBeTruthy());
    act(() => { lastWsInstance.onopen?.({}); });
    // 推进 90s
    act(() => { vi.advanceTimersByTime(90_000); });
    expect(lastWsInstance.close).toHaveBeenCalled();
    const errorCalls = onStatusChange.mock.calls.filter(c => c[1] === 'error');
    expect(errorCalls.length).toBeGreaterThan(0);
  });

  it('收到 pong 重置判活计时器,不会触发 close', async () => {
    setupWs();
    render(<TerminalPanel {...DEFAULT_PROPS} />);
    await waitFor(() => expect(lastWsInstance).toBeTruthy());
    act(() => { lastWsInstance.onopen?.({}); });
    // 每 30s 发一次 pong,共 3 次(< 90s)
    for (let i = 0; i < 3; i++) {
      act(() => { vi.advanceTimersByTime(30_000); });
      act(() => { lastWsInstance.onmessage?.({ data: JSON.stringify({ type: 'pong' }) }); });
    }
    expect(lastWsInstance.close).not.toHaveBeenCalled();
  });

  it('isActive 切换时触发 fit + resize 消息', async () => {
    setupWs();
    const { rerender } = render(<TerminalPanel {...DEFAULT_PROPS} isActive={false} />);
    await waitFor(() => expect(lastWsInstance).toBeTruthy());
    act(() => { lastWsInstance.onopen?.({}); });
    lastWsInstance.send.mockClear();
    rerender(<TerminalPanel {...DEFAULT_PROPS} isActive={true} />);
    // 下一帧 fit + resize 消息
    await waitFor(() => {
      const resize = lastWsInstance.send.mock.calls.find(c => {
        try { return JSON.parse(c[0]).type === 'resize'; } catch { return false; }
      });
      expect(resize).toBeTruthy();
    });
  });
});
```

- [ ] **Step 2: 运行测试,确认失败**

Run: `cd frontend && npx vitest run src/components/Tools/SSHTool/TerminalPanel.test.tsx`
Expected: FAIL — 旧 `TerminalPanel` 不接受新 props。

- [ ] **Step 3: 重写 `TerminalPanel.tsx`**

完全替换 `frontend/src/components/Tools/SSHTool/TerminalPanel.tsx`:

```tsx
import React, { useEffect, useRef, useState } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebLinksAddon } from 'xterm-addon-web-links';
import 'xterm/css/xterm.css';
import { buildSSHWebSocketUrl } from '../../../api/sshToolApi';
import { getAuthToken } from '../../../api/authApi';
import { useToast } from '../../../hooks/useToast';
import { ConnectionStatus, HEARTBEAT_TIMEOUT_MS } from './types';

interface Props {
  tabId: string;
  configId: string;
  /** 变化时触发重连(retry 场景) */
  createdAt: number;
  isActive: boolean;
  onStatusChange: (tabId: string, status: ConnectionStatus) => void;
  /** 当前未使用,留给 TabBar 红点点击调用;本期由 TerminalPanel 内部 retry 即可 */
  onRetry?: (tabId: string) => void;
}

/** 单条 WebSocket 会话:连接、消息分发、心跳判活、清理 */
export const TerminalPanel: React.FC<Props> = ({
  tabId, configId, createdAt, isActive, onStatusChange,
}) => {
  const { addToast } = useToast();
  const terminalRef = useRef<HTMLDivElement | null>(null);
  const terminalInstance = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const lastDataAtRef = useRef<number>(0);
  const heartbeatTimerRef = useRef<number | null>(null);
  // 用于让 isActive effect 感知当前 socket 是否 open
  const socketStateRef = useRef<'closed' | 'open'>('closed');
  // 保留当前状态以便内部判断(避免依赖 onStatusChange 回压)
  const statusRef = useRef<ConnectionStatus>('disconnected');
  // 标记是否已挂载完成,用于 createdAt effect 跳过首次
  const mountedRef = useRef<boolean>(false);

  const setStatus = (s: ConnectionStatus) => {
    statusRef.current = s;
    onStatusChange(tabId, s);
  };

  const stopHeartbeat = () => {
    if (heartbeatTimerRef.current !== null) {
      window.clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  };

  const startHeartbeat = () => {
    stopHeartbeat();
    lastDataAtRef.current = Date.now();
    heartbeatTimerRef.current = window.setInterval(() => {
      if (Date.now() - lastDataAtRef.current >= HEARTBEAT_TIMEOUT_MS) {
        // 判死
        stopHeartbeat();
        socketRef.current?.close();
        setStatus('error');
      }
    }, 5_000);
  };

  const connect = () => {
    const token = getAuthToken();
    if (!token) { addToast('请先登录再连接', 'error'); return; }
    const terminal = terminalInstance.current;
    if (!terminal) return;

    // 关闭旧 socket(若存在)
    socketRef.current?.close();

    const wsUrl = buildSSHWebSocketUrl(configId, token, terminal.cols || 80, terminal.rows || 24);
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;
    socketStateRef.current = 'closed';
    setStatus('connecting');

    socket.onopen = () => {
      socketStateRef.current = 'open';
      setStatus('connected');
      socket.send(JSON.stringify({ type: 'resize', cols: terminal.cols, rows: terminal.rows }));
      terminal.focus();
      startHeartbeat();
    };

    socket.onmessage = (event) => {
      lastDataAtRef.current = Date.now();
      let data = event.data;
      // 尝试解析为控制消息
      if (typeof data === 'string' && data.startsWith('{')) {
        try {
          const msg = JSON.parse(data);
          if (msg && typeof msg === 'object') {
            if (msg.type === 'error') {
              terminal.writeln(`\r\n[错误] ${msg.message ?? ''}`);
              setStatus('error');
              stopHeartbeat();
              socket.close();
              return;
            }
            if (msg.type === 'exit') {
              terminal.writeln('\r\n[会话已结束]');
              setStatus('disconnected');
              stopHeartbeat();
              socket.close();
              return;
            }
            if (msg.type === 'pong') {
              // 纯心跳信号,已记录 lastDataAt,无需渲染
              return;
            }
          }
        } catch {
          // 非 JSON,按普通输出处理
        }
      }
      terminal.write(data);
    };

    socket.onclose = () => {
      socketStateRef.current = 'closed';
      stopHeartbeat();
      // 若当前仍是 connecting/connected,说明异常断开 → error
      if (statusRef.current === 'connecting' || statusRef.current === 'connected') {
        setStatus('error');
      }
    };

    socket.onerror = () => {
      // 不在此处 setStatus,等 onclose 统一处理
    };
  };

  const disconnect = () => {
    stopHeartbeat();
    socketRef.current?.close();
    socketRef.current = null;
    socketStateRef.current = 'closed';
    setStatus('disconnected');
  };

  // 1. 初始化 xterm(仅挂载时一次)
  useEffect(() => {
    if (!terminalRef.current || terminalInstance.current) return;
    const terminal = new Terminal({ cursorBlink: true, fontSize: 13, theme: { background: '#0f172a', foreground: '#e2e8f0' } });
    const fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);
    terminal.loadAddon(new WebLinksAddon());
    terminal.open(terminalRef.current);
    fitAddon.fit();
    terminalInstance.current = terminal;
    fitAddonRef.current = fitAddon;

    const dataDisposable = terminal.onData((data) => {
      const s = socketRef.current;
      if (s && s.readyState === WebSocket.OPEN) s.send(JSON.stringify({ type: 'input', data }));
    });

    // 挂载后立刻连接
    connect();
    mountedRef.current = true;

    return () => {
      dataDisposable.dispose();
      stopHeartbeat();
      socketRef.current?.close();
      socketRef.current = null;
      terminal.dispose();
      terminalInstance.current = null;
      fitAddonRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 2. createdAt 变化 → 重连(retry 场景);首次挂载由上面的 effect 负责
  useEffect(() => {
    if (!mountedRef.current) return;
    if (!terminalInstance.current) return;
    terminalInstance.current.clear();
    connect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createdAt]);

  // 3. isActive 切换:补一次 fit + resize
  useEffect(() => {
    if (!isActive) return;
    const fit = fitAddonRef.current;
    const terminal = terminalInstance.current;
    const socket = socketRef.current;
    if (!fit || !terminal) return;
    // 下一帧 fit,让 DOM 完成 display 切换
    const raf = requestAnimationFrame(() => {
      fit.fit();
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'resize', cols: terminal.cols, rows: terminal.rows }));
      }
    });
    return () => cancelAnimationFrame(raf);
  }, [isActive]);

  // 4. window resize → 仅 active 的 panel 才真正 fit + resize(非 active 时 DOM 尺寸为 0,跳过)
  useEffect(() => {
    const handler = () => {
      if (!isActive) return;
      const fit = fitAddonRef.current;
      const terminal = terminalInstance.current;
      const socket = socketRef.current;
      if (!fit || !terminal) return;
      fit.fit();
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'resize', cols: terminal.cols, rows: terminal.rows }));
      }
    };
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, [isActive]);

  return (
    <div
      ref={terminalRef}
      data-testid={`ssh-terminal-${tabId}`}
      className="w-full h-full bg-slate-900"
      onClick={() => {
        terminalInstance.current?.focus();
        // 点击 error/disconnected 态:自动重连
        if (statusRef.current === 'error' || statusRef.current === 'disconnected') {
          connect();
        }
      }}
    />
  );
};
```

**关键改动点**:
- 去掉了"config 切换 → disconnect + clear"的旧逻辑(由父组件 SSHTool 控制 mount/unmount)。
- 新增 `onStatusChange` 回调,把 `connecting / connected / error / disconnected` 上报给 TabBar。
- 新增心跳定时器:5s 检查一次,若 90s 未收到任何 WS 数据(包括 pong / SSH 输出)则主动 close + 置 error。
- 解析后端 JSON 控制消息:`{"type": "error", "message"}`、`{"type": "exit"}`、`{"type": "pong"}`。
- `isActive` 切换时 `requestAnimationFrame` 后 fit + resize。
- 点击 xterm 区域时,若处于 error/disconnected,自动重连(等价于 TabBar 红点点击)。

- [ ] **Step 4: 运行测试,确认全部通过**

Run: `cd frontend && npx vitest run src/components/Tools/SSHTool/TerminalPanel.test.tsx`
Expected: 6 tests PASS。

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/Tools/SSHTool/TerminalPanel.tsx frontend/src/components/Tools/SSHTool/TerminalPanel.test.tsx
git commit -m "feat(ssh-tool): TerminalPanel 重构为常驻 DOM + 心跳判活 + exit/error 消息"
```

---

## Task 6: 微调 `ConnectionList` 文案(可选)

**Files:**
- Modify: `frontend/src/components/Tools/SSHTool/ConnectionList.tsx`(可选)

- [ ] **Step 1: 检查 `selectedId` 传 `null` 时样式是否正确**

新 `SSHTool` 把 `selectedId` 永远传 `null`。打开浏览器确认侧边栏没有"蓝底高亮"残留;如果有,删掉 `ConnectionList` 里依赖 `selectedId === config.id` 的高亮分支。

Run(在浏览器里打开 `http://localhost:5178/tools/ssh-tool` 看视觉即可):

若高亮残留,修改 `ConnectionList.tsx`:

```tsx
// 把 `selectedId === config.id ? 'bg-blue-600 text-white' : '...'`
// 改为始终使用非选中样式,因为选中态已移到 TabBar
className="p-2 rounded cursor-pointer group flex justify-between items-center text-slate-300 hover:bg-slate-700 hover:text-white"
```

- [ ] **Step 2: 提交(若修改)**

```bash
git add frontend/src/components/Tools/SSHTool/ConnectionList.tsx
git commit -m "refactor(ssh-tool): ConnectionList 去除 selectedId 高亮"
```

---

## Task 7: 后端 `handle_ssh_session` — 心跳 + 错误推送 + executor 读取

**Files:**
- Modify: `backend/app/services/ssh_tool_service.py:366-442`

- [ ] **Step 1: 重写 `handle_ssh_session`**

在 `backend/app/services/ssh_tool_service.py` 中替换 `handle_ssh_session` 方法为:

```python
@staticmethod
async def handle_ssh_session(websocket: WebSocket, config_id: str, token: str, cols: int = 80, rows: int = 24):
    await websocket.accept()
    try:
        auth_service = get_auth_service()
        token_data = auth_service.verify_token_data(token)
        user_id = token_data.user_id
    except ValueError:
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": "Authentication failed"}))
        except Exception:
            pass
        await websocket.close(code=4003, reason="Authentication failed")
        return

    config = SSHToolService._get_config_record(config_id, user_id)
    if not config:
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": "Config not found"}))
        except Exception:
            pass
        await websocket.close(code=4000, reason="Config not found")
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    channel = None
    try:
        column_map = SSHToolService._get_column_map()
        password_value = config.get(column_map["password"])
        private_key_value = config.get(column_map["private_key"])
        passphrase_value = config.get(column_map["passphrase"])
        password = EncryptionUtils.decrypt(password_value) if password_value else None
        private_key = EncryptionUtils.decrypt(private_key_value) if private_key_value else None
        passphrase = EncryptionUtils.decrypt(passphrase_value) if passphrase_value else None
        pkey = SSHToolService._load_private_key(private_key, passphrase) if private_key else None

        ssh.connect(
            hostname=config['host'],
            port=config['port'],
            username=config['username'],
            password=password,
            pkey=pkey,
            timeout=10,
            allow_agent=False,
            look_for_keys=False
        )
        # 防止被 server 端 TCP idle timeout 切断
        ssh.get_transport().set_keepalive(30)

        channel = ssh.invoke_shell(term='xterm-256color', width=cols, height=rows)
        # 设置 5s 超时,避免 recv 永久阻塞,让循环有机会响应 WebSocket 关闭
        channel.settimeout(5.0)
        logger.info("SSH session started: user_id=%s config_id=%s", user_id, config_id)

        stop_event = asyncio.Event()

        async def send_pong():
            """每 30s 向前端发一次 pong,前端以 90s 无数据为死亡判定"""
            while not stop_event.is_set():
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=30.0)
                    return  # stop_event 被 set,退出
                except asyncio.TimeoutError:
                    pass
                try:
                    if websocket.client_state.name == "CONNECTED":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                except Exception:
                    break

        async def receive_from_client():
            while not stop_event.is_set():
                try:
                    data = await websocket.receive_text()
                except WebSocketDisconnect:
                    break
                except Exception:
                    break
                try:
                    message = json.loads(data)
                except json.JSONDecodeError:
                    continue
                message_type = message.get('type')
                if message_type == 'resize' and channel is not None:
                    try:
                        channel.resize_pty(width=int(message.get('cols', cols)), height=int(message.get('rows', rows)))
                    except Exception:
                        pass
                elif message_type == 'input' and channel is not None:
                    try:
                        channel.send(message.get('data', ''))
                    except Exception:
                        break
                elif message_type == 'ping':
                    # 兼容旧协议,后端不再依赖前端 ping
                    pass

        async def send_to_client():
            loop = asyncio.get_event_loop()
            while not stop_event.is_set():
                if channel is None:
                    break
                if channel.exit_status_ready():
                    try:
                        await websocket.send_text(json.dumps({"type": "exit"}))
                    except Exception:
                        pass
                    break
                try:
                    # 在 executor 里跑阻塞的 recv,settimeout(5.0) 保证最多阻塞 5s
                    data = await loop.run_in_executor(None, channel.recv, 4096)
                except Exception as e:
                    # socket.timeout 是正常的,继续循环
                    if 'timed out' in str(e).lower() or 'timeout' in str(e).lower():
                        continue
                    # 其他异常视为会话结束
                    break
                if not data:
                    try:
                        await websocket.send_text(json.dumps({"type": "exit"}))
                    except Exception:
                        pass
                    break
                try:
                    await websocket.send_text(data.decode('utf-8', errors='ignore'))
                except Exception:
                    break

        pong_task = asyncio.create_task(send_pong())
        try:
            await asyncio.gather(receive_from_client(), send_to_client())
        finally:
            stop_event.set()
            pong_task.cancel()
            try:
                await pong_task
            except (asyncio.CancelledError, Exception):
                pass
    except Exception as e:
        logger.error("SSH connection failed: %s", str(e))
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
        try:
            await websocket.close(code=4000, reason="SSH connection failed")
        except Exception:
            pass
    finally:
        try:
            ssh.close()
        except Exception:
            pass
        logger.info("SSH session closed: user_id=%s config_id=%s", user_id, config_id)
```

**关键改动点**:
1. `ssh.get_transport().set_keepalive(30)` — SSH transport 心跳。
2. `channel.settimeout(5.0)` — `recv` 最多阻塞 5s,让循环能响应 `stop_event`。
3. `send_pong` 协程 — 每 30s 发 `{"type": "pong"}`,`stop_event` 触发后退出。
4. `send_to_client` 改为 `run_in_executor` + `recv`,不再 10ms 轮询。
5. channel 关闭 / `recv` 返回空 → 先发 `{"type": "exit"}`,再退出循环。
6. 所有 SSH 连接失败场景(鉴权 / config 缺失 / ssh.connect 异常)都先发 `{"type": "error", "message": "..."}`,再 close。
7. `receive_from_client` 用 `stop_event.is_set()` 退出,与 `send_to_client` 对齐。

- [ ] **Step 2: 本地启动后端,确认无启动报错**

Run: `python dev_services.py restart backend`
Expected: 启动日志无报错,`uvicorn` 正常监听。

- [ ] **Step 3: 提交**

```bash
git add backend/app/services/ssh_tool_service.py
git commit -m "feat(ssh-tool): handle_ssh_session 增加心跳/错误推送/executor 读取"
```

---

## Task 8: 后端单元测试 — 心跳 / 错误推送 / 断开清理

**Files:**
- Create: `backend/tests/test_ssh_session_heartbeat.py`

- [ ] **Step 1: 编写测试**

创建 `backend/tests/test_ssh_session_heartbeat.py`:

```python
"""
handle_ssh_session 单元测试
覆盖:心跳 pong 发送 / SSH 失败时 error 推送 / WebSocket 断开后 ssh.close() 被调用
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ssh_tool_service import SSHToolService


class FakeWebSocket:
    def __init__(self):
        self.sent = []
        self.closed = False
        self.close_code = None
        self.client_state = MagicMock()
        self.client_state.name = "CONNECTED"
        self._receive_queue = asyncio.Queue()
        # 默认让 receive_text 永久阻塞,模拟客户端不发送数据
        self._receive_block = asyncio.Event()

    async def send_text(self, data):
        self.sent.append(data)

    async def receive_text(self):
        # 等到 close 或显式 push
        await self._receive_block.wait()
        from fastapi import WebSocketDisconnect
        raise WebSocketDisconnect()

    async def close(self, code=1000, reason=""):
        self.closed = True
        self.close_code = code
        self._receive_block.set()
        self.client_state.name = "DISCONNECTED"

    def push_receive(self, text):
        """测试用例注入一条客户端消息(本测试未用)"""
        asyncio.create_task(self._feed(text))

    async def _feed(self, text):
        # 简化:不实际入队,只保留接口
        pass


@pytest.mark.asyncio
async def test_ssh_connect_failure_pushes_error_message_then_closes():
    """ssh.connect 抛错 → 后端先发 type=error,再 close"""
    ws = FakeWebSocket()

    fake_config = {
        'id': 'cfg-x', 'host': 'bad-host', 'port': 22, 'username': 'u',
        'password_encrypted': None, 'private_key_encrypted': None, 'passphrase_encrypted': None,
    }

    with patch.object(SSHToolService, '_get_config_record', return_value=fake_config), \
         patch.object(SSHToolService, '_get_column_map', return_value={
             'password': 'password_encrypted',
             'private_key': 'private_key_encrypted',
             'passphrase': 'passphrase_encrypted',
         }), \
         patch('app.services.ssh_tool_service.get_auth_service') as gauth, \
         patch('app.services.ssh_tool_service.EncryptionUtils.decrypt', return_value=None), \
         patch('app.services.ssh_tool_service.paramiko.SSHClient') as SSH:
        auth_svc = MagicMock()
        auth_svc.verify_token_data.return_value = MagicMock(user_id='u1')
        gauth.return_value = auth_svc
        ssh_inst = MagicMock()
        ssh_inst.connect.side_effect = OSError("Connection refused")
        SSH.return_value = ssh_inst

        await SSHToolService.handle_ssh_session(ws, 'cfg-x', 'fake-token')

    # 发了 type=error
    error_msgs = [json.loads(m) for m in ws.sent if m.startswith('{')]
    assert any(m.get('type') == 'error' and 'Connection refused' in m.get('message', '') for m in error_msgs)
    # close 被调用
    assert ws.closed


@pytest.mark.asyncio
async def test_websocket_disconnect_triggers_ssh_close():
    """WebSocket 断开后,ssh.close() 必须被调用"""
    ws = FakeWebSocket()

    fake_config = {
        'id': 'cfg-x', 'host': 'h', 'port': 22, 'username': 'u',
        'password_encrypted': None, 'private_key_encrypted': None, 'passphrase_encrypted': None,
    }

    channel = MagicMock()
    channel.recv.side_effect = TimeoutError("timed out")  # 让 send_to_client 一直循环直到 stop_event
    channel.exit_status_ready.return_value = False
    channel.settimeout = MagicMock()

    ssh_inst = MagicMock()
    ssh_inst.invoke_shell.return_value = channel
    transport = MagicMock()
    ssh_inst.get_transport.return_value = transport

    # 让 receive_text 立刻抛 WebSocketDisconnect,模拟客户端断开
    async def recv_then_disconnect():
        from fastapi import WebSocketDisconnect
        raise WebSocketDisconnect()

    ws.receive_text = recv_then_disconnect

    with patch.object(SSHToolService, '_get_config_record', return_value=fake_config), \
         patch.object(SSHToolService, '_get_column_map', return_value={
             'password': 'password_encrypted',
             'private_key': 'private_key_encrypted',
             'passphrase': 'passphrase_encrypted',
         }), \
         patch('app.services.ssh_tool_service.get_auth_service') as gauth, \
         patch('app.services.ssh_tool_service.EncryptionUtils.decrypt', return_value=None), \
         patch('app.services.ssh_tool_service.paramiko.SSHClient') as SSH:
        auth_svc = MagicMock()
        auth_svc.verify_token_data.return_value = MagicMock(user_id='u1')
        gauth.return_value = auth_svc
        SSH.return_value = ssh_inst

        await SSHToolService.handle_ssh_session(ws, 'cfg-x', 'fake-token')

    ssh_inst.close.assert_called_once()


@pytest.mark.asyncio
async def test_transport_keepalive_is_set_after_connect():
    """ssh.connect 成功后必须调用 transport.set_keepalive(30),防止 server TCP idle 切断"""
    ws = FakeWebSocket()

    fake_config = {
        'id': 'cfg-x', 'host': 'h', 'port': 22, 'username': 'u',
        'password_encrypted': None, 'private_key_encrypted': None, 'passphrase_encrypted': None,
    }

    channel = MagicMock()
    channel.recv.side_effect = TimeoutError("timed out")
    channel.exit_status_ready.return_value = False
    channel.settimeout = MagicMock()

    transport = MagicMock()
    ssh_inst = MagicMock()
    ssh_inst.invoke_shell.return_value = channel
    ssh_inst.get_transport.return_value = transport

    async def recv_then_disconnect():
        await asyncio.sleep(0.05)
        from fastapi import WebSocketDisconnect
        raise WebSocketDisconnect()
    ws.receive_text = recv_then_disconnect

    with patch.object(SSHToolService, '_get_config_record', return_value=fake_config), \
         patch.object(SSHToolService, '_get_column_map', return_value={
             'password': 'password_encrypted',
             'private_key': 'private_key_encrypted',
             'passphrase': 'passphrase_encrypted',
         }), \
         patch('app.services.ssh_tool_service.get_auth_service') as gauth, \
         patch('app.services.ssh_tool_service.EncryptionUtils.decrypt', return_value=None), \
         patch('app.services.ssh_tool_service.paramiko.SSHClient') as SSH:
        auth_svc = MagicMock()
        auth_svc.verify_token_data.return_value = MagicMock(user_id='u1')
        gauth.return_value = auth_svc
        SSH.return_value = ssh_inst

        await SSHToolService.handle_ssh_session(ws, 'cfg-x', 'fake-token')

    transport.set_keepalive.assert_called_once_with(30)
    channel.settimeout.assert_called_once_with(5.0)
```

> 注:三个测试都是 deterministic、毫秒级完成,无需真实 sleep 30s。心跳周期性发送 pong 的覆盖留给端到端手动验证(在 Task 9 闲置 10 分钟步骤中确认)。

- [ ] **Step 2: 运行测试**

Run: `cd backend && python -m pytest tests/test_ssh_session_heartbeat.py -v`
Expected: 3 个用例全部 PASS。

- [ ] **Step 3: 提交**

```bash
git add backend/tests/test_ssh_session_heartbeat.py
git commit -m "test(ssh-tool): 新增后端心跳 / 错误推送 / 清理单元测试"
```

---

## Task 9: 手动端到端验证(浏览器)

**Files:** 无(仅验证)

- [ ] **Step 1: 启动前后端**

```bash
python dev_services.py restart
```

确认:
- 前端 `http://localhost:5178` 可访问
- 后端日志无报错

- [ ] **Step 2: 核心流程**

1. 打开浏览器访问 `http://localhost:5178/tools/ssh-tool`,登录。
2. 点侧边栏一条 SSH 连接 → 看到新 tab 出现 + 绿点 → 输入命令,正常交互。
3. 再点同一连接 → 出现第 2 个 tab;切换 tab,原 tab 的终端输出完整保留。
4. 切换到另一个工具页(如 OCR),再回到 SSH 工具 → 所有 tab 仍在,终端输出保留。
5. 关闭某个 tab → 若处于 connected 弹确认,取消则保持,确认则 tab 消失。
6. 关闭最后一个 tab → 右侧显示空态引导。
7. 开 20 个 tab 后再点侧边栏 → toast 提示"最多保留 20 个 SSH 会话"。
8. 关闭浏览器窗口 → 服务端日志显示所有 `SSH session closed`。

- [ ] **Step 3: 心跳保活**

1. 开一个 tab,输入 `top` 或 `tail -f /var/log/...`,切到别的 tab 闲置 ≥ 10 分钟。
2. 切回来 → 输出仍为最新,WebSocket 未断。

- [ ] **Step 4: 异常场景**

1. 手动停掉后端 → 前端 TabBar 变红点(error),不自动重连。
2. 重启后端 → 点击红点,新 tab 重连(注意:是**新 SSH 会话**,不恢复旧会话)。
3. 服务端 SSH 侧执行 `exit` → 前端 TabBar 灰点(disconnected),可重连。

- [ ] **Step 5: 全部通过后提交**(本次无代码改动,仅验证)

---

## 任务依赖与执行顺序

```text
Task 1 (types) ─┐
                ├──→ Task 3 (TabBar) ─┐
Task 2 (i18n) ──┤                     ├──→ Task 4 (SSHTool) ─→ Task 6 (ConnectionList 微调)
                └──→ Task 5 (TerminalPanel) ──────────────────┘
                                                             ↓
                                              Task 7 (后端 handle_ssh_session)
                                                             ↓
                                              Task 8 (后端测试)
                                                             ↓
                                              Task 9 (端到端手动验证)
```

并行机会:Task 1 + Task 2 可并行;Task 3 + Task 5 可并行;Task 7 + Task 8 在后端侧可独立进行。

---

## 完成标准

- 所有前端单元测试 PASS(Vitest)。
- 所有后端单元测试 PASS(pytest)。
- Task 9 的 5 步端到端手动验证全部通过。
- 浏览器 Console 无错误。
- 服务端日志在浏览器窗口关闭后正确打印所有 session close 记录。
