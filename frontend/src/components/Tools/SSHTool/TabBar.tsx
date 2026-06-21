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
                aria-label={t.ssh.closeTab}
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
