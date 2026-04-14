import { useState, useEffect, useCallback, useRef, Fragment } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE_URL } from '../../config/api';

// 系统信息
interface SystemInfo {
  hostname: string;
  os: string;
  os_version: string;
  platform: string;
  python_version: string;
  boot_time: string;
  uptime: string;
  cpu: {
    model: string;
    physical_cores: number;
    logical_cores: number;
    frequency: number | null;
  };
  memory: {
    total_gb: number;
  };
  disk: {
    total_gb: number;
  };
}

interface DiskPartition {
  device: string;
  mountpoint: string;
  fstype: string;
  total_gb: number;
  used_gb: number;
  free_gb: number;
  percent: number;
}

interface ResourceUsage {
  cpu: { percent: number; per_cpu: number[] };
  memory: { total_gb: number; available_gb: number; used_gb: number; percent: number };
  swap: { total_gb: number; used_gb: number; free_gb: number; percent: number };
  disk: { total_gb: number; used_gb: number; free_gb: number; percent: number; partitions: DiskPartition[] };
  network: { bytes_sent: number; bytes_recv: number };
  disk_io: { read_bytes: number; write_bytes: number };
  gpu: { gpus: GpuInfo[] } | null;
}

interface GpuInfo {
  name: string;
  utilization: number;
  memory_used_mb: number;
  memory_total_mb: number;
  temperature: number;
  power_w: number;
}

interface Process {
  pid: number;
  name: string;
  username: string;
  status: string;
  cpu_percent: number;
  memory_percent: number;
  memory_rss: number;
  memory_vms: number;
  num_threads: number;
  create_time: string;
  command_line: string;
  project_type: string;
}

interface ProcessListResponse {
  processes: Process[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

interface TypeSummary {
  type: string;
  count: number;
  cpu_percent: number;
  memory_percent: number;
  memory_rss: number;
}

const KNOWN_PROJECT_TYPES = [
  'Python', 'FastAPI', 'Django', 'Flask', 'Celery', 'Gunicorn',
  'Java', 'Spring Boot', 'Tomcat', 'Jetty',
  'Node.js', 'Vite', 'Next.js', 'Nuxt', 'Webpack', 'npm', 'Yarn', 'pnpm',
  'Nginx', 'MySQL', 'PostgreSQL', 'Redis', 'Docker', 'Go', 'Ruby', 'Other',
];

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i];
}

function formatNetRate(bytes: number, interval: number): string {
  const rate = bytes / interval;
  if (rate < 1024) return rate.toFixed(1) + ' B/s';
  if (rate < 1024 * 1024) return (rate / 1024).toFixed(1) + ' KB/s';
  if (rate < 1024 * 1024 * 1024) return (rate / (1024 * 1024)).toFixed(1) + ' MB/s';
  return (rate / (1024 * 1024 * 1024)).toFixed(2) + ' GB/s';
}

function calcNetRate(
  prev: { sent: number; recv: number; time: number } | null,
  current: { bytes_sent: number; bytes_recv: number },
  setState: (rate: { sent: string; recv: string }) => void,
): { sent: number; recv: number; time: number } {
  const now = Date.now();
  const result = { sent: current.bytes_sent, recv: current.bytes_recv, time: now };
  if (prev) {
    const dt = (now - prev.time) / 1000;
    if (dt > 0) {
      setState({
        sent: formatNetRate(Math.max(0, current.bytes_sent - prev.sent), dt),
        recv: formatNetRate(Math.max(0, current.bytes_recv - prev.recv), dt),
      });
    }
  }
  return result;
}

function calcDiskIoRate(
  prev: { read: number; write: number; time: number } | null,
  current: { read_bytes: number; write_bytes: number },
  setState: (rate: { read: string; write: string }) => void,
): { read: number; write: number; time: number } {
  const now = Date.now();
  const result = { read: current.read_bytes, write: current.write_bytes, time: now };
  if (prev) {
    const dt = (now - prev.time) / 1000;
    if (dt > 0) {
      setState({
        read: formatNetRate(Math.max(0, current.read_bytes - prev.read), dt),
        write: formatNetRate(Math.max(0, current.write_bytes - prev.write), dt),
      });
    }
  }
  return result;
}

function formatLastUpdate(time: Date | null): string {
  if (!time) return '—';
  const diff = Math.floor((Date.now() - time.getTime()) / 1000);
  if (diff < 5) return '刚刚';
  if (diff < 60) return `${diff} 秒前`;
  return `${Math.floor(diff / 60)} 分钟前`;
}

