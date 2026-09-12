import { useEffect, useMemo, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { Dialog, DialogContent, DialogTitle } from '../ui/Dialog';
import { fetchTools } from '../../services/api';
import { buildCommandItems, filterCommands, PAGE_ITEMS, type CommandItem } from '../../lib/commandPalette';
import { OPEN_COMMAND_PALETTE_EVENT } from '../../lib/navigation';

/**
 * 全局 ⌘K 命令面板：搜索工具与页面并跳转。
 * 打开方式：Cmd/Ctrl+K 或 window 事件 'open-command-palette'（Header 移动端搜索按钮共用）。
 */
export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [tools, setTools] = useState<CommandItem[]>([]);
  const [activeIndex, setActiveIndex] = useState(0);
  const navigate = useNavigate();

  // 工具列表懒加载：首次打开面板时拉取一次，失败时仅显示页面入口
  useEffect(() => {
    if (!open || tools.length > 0) return;
    fetchTools('pc')
      .then((data) => setTools(buildCommandItems(data)))
      .catch(() => {
        /* 拉取失败时保持仅页面入口，下次打开重试 */
      });
  }, [open, tools.length]);

  // 全局快捷键（Cmd/Ctrl+K 切换）与外部打开事件监听
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    const onOpen = () => setOpen(true);
    window.addEventListener('keydown', onKey);
    window.addEventListener(OPEN_COMMAND_PALETTE_EVENT, onOpen);
    return () => {
      window.removeEventListener('keydown', onKey);
      window.removeEventListener(OPEN_COMMAND_PALETTE_EVENT, onOpen);
    };
  }, []);

  // 搜索词变化时重置键盘选中项
  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  const results = useMemo(
    () => filterCommands([...tools, ...PAGE_ITEMS], query),
    [tools, query]
  );

  // 键盘选中项兜底：结果集变短时不越界
  const currentIndex = Math.min(activeIndex, Math.max(0, results.length - 1));

  const go = (item: CommandItem) => {
    setOpen(false);
    setQuery('');
    // 工具走工作区 state 跳转（与 App.tsx handleToolClick 约定一致），页面走路由
    if (item.toolId) {
      navigate('/workspace', { state: { openToolId: item.toolId } });
    } else {
      navigate(item.route);
    }
  };

  // 输入框键盘导航：上下选择、回车确认跳转
  const onInputKeyDown = (e: ReactKeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const item = results[currentIndex];
      if (item) go(item);
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (!o) setQuery('');
      }}
    >
      {/* pr-10 为右上角自带关闭按钮留位，避免与 Esc 徽标重叠 */}
      <DialogContent className="glass-panel rounded-2xl max-w-lg p-0 top-[20%] translate-y-0">
        {/* 无障碍：Radix 要求 Dialog 有可访问名称，视觉上隐藏 */}
        <DialogTitle className="sr-only">命令面板</DialogTitle>
        <div className="flex items-center gap-3 border-b border-glass-border px-4 py-3 pr-10">
          <Search className="w-4 h-4 text-ink-faint" />
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onInputKeyDown}
            placeholder="搜索工具、页面…"
            className="w-full bg-transparent text-sm outline-none placeholder:text-ink-faint"
          />
          <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-glass-bg border border-glass-border text-ink-faint">
            Esc
          </kbd>
        </div>
        <ul className="max-h-80 overflow-y-auto p-2">
          {results.length === 0 && (
            <li className="px-3 py-6 text-center text-sm text-ink-faint">无匹配结果</li>
          )}
          {results.map((item, index) => (
            <li key={item.id}>
              <button
                onClick={() => go(item)}
                onMouseEnter={() => setActiveIndex(index)}
                ref={(node) => {
                  // 选中项滚动进可视区域，保证键盘导航可见
                  if (node && index === currentIndex) {
                    node.scrollIntoView({ block: 'nearest' });
                  }
                }}
                className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${
                  index === currentIndex ? 'bg-glass-bg-strong' : 'hover:bg-glass-bg-strong'
                }`}
              >
                <span className="text-xs text-ink-faint mr-2">{item.group}</span>
                <span className="text-sm text-ink">{item.label}</span>
                {item.hint && <span className="block text-xs text-ink-faint truncate">{item.hint}</span>}
              </button>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  );
}
