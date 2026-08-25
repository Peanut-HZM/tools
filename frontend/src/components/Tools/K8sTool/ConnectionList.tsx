/**
 * K8s 工具 - 连接列表组件
 * 左侧边栏：展示所有 K8s 集群连接，支持拖动排序
 */
import React, { useState, useEffect } from 'react';
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
import type { K8sConnection } from './types';
import { useI18n, interpolate } from '../../../i18n';

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
  if (conn.last_test_error) return 'bg-red-500';
  if (conn.last_test_at) return 'bg-green-500';
  return 'bg-surface-3';
}

function getSourceIcon(sourceType: K8sConnection['source_type']): string {
  switch (sourceType) {
    case 'kubeconfig_file': return 'fas fa-file-upload';
    case 'kubeconfig_text': return 'fas fa-paste';
    case 'manual': return 'fas fa-keyboard';
    default: return 'fas fa-server';
  }
}

/** 可排序的连接项 */
const SortableConnectionItem: React.FC<{
  conn: K8sConnection;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onEdit: (config: K8sConnection) => void;
  onDelete: (id: string) => void;
  k8sT: any;
  t: any;
}> = ({ conn, selectedId, onSelect, onEdit, onDelete, k8sT, t }) => {
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

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={[
        'p-2 rounded group flex justify-between items-center transition-colors',
        isSelected
          ? 'bg-accent/20 text-accent-info border border-accent/40'
          : 'text-ink-muted hover:bg-surface-2 hover:text-ink-inverse',
      ].join(' ')}
      onClick={() => onSelect(conn.id)}
    >
      {/* 拖动把手 */}
      <div
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-ink-faint hover:text-ink-muted mr-1 flex-shrink-0"
        onClick={(e) => e.stopPropagation()}
      >
        <i className="fas fa-grip-vertical text-xs"></i>
      </div>

      <div className="truncate flex-1 min-w-0">
        <div className="font-medium flex items-center truncate">
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
          <i className={[getSourceIcon(conn.source_type), 'mr-1.5 text-xs opacity-60 flex-shrink-0'].join(' ')}></i>
          <span className="truncate">{conn.name}</span>
        </div>
        <div className="text-xs truncate text-ink-faint group-hover:text-ink-muted ml-4">
          {conn.server || conn.cluster_name}
        </div>
      </div>

      <div className="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 flex-shrink-0">
        <button
          onClick={(e) => { e.stopPropagation(); onEdit(conn); }}
          className="p-1 rounded hover:bg-surface-3 text-ink-muted hover:text-ink-inverse"
          title={k8sT.editConnection}
        >
          <i className="fas fa-pen text-xs"></i>
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (window.confirm(interpolate(k8sT.connection.deleteConfirm, { name: conn.name }))) {
              onDelete(conn.id);
            }
          }}
          className="p-1 rounded hover:bg-surface-3 text-ink-muted hover:text-danger"
          title={t.common.delete}
        >
          <i className="fas fa-trash text-xs"></i>
        </button>
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
  const [items, setItems] = useState(configs);

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
    <div className="flex flex-col h-full bg-surface-1 border-r border-border w-full">
      <div className="p-4 border-b border-border flex flex-col gap-2 bg-surface-1">
        <div className="flex justify-between items-center">
          <h2 className="font-semibold text-ink">{k8sT.connections}</h2>
          <button
            onClick={onAdd}
            className="p-1.5 text-ink-muted hover:text-ink-inverse hover:bg-surface-2 rounded transition-colors"
            title={k8sT.addConnection}
          >
            <i className="fas fa-plus"></i>
          </button>
        </div>
      </div>

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={items.map(item => item.id)} strategy={verticalListSortingStrategy}>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {items.map(conn => (
              <SortableConnectionItem
                key={conn.id}
                conn={conn}
                selectedId={selectedId}
                onSelect={onSelect}
                onEdit={onEdit}
                onDelete={onDelete}
                k8sT={k8sT}
                t={t}
              />
            ))}

            {items.length === 0 && (
              <div className="p-4 text-center text-sm text-ink-faint">
                {k8sT.emptyConnections}
              </div>
            )}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
};