// Sparkline with gradient fill
function Sparkline({ data, color }: { data: number[]; color: string }) {
  if (data.length < 2) return null;
  const max = Math.max(...data, 1);
  const w = 100;
  const h = 32;
  const pad = 2;
  const points = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (w - pad * 2);
    const y = h - pad - (v / max) * (h - pad * 2);
    return [x, y];
  });
  const linePoints = points.map(p => p.join(',')).join(' ');
  const areaPoints = `${pad},${h - pad} ` + linePoints + ` ${w - pad},${h - pad}`;

  return (
    <svg width={w} height={h} className="mt-1.5">
      <defs>
        <linearGradient id={`grad-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={areaPoints} fill={`url(#grad-${color.replace('#', '')})`} />
      <polyline points={linePoints} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.8" />
    </svg>
  );
}

const PROJECT_TYPE_COLORS: Record<string, string> = {
  'FastAPI': 'bg-emerald-500/15 text-emerald-400',
  'Django': 'bg-emerald-500/15 text-emerald-400',
  'Flask': 'bg-emerald-500/15 text-emerald-400',
  'Celery': 'bg-emerald-500/15 text-emerald-400',
  'Gunicorn': 'bg-emerald-500/15 text-emerald-400',
  'Python': 'bg-emerald-500/15 text-emerald-400',
  'Spring Boot': 'bg-rose-500/15 text-rose-400',
  'Java': 'bg-rose-500/15 text-rose-400',
  'Tomcat': 'bg-rose-500/15 text-rose-400',
  'Jetty': 'bg-rose-500/15 text-rose-400',
  'Vite': 'bg-cyan-500/15 text-cyan-400',
  'Next.js': 'bg-slate-500/15 text-slate-300',
  'Nuxt': 'bg-slate-500/15 text-slate-300',
  'Node.js': 'bg-amber-500/15 text-amber-400',
  'Webpack': 'bg-blue-500/15 text-blue-400',
  'npm': 'bg-emerald-500/15 text-emerald-400',
  'Yarn': 'bg-blue-500/15 text-blue-400',
  'pnpm': 'bg-orange-500/15 text-orange-400',
  'Nginx': 'bg-violet-500/15 text-violet-400',
  'MySQL': 'bg-blue-500/15 text-blue-400',
  'PostgreSQL': 'bg-blue-500/15 text-blue-400',
  'Redis': 'bg-rose-500/15 text-rose-400',
  'Docker': 'bg-indigo-500/15 text-indigo-400',
  'Go': 'bg-cyan-500/15 text-cyan-400',
  'Ruby': 'bg-rose-500/15 text-rose-400',
  'Other': 'bg-slate-600/15 text-slate-400',
};

// 服务类型图标映射（FontAwesome class）
const SERVICE_ICONS: Record<string, { icon: string; color: string }> = {
  'Spring Boot': { icon: 'fa-leaf', color: 'text-emerald-400' },
  'Java': { icon: 'fa-coffee', color: 'text-orange-400' },
  'Node.js': { icon: 'fa-node-js', color: 'text-green-400' },
  'Python': { icon: 'fa-python', color: 'text-blue-400' },
  'MySQL': { icon: 'fa-database', color: 'text-blue-400' },
  'PostgreSQL': { icon: 'fa-database', color: 'text-blue-400' },
  'Redis': { icon: 'fa-bolt', color: 'text-red-400' },
  'Nginx': { icon: 'fa-server', color: 'text-emerald-400' },
  'Docker': { icon: 'fa-docker', color: 'text-blue-400' },
  'Go': { icon: 'fa-golang', color: 'text-cyan-400' },
  'FastAPI': { icon: 'fa-fire', color: 'text-orange-400' },
  'Django': { icon: 'fa-python', color: 'text-blue-400' },
  'Flask': { icon: 'fa-python', color: 'text-blue-400' },
  'Celery': { icon: 'fa-python', color: 'text-blue-400' },
  'Tomcat': { icon: 'fa-coffee', color: 'text-orange-400' },
  'Vite': { icon: 'fa-bolt', color: 'text-cyan-400' },
};

const PAGE_SIZE_OPTIONS = [20, 50, 100, 200];
const REFRESH_INTERVAL_OPTIONS = [
  { label: '3s', value: 3000 },
  { label: '5s', value: 5000 },
  { label: '10s', value: 10000 },
];

const SORT_FIELDS = ['cpu_percent', 'memory_percent', 'pid', 'memory_rss', 'num_threads', 'name'] as const;
type SortField = typeof SORT_FIELDS[number];
const SORT_ORDERS = ['asc', 'desc'] as const;
type SortOrder = typeof SORT_ORDERS[number];

// 服务概览卡片
function ServiceCard({ type, count, cpuPercent, memoryRss, onClick }: {
  type: string; count: number; cpuPercent: number; memoryRss: number; onClick?: () => void;
}) {
  const iconInfo = SERVICE_ICONS[type] || { icon: 'fa-cube', color: 'text-slate-400' };
  const cpuColor = cpuPercent > 50 ? 'text-red-400' : cpuPercent > 20 ? 'text-amber-400' : 'text-slate-400';

  return (
    <div
      className={`bg-slate-900 rounded-xl p-3 border border-slate-800 ${onClick ? 'cursor-pointer hover:border-slate-600 transition-colors' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-center gap-1.5 mb-1">
        <i className={`fas ${iconInfo.icon} ${iconInfo.color} text-xs`}></i>
        <span className="text-xs text-slate-500 truncate">{type}</span>
      </div>
      <div className="text-sm font-bold text-white mb-1">{count}</div>
      <div className="flex items-center justify-between text-xs">
        <span className={cpuColor}>{cpuPercent}%</span>
        <span className="text-slate-600">{formatBytes(memoryRss)}</span>
      </div>
    </div>
  );
}

export default function SystemMonitor() {
  const navigate = useNavigate();
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [resourceUsage, setResourceUsage] = useState<ResourceUsage | null>(null);
  const [processes, setProcesses] = useState<Process[]>([]);
  const [processTotal, setProcessTotal] = useState(0);
  const [processPage, setProcessPage] = useState(1);
  const [processPageSize, setProcessPageSize] = useState(50);
  const [processTotalPages, setProcessTotalPages] = useState(0);
  const [typeSummary, setTypeSummary] = useState<TypeSummary[]>([]);
  const [sortBy, setSortBy] = useState<SortField>('cpu_percent');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingProcesses, setLoadingProcesses] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProjectType, setSelectedProjectType] = useState<string>('all');
  const [refreshing, setRefreshing] = useState(false);
  const [expandedPid, setExpandedPid] = useState<number | null>(null);
  const [showPartitions, setShowPartitions] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(5000);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const [killingPid, setKillingPid] = useState<number | null>(null);
  const [hoveredPid, setHoveredPid] = useState<number | null>(null);

  const MAX_HISTORY = 20;
  const [cpuHistory, setCpuHistory] = useState<number[]>([]);
  const [memHistory, setMemHistory] = useState<number[]>([]);

  const handleKillProcess = async (pid: number, name: string) => {
    if (!confirm(`确定要终止进程 "${name}" (PID: ${pid}) 吗？`)) return;
    setKillingPid(pid);
    try {
      const res = await fetch(`${API_BASE_URL}/system-monitor/processes/${pid}/kill`, { method: 'POST' });
      if (!res.ok) {
        const data = await res.json();
        alert(data.detail || '终止失败');
      } else {
        fetchProcesses();
      }
    } catch (err) {
      console.error(err);
      alert('终止进程失败');
    } finally {
      setKillingPid(null);
    }
  };

  const prevNetRef = useRef<{ sent: number; recv: number; time: number } | null>(null);
  const [netRate, setNetRate] = useState<{ sent: string; recv: string }>({ sent: '0 B/s', recv: '0 B/s' });
  const prevDiskIoRef = useRef<{ read: number; write: number; time: number } | null>(null);
  const [diskIoRate, setDiskIoRate] = useState<{ read: string; write: string }>({ read: '0 B/s', write: '0 B/s' });

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 400);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const fetchSystemData = useCallback(async () => {
    try {
      const [infoRes, usageRes] = await Promise.all([
        fetch(`${API_BASE_URL}/system-monitor/info`),
        fetch(`${API_BASE_URL}/system-monitor/usage`),
      ]);
      if (!infoRes.ok || !usageRes.ok) throw new Error('获取系统数据失败');
      const info = await infoRes.json();
      const usage = await usageRes.json();
      setSystemInfo(info);
      setResourceUsage(usage);
      setError(null);
      setLastUpdateTime(new Date());
      setCpuHistory(prev => [...prev.slice(-(MAX_HISTORY - 1)), usage.cpu.percent]);
      setMemHistory(prev => [...prev.slice(-(MAX_HISTORY - 1)), usage.memory.percent]);
      prevNetRef.current = calcNetRate(prevNetRef.current, usage.network, setNetRate);
      prevDiskIoRef.current = calcDiskIoRate(prevDiskIoRef.current, usage.disk_io, setDiskIoRate);
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取系统数据失败');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const fetchProcesses = useCallback(async () => {
    setLoadingProcesses(true);
    try {
      const params = new URLSearchParams({
        sort_by: sortBy, sort_order: sortOrder,
        page: String(processPage), page_size: String(processPageSize),
      });
      if (debouncedSearch) params.append('search', debouncedSearch);
      if (selectedProjectType && selectedProjectType !== 'all') params.append('project_type', selectedProjectType);
      const res = await fetch(`${API_BASE_URL}/system-monitor/processes?${params}`);
      if (!res.ok) throw new Error('获取进程列表失败');
      const data: ProcessListResponse & { type_summary?: TypeSummary[] } = await res.json();
      setProcesses(data.processes);
      setProcessTotal(data.total);
      setProcessTotalPages(data.total_pages);
      setTypeSummary(data.type_summary || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingProcesses(false);
    }
  }, [sortBy, sortOrder, debouncedSearch, processPage, processPageSize, selectedProjectType]);

  useEffect(() => { fetchSystemData(); }, [fetchSystemData]);
  useEffect(() => { fetchProcesses(); }, [fetchProcesses]);

  useEffect(() => {
    const interval = setInterval(() => {
      fetch(`${API_BASE_URL}/system-monitor/usage`)
        .then(res => res.json())
        .then(usage => {
          setResourceUsage(usage);
          setLastUpdateTime(new Date());
          setCpuHistory(prev => [...prev.slice(-(MAX_HISTORY - 1)), usage.cpu.percent]);
          setMemHistory(prev => [...prev.slice(-(MAX_HISTORY - 1)), usage.memory.percent]);
          prevNetRef.current = calcNetRate(prevNetRef.current, usage.network, setNetRate);
          prevDiskIoRef.current = calcDiskIoRate(prevDiskIoRef.current, usage.disk_io, setDiskIoRate);
        })
        .catch(() => {});
      if (autoRefresh) fetchProcesses();
    }, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchProcesses, refreshInterval]);

  const handleManualRefresh = () => {
    setRefreshing(true);
    fetchSystemData();
    fetchProcesses();
  };

  const handleSort = (field: SortField) => {
    if (sortBy === field) setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    else { setSortBy(field); setSortOrder('desc'); }
    setProcessPage(1);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setDebouncedSearch(searchQuery);
    setProcessPage(1);
  };

  const handleExportCSV = async (all: boolean = false) => {
    let exportProcesses: Process[] = processes;
    if (all) {
      try {
        const params = new URLSearchParams({ sort_by: sortBy, sort_order: sortOrder, page: '1', page_size: '200' });
        if (debouncedSearch) params.append('search', debouncedSearch);
        if (selectedProjectType && selectedProjectType !== 'all') params.append('project_type', selectedProjectType);
        const res = await fetch(`${API_BASE_URL}/system-monitor/processes?${params}`);
        if (res.ok) exportProcesses = (await res.json()).processes;
      } catch (err) { console.error(err); }
    }
    const headers = ['PID', '进程名', '类型', '状态', '用户', 'CPU %', '内存 %', 'RSS', '线程数', '启动时间', '命令行'];
    const rows = exportProcesses.map(p => [
      p.pid, `"${(p.name || '').replace(/"/g, '""')}"`, p.project_type,
      p.status === 'running' ? '运行中' : p.status, p.username || '',
      p.cpu_percent, p.memory_percent, formatBytes(p.memory_rss),
      p.num_threads, p.create_time, `"${(p.command_line || '').replace(/"/g, '""')}"`,
    ]);
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `进程列表_${all ? '全部' : '当前页'}_${new Date().toLocaleString('zh-CN').replace(/[/:]/g, '-')}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const SortIndicator = ({ field }: { field: string }) => {
    if (sortBy !== field) return <span className="text-slate-600 ml-0.5 text-xs">↕</span>;
    return <span className="text-blue-400 ml-0.5 text-xs">{sortOrder === 'desc' ? '↓' : '↑'}</span>;
  };

  const availableProjectTypes = typeSummary.map(s => s.type);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex items-center gap-3 text-slate-400">
          <i className="fas fa-spinner fa-spin text-xl"></i>
          <span>加载中...</span>
        </div>
      </div>
    );
  }

  // 提取 OS 短名称
  const osShort = systemInfo ? (systemInfo.os === 'Darwin' ? 'macOS' : systemInfo.os) : '';
  const osVersionShort = systemInfo?.os_version ? systemInfo.os_version.split(':')[0].trim() : '';

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-slate-950">
      {/* 顶部工具栏 */}
      <div className="bg-slate-900/80 backdrop-blur border-b border-slate-800 px-3 py-2 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/')} className="text-slate-500 hover:text-white transition-colors">
            <i className="fas fa-arrow-left text-sm"></i>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 bg-emerald-500/20 rounded-lg flex items-center justify-center">
              <i className="fas fa-gauge-high text-emerald-400 text-xs"></i>
            </div>
            <h1 className="text-sm font-semibold text-white">系统性能监控</h1>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {/* 间隔选择 + 更新时间 */}
          <div className="flex items-center gap-1.5 bg-slate-800 rounded-lg px-2 py-1 border border-slate-700/50">
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              className="text-xs bg-transparent text-slate-300 focus:outline-none cursor-pointer"
            >
              {REFRESH_INTERVAL_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value} className="bg-slate-800">{opt.label}</option>
              ))}
            </select>
            <span className="text-slate-600">|</span>
            <span className="text-xs text-slate-500">{formatLastUpdate(lastUpdateTime)}</span>
          </div>
          {/* 自动刷新 Toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg transition-all ${
              autoRefresh
                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                : 'bg-slate-800 text-slate-500 border border-slate-700/50 hover:text-slate-300'
            }`}
          >
            <i className={`fas fa-sync-alt text-xs ${autoRefresh ? 'animate-spin' : ''}`}></i>
            <span className="hidden sm:inline">{autoRefresh ? '自动' : '手动'}</span>
          </button>
          <button
            onClick={handleManualRefresh}
            disabled={refreshing}
            className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-lg bg-slate-800 text-slate-400 border border-slate-700/50 hover:text-white hover:bg-slate-700 transition-all disabled:opacity-30"
          >
            <i className={`fas fa-sync-alt text-xs ${refreshing ? 'animate-spin' : ''}`}></i>
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border-b border-red-500/30 text-red-400 px-3 py-1.5 text-xs flex items-center gap-2 flex-shrink-0">
          <i className="fas fa-exclamation-circle"></i>{error}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* 系统信息 — 网格卡片 */}
        {systemInfo && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {/* 主机 */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-server text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">主机</span>
              </div>
              <div className="text-sm text-white font-medium truncate" title={systemInfo.hostname}>
                {systemInfo.hostname}
              </div>
              <div className="text-xs text-slate-600">{systemInfo.platform.split('-')[0]}</div>
            </div>

            {/* 系统 */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-laptop text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">系统</span>
              </div>
              <div className="text-sm text-white font-medium">{osShort}</div>
              <div className="text-xs text-slate-600 truncate" title={systemInfo.os_version}>
                {osVersionShort}
              </div>
            </div>

            {/* CPU */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-microchip text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">CPU</span>
              </div>
              <div className="text-sm text-white font-medium truncate" title={systemInfo.cpu.model}>
                {systemInfo.cpu.model.split('@')[0].trim()}
              </div>
              <div className="text-xs text-slate-600">
                {systemInfo.cpu.physical_cores}C{systemInfo.cpu.logical_cores}T
                {systemInfo.cpu.frequency ? ` · ${(systemInfo.cpu.frequency / 1000).toFixed(1)}GHz` : ''}
              </div>
            </div>

            {/* 内存 */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-memory text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">内存</span>
              </div>
              <div className="text-sm text-white font-medium">{systemInfo.memory.total_gb} GB</div>
              <div className="text-xs text-slate-600">
                {resourceUsage ? `已用 ${resourceUsage.memory.used_gb} GB (${resourceUsage.memory.percent}%)` : '加载中...'}
              </div>
            </div>

            {/* 磁盘 */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-hdd text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">磁盘</span>
              </div>
              <div className="text-sm text-white font-medium">{systemInfo.disk.total_gb} GB</div>
              <div className="text-xs text-slate-600">
                {resourceUsage ? `已用 ${resourceUsage.disk.used_gb} GB (${resourceUsage.disk.percent}%)` : '加载中...'}
              </div>
            </div>

            {/* 启动时间 */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-calendar text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">启动</span>
              </div>
              <div className="text-sm text-white font-medium font-mono">{systemInfo.boot_time.split(' ')[0]}</div>
              <div className="text-xs text-slate-600">{systemInfo.boot_time.split(' ')[1]}</div>
            </div>

            {/* 运行时间 */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-clock text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">运行</span>
              </div>
              <div className="text-sm text-white font-medium">{systemInfo.uptime}</div>
              <div className="text-xs text-slate-600">自启动以来</div>
            </div>

            {/* Python */}
            <div className="bg-slate-900 rounded-xl p-2.5 border border-slate-800">
              <div className="flex items-center gap-1.5 mb-0.5">
                <i className="fas fa-code text-slate-600 text-xs"></i>
                <span className="text-xs text-slate-500">Python</span>
              </div>
              <div className="text-sm text-white font-medium font-mono">{systemInfo.python_version}</div>
              <div className="text-xs text-slate-600">后端运行时</div>
            </div>
          </div>
        )}

        {/* 资源卡片 */}
        {resourceUsage && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {/* CPU */}
            <div className="bg-slate-900 rounded-xl p-3 border border-slate-800">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-500">CPU</span>
                <i className="fas fa-microchip text-blue-400/60 text-xs"></i>
              </div>
              <div className="flex items-end justify-between">
                <div>
                  <div className="text-xl font-bold text-white">{resourceUsage.cpu.percent}%</div>
                  <Sparkline data={cpuHistory} color="#3b82f6" />
                </div>
              </div>
              <div className="mt-1.5 bg-slate-800 rounded-full h-1.5">
                <div className="h-1.5 rounded-full bg-blue-500 transition-all shadow-sm shadow-blue-500/30"
                  style={{ width: `${Math.min(resourceUsage.cpu.percent, 100)}%` }}></div>
              </div>
              {resourceUsage.cpu.per_cpu && resourceUsage.cpu.per_cpu.length > 0 && (
                <details className="mt-1.5 text-xs text-slate-600">
                  <summary className="cursor-pointer hover:text-slate-400">{resourceUsage.cpu.per_cpu.length} 核</summary>
                  <div className="mt-1 grid grid-cols-4 gap-0.5">
                    {resourceUsage.cpu.per_cpu.map((v, i) => (
                      <div key={i} className="flex items-center gap-0.5">
                        <span className="text-slate-700 w-2 text-right">{i}</span>
                        <div className="flex-1 bg-slate-800 rounded-full h-1">
                          <div className="h-1 rounded-full bg-blue-400/70" style={{ width: `${Math.min(v, 100)}%` }}></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>

            {/* 内存 */}
            <div className="bg-slate-900 rounded-xl p-3 border border-slate-800">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-500">内存</span>
                <i className="fas fa-memory text-emerald-400/60 text-xs"></i>
              </div>
              <div className="text-xl font-bold text-white">{resourceUsage.memory.percent}%</div>
              <div className="text-xs text-slate-600">{resourceUsage.memory.used_gb} / {resourceUsage.memory.total_gb} GB</div>
              <div className="mt-1.5 bg-slate-800 rounded-full h-1.5">
                <div className="h-1.5 rounded-full bg-emerald-500 transition-all shadow-sm shadow-emerald-500/30"
                  style={{ width: `${Math.min(resourceUsage.memory.percent, 100)}%` }}></div>
              </div>
              <Sparkline data={memHistory} color="#22c55e" />
              {resourceUsage.swap.total_gb > 0 && (
                <div className="mt-1.5 pt-1.5 border-t border-slate-800">
                  <div className="flex justify-between text-xs text-slate-600">
                    <span>Swap</span>
                    <span>{resourceUsage.swap.percent}%</span>
                  </div>
                  <div className="mt-0.5 bg-slate-800 rounded-full h-1">
                    <div className="h-1 rounded-full bg-orange-400/70 transition-all"
                      style={{ width: `${Math.min(resourceUsage.swap.percent, 100)}%` }}></div>
                  </div>
                </div>
              )}
            </div>

            {/* 磁盘 */}
            <div className="bg-slate-900 rounded-xl p-3 border border-slate-800">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-500">磁盘</span>
                <i className="fas fa-hdd text-amber-400/60 text-xs"></i>
              </div>
              <div className="text-xl font-bold text-white">{resourceUsage.disk.percent}%</div>
              <div className="text-xs text-slate-600">{resourceUsage.disk.used_gb} / {resourceUsage.disk.total_gb} GB</div>
              <div className="mt-1.5 bg-slate-800 rounded-full h-1.5">
                <div className={`h-1.5 rounded-full transition-all ${resourceUsage.disk.percent > 90 ? 'bg-red-500' : 'bg-amber-500'}`}
                  style={{ width: `${Math.min(resourceUsage.disk.percent, 100)}%` }}></div>
              </div>
              {resourceUsage.disk.partitions && resourceUsage.disk.partitions.length > 0 && (
                <details className="mt-1.5 text-xs text-slate-600" open={false}>
                  <summary className="cursor-pointer hover:text-slate-400">{resourceUsage.disk.partitions.length} 分区</summary>
                  <div className="mt-1 space-y-1">
                    {resourceUsage.disk.partitions.map((p, i) => (
                      <div key={i} className="bg-slate-800/50 rounded px-1.5 py-1">
                        <div className="flex justify-between">
                          <span className="font-mono text-slate-400 text-xs">{p.mountpoint}</span>
                          <span className="text-xs">{p.percent}%</span>
                        </div>
                        <div className="mt-0.5 bg-slate-700 rounded-full h-0.5">
                          <div className={`h-0.5 rounded-full ${p.percent > 90 ? 'bg-red-500' : 'bg-amber-400/70'}`}
                            style={{ width: `${Math.min(p.percent, 100)}%` }}></div>
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>

            {/* 网络 + 磁盘 I/O */}
            <div className="bg-slate-900 rounded-xl p-3 border border-slate-800">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-slate-500">网络 I/O</span>
                <i className="fas fa-network-wired text-violet-400/60 text-xs"></i>
              </div>
              <div className="text-sm font-semibold">
                <span className="text-emerald-400">↑ {netRate.sent}</span>
              </div>
              <div className="text-sm font-semibold">
                <span className="text-blue-400">↓ {netRate.recv}</span>
              </div>
              <div className="mt-1.5 pt-1.5 border-t border-slate-800">
                <span className="text-xs text-slate-500">磁盘 I/O</span>
                <div className="text-xs font-semibold mt-0.5">
                  <span className="text-emerald-400">读 {diskIoRate.read}</span>
                  <span className="text-slate-700 mx-1">/</span>
                  <span className="text-blue-400">写 {diskIoRate.write}</span>
                </div>
              </div>
            </div>

            {/* GPU（如果有） */}
            {resourceUsage.gpu?.gpus && resourceUsage.gpu.gpus.length > 0 && resourceUsage.gpu.gpus.map((gpu, i) => (
              <div key={i} className="bg-slate-900 rounded-xl p-3 border border-slate-800">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-500">GPU {i}</span>
                  <i className="fas fa-microchip text-orange-400/60 text-xs"></i>
                </div>
                <div className="text-xl font-bold text-white">{gpu.utilization}%</div>
                <div className="text-xs text-slate-600 truncate" title={gpu.name}>{gpu.name}</div>
                <div className="mt-1.5 bg-slate-800 rounded-full h-1.5">
                  <div className={`h-1.5 rounded-full transition-all ${gpu.utilization > 80 ? 'bg-red-500' : gpu.utilization > 50 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                    style={{ width: `${Math.min(gpu.utilization, 100)}%` }}></div>
                </div>
                <div className="flex justify-between text-xs text-slate-600 mt-1">
                  <span>显存 {gpu.memory_used_mb.toFixed(0)}/{gpu.memory_total_mb.toFixed(0)}MB</span>
                  <span>{gpu.temperature}°C</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* 服务概览 */}
        {typeSummary.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <i className="fas fa-cubes text-violet-400/60 text-xs"></i>
              <span className="text-xs text-slate-500">服务概览 ({typeSummary.length} 种类型)</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
              {typeSummary.map((svc) => (
                <ServiceCard
                  key={svc.type}
                  type={svc.type}
                  count={svc.count}
                  cpuPercent={svc.cpu_percent}
                  memoryRss={svc.memory_rss}
                  onClick={() => {
                    setSelectedProjectType(svc.type);
                    setProcessPage(1);
                  }}
                />
              ))}
            </div>
          </div>
        )}

        {/* 进程列表 */}
        <div className="bg-slate-900 rounded-xl border border-slate-800">
          <div className="px-3 py-2 border-b border-slate-800">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <i className="fas fa-list text-violet-400/60"></i>进程列表
                <span className="text-xs font-normal text-slate-500">({processTotal})</span>
              </h2>
              <div className="flex flex-wrap items-center gap-1.5">
                <form onSubmit={handleSearch} className="flex">
                  <input
                    type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="搜索进程..."
                    className="bg-slate-800 text-xs px-2 py-1 rounded-l border border-slate-700 focus:outline-none focus:border-blue-500 w-32 placeholder-slate-600"
                  />
                  <button type="submit" className="bg-blue-500/80 hover:bg-blue-500 px-2 py-1 rounded-r text-xs">
                    <i className="fas fa-search"></i>
                  </button>
                </form>
                <select
                  value={selectedProjectType} onChange={(e) => { setSelectedProjectType(e.target.value); setProcessPage(1); }}
                  className="bg-slate-800 text-xs px-1.5 py-1 rounded border border-slate-700 focus:outline-none focus:border-blue-500 text-slate-300"
                >
                  <option value="all" className="bg-slate-800">全部</option>
                  {availableProjectTypes.map(type => (
                    <option key={type} value={type} className="bg-slate-800">{type}</option>
                  ))}
                </select>
                <select
                  value={processPageSize} onChange={(e) => { setProcessPageSize(Number(e.target.value)); setProcessPage(1); }}
                  className="bg-slate-800 text-xs px-1.5 py-1 rounded border border-slate-700 focus:outline-none focus:border-blue-500 text-slate-300"
                >
                  {PAGE_SIZE_OPTIONS.map(size => (
                    <option key={size} value={size} className="bg-slate-800">{size}</option>
                  ))}
                </select>
                <div className="relative group">
                  <button className="text-xs bg-slate-800 hover:bg-slate-700 px-2 py-1 rounded border border-slate-700 transition-all flex items-center gap-1 text-slate-400">
                    <i className="fas fa-download"></i>
                  </button>
                  <div className="absolute right-0 top-full mt-1 bg-slate-800 border border-slate-700 rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 min-w-[100px] overflow-hidden">
                    <button onClick={() => handleExportCSV(false)} className="block w-full text-left text-xs px-3 py-1.5 hover:bg-slate-700 text-slate-300">
                      当前页 ({processes.length})
                    </button>
                    <button onClick={() => handleExportCSV(true)} className="block w-full text-left text-xs px-3 py-1.5 hover:bg-slate-700 text-slate-300 border-t border-slate-700">
                      全部 (≤200)
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="bg-slate-800/50 border-b border-slate-800">
                <tr>
                  <th className="text-left px-2 py-1.5 text-slate-500 font-medium w-6"></th>
                  <th className="text-left px-2 py-1.5 text-slate-500 font-medium cursor-pointer select-none hover:text-slate-300" onClick={() => handleSort('pid')}>
                    PID<SortIndicator field="pid" />
                  </th>
                  <th className="text-left px-2 py-1.5 text-slate-500 font-medium cursor-pointer select-none hover:text-slate-300" onClick={() => handleSort('name')}>
                    进程名<SortIndicator field="name" />
                  </th>
                  <th className="text-left px-2 py-1.5 text-slate-500 font-medium">类型</th>
                  <th className="text-left px-2 py-1.5 text-slate-500 font-medium">状态</th>
                  <th className="text-left px-2 py-1.5 text-slate-500 font-medium cursor-pointer select-none hover:text-slate-300" onClick={() => handleSort('cpu_percent')}>
                    CPU<SortIndicator field="cpu_percent" />
                  </th>
                  <th className="text-left px-2 py-1.5 text-slate-500 font-medium cursor-pointer select-none hover:text-slate-300" onClick={() => handleSort('memory_percent')}>
                    内存<SortIndicator field="memory_percent" />
                  </th>
                  <th className="text-left px-2 py-1.5 text-slate-500 font-medium cursor-pointer select-none hover:text-slate-300 hidden lg:table-cell" onClick={() => handleSort('memory_rss')}>
                    RSS<SortIndicator field="memory_rss" />
                  </th>
                  <th className="text-left px-2 py-1.5 text-slate-500 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {loadingProcesses ? (
                  <tr><td colSpan={9} className="text-center py-6 text-slate-600"><i className="fas fa-spinner fa-spin mr-1.5"></i>加载中...</td></tr>
                ) : processes.length === 0 ? (
                  <tr><td colSpan={9} className="text-center py-6 text-slate-600">没有匹配的进程</td></tr>
                ) : (
                  processes.map((proc) => (
                    <Fragment key={proc.pid}>
                      <tr
                        className={`border-b border-slate-800/50 transition-colors ${expandedPid === proc.pid ? 'bg-slate-800/30' : 'hover:bg-slate-800/20'}`}
                        style={{ contentVisibility: 'auto', containIntrinsicSize: '0 28px' }}
                        onMouseEnter={() => setHoveredPid(proc.pid)}
                        onMouseLeave={() => setHoveredPid(null)}
                      >
                        <td className="px-2 py-1.5 text-slate-600 cursor-pointer" onClick={() => setExpandedPid(expandedPid === proc.pid ? null : proc.pid)}>
                          <i className={`fas fa-chevron-${expandedPid === proc.pid ? 'down' : 'right'} text-xs`}></i>
                        </td>
                        <td className="px-2 py-1.5 font-mono text-slate-400 cursor-pointer" onClick={() => setExpandedPid(expandedPid === proc.pid ? null : proc.pid)}>{proc.pid}</td>
                        <td className="px-2 py-1.5 cursor-pointer relative" onClick={() => setExpandedPid(expandedPid === proc.pid ? null : proc.pid)}>
                          <div className="font-medium truncate max-w-[160px]" title={proc.name}>{proc.name || '-'}</div>
                          {/* 终止按钮 hover 显示 */}
                          {hoveredPid === proc.pid && (
                            <button
                              onClick={(e) => { e.stopPropagation(); handleKillProcess(proc.pid, proc.name); }}
                              disabled={killingPid === proc.pid}
                              className="absolute right-1 top-1/2 -translate-y-1/2 text-xs w-5 h-5 rounded bg-red-500/15 text-red-400 hover:bg-red-500/25 transition-all flex items-center justify-center disabled:opacity-30"
                              title="终止进程"
                            >
                              {killingPid === proc.pid ? <i className="fas fa-spinner fa-spin text-xs"></i> : <i className="fas fa-stop text-xs"></i>}
                            </button>
                          )}
                        </td>
                        <td className="px-2 py-1.5">
                          <span className={`text-xs px-1.5 py-0.5 rounded ${PROJECT_TYPE_COLORS[proc.project_type] || PROJECT_TYPE_COLORS['Other']}`}>
                            {proc.project_type}
                          </span>
                        </td>
                        <td className="px-2 py-1.5">
                          <span className={`text-xs ${proc.status === 'running' ? 'text-emerald-400' : 'text-slate-500'}`}>
                            {proc.status === 'running' ? '运行' : proc.status === 'sleeping' ? '休眠' : proc.status}
                          </span>
                        </td>
                        <td className="px-2 py-1.5">
                          <span className={proc.cpu_percent > 50 ? 'text-red-400 font-semibold' : proc.cpu_percent > 20 ? 'text-amber-400' : 'text-slate-400'}>
                            {proc.cpu_percent}%
                          </span>
                        </td>
                        <td className="px-2 py-1.5">
                          <span className={proc.memory_percent > 50 ? 'text-red-400 font-semibold' : proc.memory_percent > 20 ? 'text-amber-400' : 'text-slate-400'}>
                            {proc.memory_percent}%
                          </span>
                        </td>
                        <td className="px-2 py-1.5 text-slate-500 hidden lg:table-cell">{formatBytes(proc.memory_rss)}</td>
                        <td className="px-2 py-1.5">
                          {/* 终止按钮默认显示在操作列 */}
                          <button
                            onClick={(e) => { e.stopPropagation(); handleKillProcess(proc.pid, proc.name); }}
                            disabled={killingPid === proc.pid}
                            className="text-xs w-5 h-5 rounded bg-red-500/10 text-red-400/60 hover:bg-red-500/20 hover:text-red-400 transition-all disabled:opacity-30 flex items-center justify-center"
                            title="终止进程"
                          >
                            {killingPid === proc.pid ? <i className="fas fa-spinner fa-spin text-xs"></i> : <i className="fas fa-stop text-xs"></i>}
                          </button>
                        </td>
                      </tr>
                      {expandedPid === proc.pid && (
                        <tr className="bg-slate-800/20">
                          <td colSpan={9} className="px-3 py-1.5">
                            <div className="text-xs">
                              <span className="text-slate-600">命令：</span>
                              <code className="text-slate-400 break-all">{proc.command_line || '-'}</code>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* 分页 */}
          {processTotalPages > 1 && (
            <div className="px-3 py-2 border-t border-slate-800 flex items-center justify-between">
              <div className="text-xs text-slate-500">{processPage} / {processTotalPages} · {processTotal} 条</div>
              <div className="flex items-center gap-0.5">
                <button onClick={() => setProcessPage(1)} disabled={processPage === 1}
                  className="w-6 h-6 flex items-center justify-center text-xs bg-slate-800 rounded disabled:opacity-20 hover:bg-slate-700 text-slate-400 disabled:hover:bg-slate-800">
                  <i className="fas fa-angles-left"></i>
                </button>
                <button onClick={() => setProcessPage(p => Math.max(1, p - 1))} disabled={processPage === 1}
                  className="w-6 h-6 flex items-center justify-center text-xs bg-slate-800 rounded disabled:opacity-20 hover:bg-slate-700 text-slate-400 disabled:hover:bg-slate-800">
                  <i className="fas fa-angle-left"></i>
                </button>
                <span className="px-2 text-xs text-slate-300">{processPage}</span>
                <button onClick={() => setProcessPage(p => Math.min(processTotalPages, p + 1))} disabled={processPage === processTotalPages}
                  className="w-6 h-6 flex items-center justify-center text-xs bg-slate-800 rounded disabled:opacity-20 hover:bg-slate-700 text-slate-400 disabled:hover:bg-slate-800">
                  <i className="fas fa-angle-right"></i>
                </button>
                <button onClick={() => setProcessPage(processTotalPages)} disabled={processPage === processTotalPages}
                  className="w-6 h-6 flex items-center justify-center text-xs bg-slate-800 rounded disabled:opacity-20 hover:bg-slate-700 text-slate-400 disabled:hover:bg-slate-800">
                  <i className="fas fa-angles-right"></i>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
