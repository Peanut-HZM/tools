import React from 'react';
import type { McpServerTestResponse } from '../../../api/mcpServersApi';

interface Props {
  result: McpServerTestResponse;
  onClose: () => void;
}

const TestResultDialog: React.FC<Props> = ({ result, onClose }) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-surface-1 rounded-lg p-6 w-full max-w-lg border border-border/50 shadow-xl">
        <h2 className="text-xl font-bold mb-4 text-ink">
          {result.success ? '连接成功' : '连接失败'}
        </h2>

        {result.success && result.tools.length > 0 && (
          <div>
            <h3 className="font-medium mb-2 text-ink">
              发现 {result.tools.length} 个工具：
            </h3>
            <div className="max-h-64 overflow-y-auto border border-border/50 rounded p-3 bg-canvas">
              {result.tools.map((tool, i) => (
                <div key={`${tool.name}-${i}`} className="mb-2 last:mb-0">
                  <div className="font-medium text-ink">{tool.name}</div>
                  {tool.description && (
                    <div className="text-sm text-ink-muted">{tool.description}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {result.success && result.tools.length === 0 && (
          <div className="text-sm text-ink-muted">
            已建立连接，但服务器未声明任何工具。
          </div>
        )}

        {result.error && (
          <div className="text-danger text-sm mt-4 bg-danger/10 border border-danger/30 rounded p-3">
            <strong>Error:</strong> {result.error}
          </div>
        )}

        <div className="flex justify-end mt-6">
          <button
            onClick={onClose}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};

export default TestResultDialog;
