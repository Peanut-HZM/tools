/**
 * K8s 资源详情 - YAML 面板
 *
 * 使用 prism-react-renderer v2 展示资源 YAML，支持一键复制
 * 数据来源：api.getPodYaml()
 */
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Highlight, themes } from 'prism-react-renderer';
import { Loader2, AlertTriangle, Check, Copy } from 'lucide-react';
import { useI18n } from '../../../../i18n';
import { useToast } from '../../../../hooks/useToast';
import * as api from '../../../../api/k8sToolApi';
import { Button } from '@/components/ui/Button';

interface Props {
  configId: string;
  /** 资源类型，当前固定为 'pods'，后续可扩展 */
  resourceType: string;
  namespace: string;
  name: string;
}

export const YamlPanel: React.FC<Props> = ({ configId, resourceType, namespace, name }) => {
  const { t } = useI18n();
  const yt = t.tools['k8s-tool'].resourceDetail.yaml;
  const { addToast } = useToast();
  const [copied, setCopied] = useState(false);

  // 获取 YAML 内容
  const { data, isLoading, isError } = useQuery({
    queryKey: ['k8s', configId, resourceType, name, 'yaml', namespace],
    queryFn: () => {
      // 当前仅支持 pods 类型
      if (resourceType === 'pod') {
        return api.getPodYaml(configId, name, namespace);
      }
      throw new Error('Unsupported resource type');
    },
    enabled: !!configId && !!name && !!namespace,
  });

  const yamlText = data?.yaml ?? '';

  /** 复制到剪贴板 */
  const handleCopy = async () => {
    if (!yamlText) return;
    try {
      await navigator.clipboard.writeText(yamlText);
      setCopied(true);
      addToast(yt.copied, 'success');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      addToast(t.common.error, 'error');
    }
  };

  // 加载中
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full text-ink-faint">
        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
        {yt.loading}
      </div>
    );
  }

  // 加载失败
  if (isError) {
    return (
      <div className="flex items-center justify-center h-full text-danger">
        <AlertTriangle className="w-4 h-4 mr-2" />
        {yt.error}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* 工具栏：复制按钮 */}
      <div className="flex items-center justify-end px-3 py-1.5 border-b border-border bg-surface-1/50 shrink-0">
        <Button
          variant="secondary"
          size="sm"
          onClick={handleCopy}
          className="h-7 px-2.5 py-1 text-xs"
        >
          {copied ? <Check className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
          {copied ? yt.copied : yt.copy}
        </Button>
      </div>

      {/* YAML 代码区域 */}
      <div className="flex-1 overflow-auto">
        <Highlight theme={themes.nightOwl} code={yamlText} language="yaml">
          {({ className, style, tokens, getLineProps, getTokenProps }) => (
            <pre
              className={`${className} text-xs font-mono leading-relaxed p-0 m-0`}
              style={{ ...style, background: 'transparent', minHeight: '100%' }}
            >
              {tokens.map((line, i) => (
                <div key={i} {...getLineProps({ line })} className="table-row">
                  {/* 行号 */}
                  <span className="table-cell text-right pr-3 pl-3 select-none text-ink-faint border-r border-border">
                    {i + 1}
                  </span>
                  {/* 代码内容 */}
                  <span className="table-cell pl-3 pr-4">
                    {line.map((token, key) => (
                      <span key={key} {...getTokenProps({ token })} />
                    ))}
                  </span>
                </div>
              ))}
            </pre>
          )}
        </Highlight>
      </div>
    </div>
  );
};