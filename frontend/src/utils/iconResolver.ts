/**
 * 将后端/数据层返回的 Font Awesome class 字符串映射到 lucide-react 组件。
 *
 * 历史原因：tool 数据模型里的 `icon` 字段当前存储的是 FA class 字符串
 * （例如 'fa-server'、'fas fa-key'）。在前端解析成 lucide 组件，可以彻底
 * 移除对 Font Awesome CDN 的依赖。
 *
 * 后续迁移方向：把后端存储从 FA class 字符串改为 lucide icon 名
 * （如 'Server' / 'Key'），届时可以直接传入组件引用，本文件退役。
 */
import {
  Server, Key, Database, Code, Globe, Bot, FileText, Image as ImageIcon, Cpu,
  Network as NetworkIcon, Rocket, Sparkles, Zap, Shield, Layers, Workflow, Puzzle,
  Gamepad2, Package, Settings, Monitor, Smartphone, Search, Folder, Lock, Check,
  Pencil, Trash2, Terminal, Plug, Mic, Video, LineChart, Gauge, MessageSquare,
  History, CalendarDays, FileImage, FileOutput, Share2, Briefcase, Ship, Cloud,
  List, Table, Clock, Bell, User, Tag, Download, Upload, Wrench,
  type LucideIcon,
} from 'lucide-react';
import type { ComponentType } from 'react';

export const faIconMap: Record<string, ComponentType<{ className?: string }>> = {
  'fa-server': Server,
  'fa-terminal': Terminal,
  'fa-key': Key,
  'fa-plug': Plug,
  'fa-microphone': Mic,
  'fa-video': Video,
  'fa-database': Database,
  'fa-code': Code,
  'fa-globe': Globe,
  'fa-robot': Bot,
  'fa-file': FileText,
  'fa-file-alt': FileText,
  'fa-file-lines': FileText,
  'fa-image': ImageIcon,
  'fa-microchip': Cpu,
  'fa-network-wired': NetworkIcon,
  'fa-rocket': Rocket,
  'fa-magic': Sparkles,
  'fa-wand-magic-sparkles': Sparkles,
  'fa-bolt': Zap,
  'fa-shield': Shield,
  'fa-shield-alt': Shield,
  'fa-shield-halved': Shield,
  'fa-layer-group': Layers,
  'fa-layer': Layers,
  'fa-sitemap': Workflow,
  'fa-project-diagram': Workflow,
  'fa-puzzle-piece': Puzzle,
  'fa-gamepad': Gamepad2,
  'fa-box': Package,
  'fa-cube': Package,
  'fa-cog': Settings,
  'fa-gear': Settings,
  'fa-gears': Settings,
  'fa-cogs': Settings,
  'fa-desktop': Monitor,
  'fa-mobile': Smartphone,
  'fa-search': Search,
  'fa-folder': Folder,
  'fa-lock': Lock,
  'fa-check': Check,
  'fa-edit': Pencil,
  'fa-pen': Pencil,
  'fa-trash': Trash2,
  'fa-trash-alt': Trash2,
  'fa-chart-line': LineChart,
  'fa-gauge-high': Gauge,
  'fa-gauge': Gauge,
  'fa-tachometer-alt': Gauge,
  'fa-comments': MessageSquare,
  'fa-comment': MessageSquare,
  'fa-clock-rotate-left': History,
  'fa-history': History,
  'fa-calendar-alt': CalendarDays,
  'fa-calendar': CalendarDays,
  'fa-file-image': FileImage,
  'fa-file-export': FileOutput,
  'fa-file-code': Code,
  'fa-share-alt': Share2,
  'fa-share': Share2,
  'fa-user-tie': Briefcase,
  'fa-dharmachakra': Ship,
  'fa-pen-to-square': Pencil,
  'fa-cloud': Cloud,
  'fa-list': List,
  'fa-list-ul': List,
  'fa-table': Table,
  'fa-clock': Clock,
  'fa-bell': Bell,
  'fa-user': User,
  'fa-tag': Tag,
  'fa-download': Download,
  'fa-upload': Upload,
  'fa-wrench': Wrench,
};

/** 从 'fas fa-server' / 'fa-server' / 'fa-server  extra' 提取出 'fa-server' */
export function resolveFaIconName(iconString: string | undefined | null): string | undefined {
  if (!iconString) return undefined;
  // 后端可能返回 'fa-server' 或 'fas fa-server' 或 'fa-server something'，取最后一个 token
  const tokens = iconString.trim().split(/\s+/);
  // 跳过 'fas' / 'far' / 'fab' / 'fal' / 'fat' 等样式前缀
  const stylePrefixes = new Set(['fas', 'far', 'fab', 'fal', 'fat', 'fa-solid', 'fa-regular', 'fa-brands']);
  for (const t of tokens) {
    if (!stylePrefixes.has(t)) return t;
  }
  return tokens[tokens.length - 1];
}

/** 解析 FA class 字符串为 lucide 组件；找不到则 fallback 到 Wrench */
export function resolveIcon(
  iconString: string | undefined | null
): ComponentType<{ className?: string }> {
  const name = resolveFaIconName(iconString);
  return (name && faIconMap[name]) || Wrench;
}

/** 仅用于：把当前仍是 FA class 的字符串映射到 lucide 组件，避免硬依赖 FA CDN。
 *  后续后端数据迁完后此模块可退役。*/
export type { LucideIcon };