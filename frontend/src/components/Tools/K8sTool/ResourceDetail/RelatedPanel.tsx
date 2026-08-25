/**
 * K8s 资源详情 - 关联资源面板
 *
 * 从 Pod YAML 中提取 ConfigMap / Secret / PVC 引用，展示容器镜像和 Owner Reference
 * 点击条目可跳转到对应资源的事件视图
 */
import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useI18n } from '../../../../i18n';
import { useK8sStore } from '../../../../stores/k8sStore';
import * as api from '../../../../api/k8sToolApi';

interface Props {
  configId: string;
  namespace: string;
  podName: string;
}

/** 从 YAML 文本中提取指定 key 下的所有 name 值 */
const extractYamlNames = (yaml: string, parentKey: string): string[] => {
  const names = new Set<string>();
  const lines = yaml.split('\n');
  let inParent = false;
  const parentIndent = parentKey.length;

  for (const line of lines) {
    // 匹配顶层 parentKey（如 configMapKeyRef:、secretKeyRef:、persistentVolumeClaim:）
    const trimmed = line.trimStart();
    const indent = line.length - trimmed.length;

    if (trimmed.startsWith(`${parentKey}:`)) {
      inParent = true;
      continue;
    }

    if (inParent) {
      // 仍在该块内（缩进大于 parentKey 所在行）
      if (indent === 0 && trimmed.length > 0 && !trimmed.startsWith('#')) {
        inParent = false;
        continue;
      }
      const nameMatch = trimmed.match(/^name:\s*(.+)$/);
      if (nameMatch) {
        const name = nameMatch[1].trim().replace(/^["']|["']$/g, '');
        if (name) names.add(name);
      }
    }
  }

  return Array.from(names);
};

/** 关联资源条目 */
interface RelatedItem {
  kind: 'ConfigMap' | 'Secret' | 'PVC';
  name: string;
}

export const RelatedPanel: React.FC<Props> = ({ configId, namespace, podName }) => {
  const { t } = useI18n();
  const rt = t.tools['k8s-tool'].resourceDetail.related;
  const { setSelectedResource } = useK8sStore();

  // 获取 Pod YAML，用于提取关联资源引用
  const { data: yamlData } = useQuery({
    queryKey: ['k8s', configId, 'pod', podName, 'yaml', namespace],
    queryFn: () => api.getPodYaml(configId, podName, namespace),
    enabled: !!configId && !!podName && !!namespace,
  });

  // 获取 Pod 详情以获取 Owner Reference 和容器信息
  const { data: pod } = useQuery({
    queryKey: ['k8s', configId, 'pod', podName, namespace],
    queryFn: () => api.getPodDetail(configId, podName, namespace),
    enabled: !!configId && !!podName && !!namespace,
  });

  // 从 YAML 中提取关联资源
  const relatedItems = useMemo<RelatedItem[]>(() => {
    if (!yamlData?.yaml) return [];

    const configmaps = extractYamlNames(yamlData.yaml, 'configMapKeyRef');
    const configmapNames = extractYamlNames(yamlData.yaml, 'configMap');
    const secrets = extractYamlNames(yamlData.yaml, 'secretKeyRef');
    const secretNames = extractYamlNames(yamlData.yaml, 'secret');
    const pvcs = extractYamlNames(yamlData.yaml, 'persistentVolumeClaim');

    const items: RelatedItem[] = [];

    // 去重后添加
    [...new Set([...configmaps, ...configmapNames])].forEach((name) =>
      items.push({ kind: 'ConfigMap', name })
    );
    [...new Set([...secrets, ...secretNames])].forEach((name) =>
      items.push({ kind: 'Secret', name })
    );
    pvcs.forEach((name) => items.push({ kind: 'PVC', name }));

    return items;
  }, [yamlData]);

  /** 点击查看该资源的事件 */
  const handleViewEvents = (item: RelatedItem) => {
    // 切换到 Events tab，并通过 selectedResource 传递过滤信息
    // 这里使用 resourceType 为 events，selectedResource 为资源名称
    setSelectedResource({
      type: `${item.kind.toLowerCase()}-events`,
      namespace,
      name: item.name,
    });
  };

  /** 资源 Kind 图标 */
  const getKindIcon = (kind: string): string => {
    switch (kind) {
      case 'ConfigMap': return 'fas fa-map text-accent-info';
      case 'Secret': return 'fas fa-key text-accent-warning';
      case 'PVC': return 'fas fa-database text-accent-secondary';
      default: return 'fas fa-cube text-ink-muted';
    }
  };

  /** 资源 Kind 颜色 */
  const getKindColor = (kind: string): string => {
    switch (kind) {
      case 'ConfigMap': return 'border-accent-info/30 bg-accent-info/10';
      case 'Secret': return 'border-yellow-500/30 bg-yellow-500/10';
      case 'PVC': return 'border-accent-secondary/30 bg-accent-secondary/10';
      default: return 'border-border bg-surface-1/50';
    }
  };

  const hasContent = (pod?.owner_references?.length ?? 0) > 0
    || relatedItems.length > 0
    || (pod?.containers?.length ?? 0) > 0;

  if (!hasContent && !pod) {
    return (
      <div className="flex items-center justify-center h-full text-ink-faint text-sm">
        {rt.noRelated}
      </div>
    );
  }

  return (
    <div className="p-4 overflow-y-auto h-full space-y-5">
      {/* Owner Reference */}
      {pod?.owner_references && pod.owner_references.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-2">
            {rt.ownerReferences}
          </h4>
          <div className="space-y-1.5">
            {pod.owner_references.map((ref) => (
              <div
                key={ref.uid}
                className="flex items-center gap-2 px-3 py-2 bg-surface-1/50 border border-border/50 rounded text-xs hover:bg-surface-1 cursor-pointer"
                onClick={() => setSelectedResource({
                  type: ref.kind.toLowerCase(),
                  namespace,
                  name: ref.name,
                })}
              >
                <i className="fas fa-link text-accent-info"></i>
                <span className="text-accent-info font-medium">{ref.kind}</span>
                <span className="text-ink-muted">/</span>
                <span className="text-ink font-mono">{ref.name}</span>
                <i className="fas fa-bolt text-ink-faint ml-auto" title={rt.viewEvents}></i>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 节点信息 */}
      {pod?.node && (
        <div>
          <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-2">
            {rt.node}
          </h4>
          <div className="flex items-center gap-2 px-3 py-2 bg-surface-1/50 border border-border/50 rounded text-xs">
            <i className="fas fa-server text-green-400"></i>
            <span className="text-ink font-mono">{pod.node}</span>
          </div>
        </div>
      )}

      {/* 容器镜像 */}
      {pod?.containers && pod.containers.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-2">
            {rt.containerImages}
          </h4>
          <div className="space-y-1">
            {pod.containers.map((c) => (
              <div
                key={c.name}
                className="flex items-center gap-2 px-3 py-1.5 bg-surface-1/30 border border-border/30 rounded text-xs"
              >
                <i className="fas fa-cube text-ink-faint"></i>
                <span className="text-ink-muted">{c.name}:</span>
                <span
                  className="text-ink-muted font-mono truncate"
                  title={c.image}
                >
                  {c.image}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ConfigMap / Secret / PVC 引用 */}
      <div>
        <h4 className="text-xs font-semibold text-ink-muted uppercase tracking-wide mb-2">
          {rt.configmaps} / {rt.secrets} / {rt.pvcs}
        </h4>

        {relatedItems.length === 0 ? (
          <div className="text-xs text-ink-faint italic">{rt.noRelated}</div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {relatedItems.map((item) => (
              <button
                key={`${item.kind}/${item.name}`}
                onClick={() => handleViewEvents(item)}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 border rounded text-xs transition-colors hover:opacity-80 ${getKindColor(item.kind)}`}
                title={rt.viewEvents}
              >
                <i className={getKindIcon(item.kind)}></i>
                <span className="text-ink-muted font-mono truncate max-w-[200px]">
                  {item.name}
                </span>
                <span className="text-ink-faint">({item.kind})</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
