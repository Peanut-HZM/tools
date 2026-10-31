/**
 * K8s 工具 - 连接列表组件
 * 左侧边栏：展示所有 K8s 集群连接，支持拖动排序
 */
import React, { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { FileUp, ClipboardPaste, Keyboard, Server, GripVertical, Pencil, Trash2, Plus, Search, HardDriveDownload, HardDriveUpload } from 'lucide-react';
import type { K8sConnection } from './types';
import { useI18n, interpolate } from '../../../i18n';
import { Button } from '@/components/ui/Button';
import StorageLocationBadge from '../../Common/StorageLocationBadge';
import { migrateConfig } from '../../../api/storageApi';
import { useToast } from '../../../hooks/useToast';
import type { StorageLocation } from '../../../types/storage';

interface Props {
  configs: K8sConnection[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onAdd: () => void;
  onEdit: (config: K8sConnection) => void;
  onDelete: (id: string) => void;
  onSortEnd: (configIds: string[]) => void;
}

function getHealthDotClass(conn: K8sConnection): string {
  if (conn.last_test_error) return 'bg-danger';
  if (conn.last_test_at) return 'bg-success';
  return 'bg-surface-3';
}

function getSourceIcon(sourceType: K8sConnection['source_type']): React.ReactNode {
  switch (sourceType) {
    case 'kubeconfig_file': return <FileUp className="w-3 h-3 mr-1.5 opacity-60 flex-shrink-0" />;
    case 'kubeconfig_text': return <ClipboardPaste className="w-3 h-3 mr-1.5 opacity-60 flex-shrink-0" />;
    case 'manual': return <Keyboard className="w-3 h-3 mr-1.5 opacity-60 flex-shrink-0" />;
    default: return <Server className="w-3 h-3 mr-1.5 opacity-60 flex-shrink-0" />;
  }
}

/** 可排序的连接项 */
const SortableConnectionItem: React.FC<{
  conn: K8sConnection;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onEdit: (config: K8sConnection) => void;
  onDelete: (id: string) => void;
  onMigrated?: () => void;
  k8sT: any;
  t: any;
}> = ({ conn, selectedId, onSelect, onEdit, onDelete, onMigrated, k8sT, t }) => {
  const { addToast } = useToast();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
  } = useSortable({ id: conn.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const isSelected = conn.id === selectedId;

  /** 存储位置迁移：本机 ↔ 服务器（迁移时后端会用目标端密钥重新加密凭据） */
  const handleMigrate = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const target: StorageLocation =
      (conn.storage_location ?? 'local') === 'local' ? 'server' : 'local';
    const targetLabel = target === 'local' ? '仅保存在本机' : '上传到服务器';
    if (
      !window.confirm(
        `确定要「${targetLabel}」该连接配置吗？\n迁移时会用目标端的密钥重新加密凭据。`,
      )
    ) {
      return;
    }
    try {
      const result = await migrateConfig('k8s', conn.id, target);
      addToast(result.message || '迁移成功', result.success ? 'success' : 'error');
      onMigrated?.();
    } catch (err) {
      addToast(err instanceof Error ? err.message : '迁移失败', 'error');
    }
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={[
        'group flex items-center justify-between rounded-lg border px-2 py-2 transition-colors',
        isSelected
          ? 'border-indigo-200 bg-indigo-50 text-indigo-700 dark:border-indigo-400/30 dark:bg-indigo-400/10 dark:text-indigo-300'
          : 'border-transparent text-ink-muted hover:border-border hover:bg-surface-2 hover:text-ink',
      ].join(' ')}
    >
      {/* 拖动把手 */}
      <div
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-ink-faint hover:text-ink-muted mr-1 flex-shrink-0"
        onClick={(e) => e.stopPropagation()}
      >
        <GripVertical className="w-3 h-3" />
      </div>

      <button
        type="button"
        aria-pressed={isSelected}
        className="min-w-0 flex-1 truncate text-left"
        onClick={() => onSelect(conn.id)}
      >
        <div className="flex truncate text-xs font-medium">
          <span
            className={['w-2 h-2 rounded-full mr-2 flex-shrink-0', getHealthDotClass(conn)].join(' ')}
            title={
              conn.last_test_error
                ? conn.last_test_error
                : conn.last_test_at
                  ? k8sT.connection.metricsAvailable
                  : undefined
            }
          ></span>
          {getSourceIcon(conn.source_type)}
          <span className="truncate">{conn.name}</span>
          <span className="ml-1.5 flex-shrink-0">
            <StorageLocationBadge location={(conn.storage_location ?? 'local') as StorageLocation} />
          </span>
        </div>
        <div className="ml-4 mt-0.5 truncate text-[10px] text-ink-faint group-hover:text-ink-muted" title={conn.server || conn.cluster_name}>
          {conn.server || conn.cluster_name}
        </div>
      </button>

      <div className="flex space-x-1 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100 ml-2 flex-shrink-0">
        <Button
          variant="ghost"
          size="icon"
          onClick={handleMigrate}
          className="h-7 w-7 p-0"
          title={
            (conn.storage_location ?? 'local') === 'local'
              ? '迁移到服务器存储'
              : '迁移到本机存储'
          }
        >
          {(conn.storage_location ?? 'local') === 'local' ? (
            <HardDriveUpload className="w-3 h-3" />
          ) : (
            <HardDriveDownload className="w-3 h-3" />
          )}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={(e) => { e.stopPropagation(); onEdit(conn); }}
          className="h-7 w-7 p-0"
          title={k8sT.editConnection}
        >
          <Pencil className="w-3 h-3" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={(e) => {
            e.stopPropagation();
            if (window.confirm(interpolate(k8sT.connection.deleteConfirm, { name: conn.name }))) {
              onDelete(conn.id);
            }
          }}
          className="h-7 w-7 p-0 hover:text-danger"
          title={t.common.delete}
        >
          <Trash2 className="w-3 h-3" />
        </Button>
      </div>
    </div>
  );
};

export const ConnectionList: React.FC<Props> = ({
  configs,
  selectedId,
  onSelect,
  onAdd,
  onEdit,
  onDelete,
  onSortEnd,
}) => {
  const { t } = useI18n();
  const k8sT = t.tools['k8s-tool'];
  const queryClient = useQueryClient();
  const [items, setItems] = useState(configs);
  const [searchText, setSearchText] = useState('');
  const visibleItems = items.filter((connection) => {
    const keyword = searchText.trim().toLowerCase();
    if (!keyword) return true;
    return [connection.name, connection.cluster_name, connection.server]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(keyword));
  });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = items.findIndex(item => item.id === active.id);
      const newIndex = items.findIndex(item => item.id === over.id);
      const newItems = arrayMove(items, oldIndex, newIndex);
      setItems(newItems);
      onSortEnd(newItems.map(item => item.id));
    }
  };

  useEffect(() => {
    setItems(configs);
  }, [configs]);

  return (
    <div className="flex h-full w-full flex-col border-r border-border bg-surface-1">
      <div className="flex flex-col gap-2 border-b border-border bg-surface-1 p-3">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-sm font-semibold text-ink">{k8sT.title}</h2>
            <p className="mt-0.5 text-[10px] text-ink-faint">{k8sT.connections}</p>
          </div>
          <Button
            size="sm"
            onClick={onAdd}
            className="h-7 gap-1 px-2 text-[11px]"
            title={k8sT.addConnection}
          >
            <Plus className="h-3.5 w-3.5" />
            {k8sT.connection.addConfig}
          </Button>
        </div>
        <label className="relative block">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-faint" />
          <input
            aria-label={k8sT.searchClusters}
            value={searchText}
            onChange={(event) => setSearchText(event.target.value)}
            placeholder={k8sT.searchClusters}
            className="h-8 w-full rounded-md border border-border bg-canvas pl-8 pr-2 text-xs text-ink placeholder:text-ink-faint outline-none transition-colors focus:border-accent"
          />
        </label>
      </div>

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={visibleItems.map(item => item.id)} strategy={verticalListSortingStrategy}>
          <div className="flex-1 space-y-1 overflow-y-auto p-2">
            {visibleItems.map(conn => (
              <SortableConnectionItem
                key={conn.id}
                conn={conn}
                selectedId={selectedId}
                onSelect={onSelect}
                onEdit={onEdit}
                onDelete={onDelete}
                onMigrated={() =>
                  queryClient.invalidateQueries({ queryKey: ['k8s', 'connections'] })
                }
                k8sT={k8sT}
                t={t}
              />
            ))}

            {items.length === 0 && (
              <div className="p-4 text-center text-sm text-ink-faint">
                {k8sT.emptyConnections}
              </div>
            )}
            {items.length > 0 && visibleItems.length === 0 && (
              <div className="p-4 text-center text-sm text-ink-faint">
                {k8sT.noMatchingClusters}
              </div>
            )}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
};
