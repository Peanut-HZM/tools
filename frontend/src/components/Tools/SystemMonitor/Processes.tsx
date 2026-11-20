// frontend/src/components/Tools/SystemMonitor/Processes.tsx
import { useEffect, useState, useCallback, useMemo } from 'react';
import { RefreshCw, Cpu, MemoryStick, Layers, Activity, ChevronDown, ChevronUp } from 'lucide-react';
import { useMonitorStore } from '../../../stores/monitorStore';
import * as monitorApi from '../../../api/monitorApi';
import type {
  MonitorProcess,
  ProcessListResponse,
  ProcessSummary,
  ProcessTypeSummary,
} from '../../../api/monitorApi';
import ServerSelector from './components/ServerSelector';
import { ConfirmDialog } from '@/components/ui/ConfirmDialog';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";

const KNOWN_TYPES = ['all', 'FastAPI', 'Django', 'Flask', 'Celery', 'Gunicorn', 'Python',
  'Java', 'Spring Boot', 'Node.js', 'Vite', 'npm', 'Nginx', 'MySQL', 'PostgreSQL', 'Redis',
  'Docker', 'Go', 'Browser', 'Electron', 'Other'];

function fmtBytes(v: number): string {
  if (!v) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(v) / Math.log(1024));
  return `${(v / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

/** 类型 → 进度条颜色（按 CPU 份额可视化） */
function barColor(share: number): string {
  if (share >= 50) return 'bg-accent-danger';
  if (share >= 20) return 'bg-accent-warning';
  return 'bg-accent-success';
}

/** 顶部汇总指标卡 */
function SummaryCards({ summary }: { summary: ProcessSummary }) {
  const items = [
    {
      icon: Layers,
      label: '进程总数',
      value: summary.process_count.toLocaleString('zh-CN'),
      hint: `${summary.thread_count_total.toLocaleString('zh-CN')} 个线程`,
    },
    {
      icon: Cpu,
      label: 'CPU 占用',
      value: `${summary.cpu_percent_of_machine}%`,
      hint: `整机占用 · 累计 ${summary.cpu_percent_total}%（${summary.logical_cpus} 核累加）`,
    },
    {
      icon: MemoryStick,
      label: '内存占用',
      value: fmtBytes(summary.memory_rss_total),
      hint: `占物理内存 ${summary.memory_percent_total}%`,
    },
    {
      icon: Activity,
      label: 'CPU 最高',
      value: summary.top_cpu[0]
        ? `${summary.top_cpu[0].cpu_percent}%`
        : '—',
      hint: summary.top_cpu[0]?.name ?? '暂无数据',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-2 lg:grid-cols-4">
      {items.map(({ icon: Icon, label, value, hint }) => (
        <Card key={label} className="bg-canvas">
          <CardContent className="p-3">
            <div className="flex items-center gap-1.5 text-[11px] text-ink-faint">
              <Icon className="h-3.5 w-3.5" aria-hidden />
              {label}
            </div>
            <div className="mt-1 text-lg font-semibold tabular-nums text-ink">{value}</div>
            <div className="mt-0.5 truncate text-[11px] text-ink-faint" title={hint}>
              {hint}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/** 类型分布：按 CPU 份额排序，带占比条 */
function TypeBreakdown({ groups }: { groups: ProcessTypeSummary[] }) {
  const [expanded, setExpanded] = useState(false);
  const totalCpu = groups.reduce((s, g) => s + g.cpu_percent, 0) || 1;

  // 折叠时只显示前 6 个，避免长列表把表格挤下去
  const shown = expanded ? groups : groups.slice(0, 6);

  return (
    <Card className="bg-canvas">
      <CardContent className="p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium text-ink">按类型汇总</span>
          <span className="text-[11px] text-ink-faint">
            {groups.length} 种类型 · CPU 合计 {totalCpu.toFixed(1)}%
          </span>
        </div>
        <div className="space-y-1.5">
          {shown.map((g) => {
            const share = (g.cpu_percent / totalCpu) * 100;
            return (
              <div key={g.type} className="flex items-center gap-2 text-[11px]">
                <span className="w-20 shrink-0 truncate text-ink-muted" title={g.type}>
                  {g.type}
                </span>
                <span className="w-9 shrink-0 text-right tabular-nums text-ink-faint">
                  {g.count}
                </span>
                <div className="h-1.5 min-w-0 flex-1 overflow-hidden rounded-full bg-surface-2">
                  <div
                    className={`h-full rounded-full ${barColor(share)}`}
                    style={{ width: `${Math.max(share, 1)}%` }}
                  />
                </div>
                <span className="w-14 shrink-0 text-right tabular-nums text-ink-muted">
                  {g.cpu_percent.toFixed(1)}%
                </span>
                <span className="w-16 shrink-0 text-right tabular-nums text-ink-faint">
                  {fmtBytes(g.memory_rss)}
                </span>
              </div>
            );
          })}
        </div>
        {groups.length > 6 && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="mt-2 flex w-full items-center justify-center gap-1 text-[11px] text-ink-faint hover:text-ink-muted"
          >
            {expanded ? (
              <>
                <ChevronUp className="h-3 w-3" aria-hidden /> 收起
              </>
            ) : (
              <>
                <ChevronDown className="h-3 w-3" aria-hidden /> 展开其余 {groups.length - 6} 种
              </>
            )}
          </button>
        )}
      </CardContent>
    </Card>
  );
}

/** 页签④进程管理：顶部汇总 + 类型分布 + 列表/搜索/排序/分页/结束 */
export default function Processes() {
  const { servers, selectedServerId, setSelectedServerId } = useMonitorStore();
  const [data, setData] = useState<ProcessListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [search, setSearch] = useState('');
  const [projectType, setProjectType] = useState('all');
  const [sortBy, setSortBy] = useState('cpu_percent');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [loading, setLoading] = useState(false);
  const [killing, setKilling] = useState<MonitorProcess | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!selectedServerId) return;
    setLoading(true);
    setError('');
    try {
      const res = await monitorApi.getProcesses(selectedServerId, {
        sort_by: sortBy, sort_order: sortOrder, search: search || undefined,
        project_type: projectType, page, page_size: pageSize,
      });
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '加载失败');
    } finally {
      setLoading(false);
    }
  }, [selectedServerId, sortBy, sortOrder, search, projectType, page, pageSize]);

  useEffect(() => { void load(); }, [load]);

  const processes = data?.processes ?? [];
  const total = data?.total ?? 0;
  const summary = data?.summary;
  // 类型汇总在后端是全量口径；筛选/搜索时后端返回的仍是当前过滤结果，按需展示
  const typeGroups = useMemo(() => data?.type_summary ?? [], [data]);

  const handleSort = (key: string) => {
    if (sortBy === key) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(key);
      setSortOrder('desc');
    }
    setPage(1);
  };

  const handleKill = async () => {
    if (!killing || !selectedServerId) return;
    try {
      await monitorApi.killProcess(selectedServerId, killing.pid);
      setKilling(null);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '结束进程失败');
      setKilling(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const sortIndicator = (key: string) =>
    sortBy === key ? (sortOrder === 'desc' ? ' ↓' : ' ↑') : '';

  return (
    <div className="space-y-3">
      {/* ---------- 顶部：总览汇总 ---------- */}
      {summary && <SummaryCards summary={summary} />}

      {/* ---------- 顶部：类型分布 + TOP 榜 ---------- */}
      <div className="grid gap-3 lg:grid-cols-2">
        {typeGroups.length > 0 && <TypeBreakdown groups={typeGroups} />}
        {summary && (
          <Card className="bg-canvas">
            <CardContent className="p-3">
              <div className="mb-2 text-xs font-medium text-ink">占用 TOP 5</div>
              <div className="grid gap-2 sm:grid-cols-2">
                <div>
                  <div className="mb-1 flex items-center gap-1 text-[11px] text-ink-faint">
                    <Cpu className="h-3 w-3" aria-hidden /> CPU
                  </div>
                  {summary.top_cpu.map((p) => (
                    <div key={`c-${p.pid}`} className="flex items-center gap-1.5 text-[11px]">
                      <span className="min-w-0 flex-1 truncate text-ink-muted" title={p.name}>
                        {p.name}
                      </span>
                      <span className="shrink-0 tabular-nums text-ink">
                        {p.cpu_percent.toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
                <div>
                  <div className="mb-1 flex items-center gap-1 text-[11px] text-ink-faint">
                    <MemoryStick className="h-3 w-3" aria-hidden /> 内存
                  </div>
                  {summary.top_memory.map((p) => (
                    <div key={`m-${p.pid}`} className="flex items-center gap-1.5 text-[11px]">
                      <span className="min-w-0 flex-1 truncate text-ink-muted" title={p.name}>
                        {p.name}
                      </span>
                      <span className="shrink-0 tabular-nums text-ink">
                        {fmtBytes(p.memory_rss)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* ---------- 筛选栏 ---------- */}
      <div className="flex flex-wrap items-center gap-2">
        <ServerSelector servers={servers} value={selectedServerId} onChange={setSelectedServerId} />
        <Input
          className="min-w-[160px] flex-1"
          placeholder="搜索进程名或命令行"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        />
        <Select value={projectType} onValueChange={(v) => { setProjectType(v); setPage(1); }}>
          <SelectTrigger className="w-[140px] rounded-lg border border-border bg-canvas">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {KNOWN_TYPES.map((t) => (
              <SelectItem key={t} value={t}>{t === 'all' ? '全部类型' : t}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="secondary" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {loading ? '刷新中…' : '刷新'}
        </Button>
      </div>

      {error && <div className="text-sm text-accent-danger">{error}</div>}

      {/* ---------- 进程列表 ---------- */}
      <Card className="bg-canvas">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[860px] text-xs">
              <thead>
                <tr className="border-b border-border text-ink-faint">
                  <th className="cursor-pointer px-3 py-2 text-left hover:text-ink-muted" onClick={() => handleSort('pid')}>
                    PID{sortIndicator('pid')}
                  </th>
                  <th className="cursor-pointer px-3 py-2 text-left hover:text-ink-muted" onClick={() => handleSort('name')}>
                    进程名{sortIndicator('name')}
                  </th>
                  <th className="hidden px-3 py-2 text-left md:table-cell">用户</th>
                  <th className="cursor-pointer px-3 py-2 text-right hover:text-ink-muted" onClick={() => handleSort('cpu_percent')}>
                    CPU%{sortIndicator('cpu_percent')}
                  </th>
                  <th className="cursor-pointer px-3 py-2 text-right hover:text-ink-muted" onClick={() => handleSort('memory_percent')}>
                    内存%{sortIndicator('memory_percent')}
                  </th>
                  <th className="hidden cursor-pointer px-3 py-2 text-right hover:text-ink-muted lg:table-cell" onClick={() => handleSort('memory_rss')}>
                    内存{sortIndicator('memory_rss')}
                  </th>
                  <th className="hidden cursor-pointer px-3 py-2 text-right hover:text-ink-muted xl:table-cell" onClick={() => handleSort('num_threads')}>
                    线程{sortIndicator('num_threads')}
                  </th>
                  <th className="hidden px-3 py-2 text-left xl:table-cell">启动时间</th>
                  <th className="px-3 py-2 text-left">类型</th>
                  <th className="px-3 py-2 text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {processes.map((p) => (
                  <tr key={p.pid} className="border-b border-border/50 last:border-0 hover:bg-surface-1/30">
                    <td className="px-3 py-2 tabular-nums text-ink-muted">{p.pid}</td>
                    <td className="max-w-[260px] truncate px-3 py-2 text-ink" title={p.command_line || p.name}>
                      {p.name}
                    </td>
                    <td className="hidden px-3 py-2 text-ink-faint md:table-cell">{p.username}</td>
                    <td className={`px-3 py-2 text-right tabular-nums ${
                      p.cpu_percent >= 50 ? 'font-medium text-accent-danger'
                        : p.cpu_percent >= 20 ? 'text-accent-warning'
                        : 'text-ink-muted'
                    }`}>
                      {p.cpu_percent.toFixed(1)}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-muted">
                      {p.memory_percent.toFixed(1)}
                    </td>
                    <td className="hidden px-3 py-2 text-right tabular-nums text-ink-muted lg:table-cell">
                      {fmtBytes(p.memory_rss)}
                    </td>
                    <td className="hidden px-3 py-2 text-right tabular-nums text-ink-faint xl:table-cell">
                      {p.num_threads}
                    </td>
                    <td className="hidden px-3 py-2 text-ink-faint xl:table-cell">{p.create_time}</td>
                    <td className="px-3 py-2">
                      <Badge variant="tint-success" className="text-[10px]">{p.project_type}</Badge>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <button
                        type="button"
                        className="text-[11px] text-accent-danger/80 hover:text-accent-danger"
                        onClick={() => setKilling(p)}
                      >
                        结束
                      </button>
                    </td>
                  </tr>
                ))}
                {processes.length === 0 && !loading && (
                  <tr>
                    <td colSpan={10} className="px-3 py-10 text-center text-ink-faint">
                      暂无进程
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ---------- 分页 ---------- */}
      {total > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-faint">
          <span>
            共 {total} 个进程
            {summary && (
              <span className="ml-2 text-ink-faint/80">
                （全量 CPU {summary.cpu_percent_total}% · 内存 {fmtBytes(summary.memory_rss_total)}）
              </span>
            )}
          </span>
          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              上一页
            </Button>
            <span className="tabular-nums">{page} / {totalPages}</span>
            <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
              下一页
            </Button>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!killing}
        onOpenChange={(open) => { if (!open) setKilling(null); }}
        title="结束进程"
        description={`确定结束进程 ${killing?.pid}（${killing?.name}）？该操作不可撤销。`}
        confirmText="结束"
        variant="destructive"
        onConfirm={handleKill}
      />
    </div>
  );
}
