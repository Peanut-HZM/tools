# Token Usage 操作行精简 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Token Usage 页面顶部操作行从 ~60px 压缩到 ~32px，DataFreshnessBadge 精简为内联文本+Tooltip，按钮改为纯图标，确保单行不换行。

**Architecture:** 修改单个文件 `frontend/src/components/Tools/TokenUsage.tsx`，替换 `DataFreshnessBadge` 卡片组件为内联状态行，按钮组去除文字保留图标，使用 `flex-nowrap` + `flex-shrink-0` 确保单行布局。

**Tech Stack:** React 18, TypeScript, Tailwind CSS, lucide-react.

---

## File Structure

- Modify `frontend/src/components/Tools/TokenUsage.tsx`: 替换 `DataFreshnessBadge` 组件为 `CompactStatusBar`，按钮组改为纯图标，整行改为 `flex-nowrap`

---

## Task 1: 精简操作行布局

**Files:**
- Modify: `frontend/src/components/Tools/TokenUsage.tsx`

- [ ] **Step 1: 将 `DataFreshnessBadge` 替换为 `CompactStatusBar` 内联组件**

在 `DataFreshnessBadge` 函数之后添加新的 `CompactStatusBar` 函数：

```tsx
function CompactStatusBar({
  syncMeta,
  cached,
  refreshing,
  refreshError,
  onRefresh,
}: {
  syncMeta: SyncMeta | null;
  cached: boolean;
  refreshing: boolean;
  refreshError: string | null;
  onRefresh: () => void;
}) {
  const stale = Boolean(syncMeta?.is_stale);
  const locked = Boolean(syncMeta?.refresh_lock?.locked);
  const ttl = syncMeta?.cache_ttl_seconds ?? 0;

  const buildTooltip = () => {
    const lines: string[] = [];
    lines.push(`状态：${refreshing ? '后台更新中' : refreshError ? '刷新失败' : locked ? '其他窗口正在更新' : stale ? '数据已过期' : cached ? '缓存有效' : '数据库聚合'}`);
    lines.push(`最后同步：${formatDateTime(syncMeta?.last_success_at)}`);
    if (ttl > 0) lines.push(`缓存有效期：剩余 ${Math.ceil(ttl / 60)} 分钟`);
    if (syncMeta?.stale_reason) lines.push(syncMeta.stale_reason);
    if (refreshError) lines.push(refreshError);
    return lines.join('\n');
  };

  const textClass = refreshing || locked
    ? 'text-sky-300'
    : refreshError || stale
      ? 'text-amber-300'
      : 'text-emerald-300';

  return (
    <span className="inline-flex min-w-0 flex-1 items-center gap-1.5 text-xs" title={buildTooltip()}>
      {refreshing ? (
        <Loader2 className="h-3.5 w-3.5 flex-shrink-0 animate-spin text-sky-300" />
      ) : refreshError || stale ? (
        <AlertTriangle className={`h-3.5 w-3.5 flex-shrink-0 ${textClass}`} />
      ) : (
        <Clock className={`h-3.5 w-3.5 flex-shrink-0 ${textClass}`} />
      )}
      <span className={`truncate ${textClass}`}>
        {refreshing ? '后台更新中' : refreshError ? '刷新失败' : `最后同步 ${formatRelativeTime(syncMeta?.last_success_at)}`}
      </span>
    </span>
  );
}
```

- [ ] **Step 2: 将按钮组改为纯图标按钮**

在 JSX 中替换 `DataFreshnessBadge` 使用为 `CompactStatusBar`，并将按钮组改为纯图标：

```tsx
        <div className="flex flex-nowrap items-center gap-2">
          <CompactStatusBar
            syncMeta={syncMeta}
            cached={cached}
            refreshing={refreshing || backgroundRefreshing}
            refreshError={refreshError}
            onRefresh={handleRefresh}
          />
          <button
            onClick={handleRefresh}
            disabled={loading || refreshing}
            className="inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            title="刷新"
          >
            {refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </button>
          <button
            onClick={exportCSV}
            disabled={!items.length || loading}
            className="inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            title="导出"
          >
            <Download className="h-4 w-4" />
          </button>
          <button
            onClick={handleClearData}
            disabled={loading || clearing}
            className="inline-flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md border border-slate-700 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
            title="清理"
          >
            {clearing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
          </button>
        </div>
```

- [ ] **Step 3: 构建并验证**

```bash
cd frontend
npm run build
```

预期：构建成功。

- [ ] **Step 4: 浏览器验证**

确保 dev-services 运行，打开 http://localhost:5178/tools/token-usage 验证：
- 操作行在所有窗口宽度下不换行
- 行高不超过 36px
- 图标按钮有 hover tooltip 提示文字
- 状态文本 hover 显示详细信息
- 异常状态颜色正确区分（stale 为琥珀色、正常为绿色、刷新中为天蓝色）

- [ ] **Step 5: 推送**

```bash
git add frontend/src/components/Tools/TokenUsage.tsx
git commit -m "fix: 精简 token-usage 操作行布局，防止换行"
```

---

## Self-Review

- **Spec coverage:** 全部三点（DataFreshnessBadge 精简、按钮精简、整行不换行）均已覆盖。
- **Placeholder scan:** 无 TBD/TODO，所有代码均在计划中给出。
- **Type consistency:** `CompactStatusBar` props 类型与已有类型 `SyncMeta` 一致。
