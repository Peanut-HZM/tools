import React from 'react';
import ReactMarkdown from 'react-markdown';

interface Version {
  id: string;
  version_number: number;
  content: string;
  created_at: string;
}

interface VersionDiffProps {
  fromVersion: Version;
  toVersion: Version;
  diff: string;
  onClose: () => void;
}

const VersionDiff: React.FC<VersionDiffProps> = ({
  fromVersion,
  toVersion,
  diff,
  onClose,
}) => {
  const renderDiffLine = (line: string, index: number) => {
    if (line.startsWith('+')) {
      return (
        <div key={index} className="bg-green-500/20 text-green-400 px-2 py-0.5">
          {line}
        </div>
      );
    }
    if (line.startsWith('-')) {
      return (
        <div key={index} className="bg-red-500/20 text-red-400 px-2 py-0.5">
          {line}
        </div>
      );
    }
    return (
      <div key={index} className="text-slate-300 px-2 py-0.5">
        {line}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-lg w-full max-w-6xl h-[90vh] flex flex-col m-4">
        <div className="p-4 border-b border-slate-700 flex justify-between items-center">
          <div>
            <h3 className="text-white font-semibold text-lg">版本对比</h3>
            <p className="text-slate-400 text-sm mt-1">
              版本 {fromVersion.version_number} → 版本 {toVersion.version_number}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-xl"
          >
            ×
          </button>
        </div>

        <div className="flex-1 overflow-hidden flex">
          {/* 左侧：旧版本 */}
          <div className="flex-1 overflow-y-auto p-4 border-r border-slate-700">
            <div className="text-slate-400 text-sm mb-2">
              版本 {fromVersion.version_number}
              <span className="ml-2 text-xs">
                {new Date(fromVersion.created_at).toLocaleString()}
              </span>
            </div>
            <div className="prose prose-invert max-w-none">
              <ReactMarkdown>{fromVersion.content}</ReactMarkdown>
            </div>
          </div>

          {/* 中间：Diff */}
          <div className="flex-1 overflow-y-auto p-4 border-r border-slate-700">
            <div className="text-slate-400 text-sm mb-2">差异对比</div>
            <div className="font-mono text-sm whitespace-pre-wrap">
              {diff.split('\n').map((line, i) => renderDiffLine(line, i))}
            </div>
          </div>

          {/* 右侧：新版本 */}
          <div className="flex-1 overflow-y-auto p-4">
            <div className="text-slate-400 text-sm mb-2">
              版本 {toVersion.version_number}
              <span className="ml-2 text-xs">
                {new Date(toVersion.created_at).toLocaleString()}
              </span>
            </div>
            <div className="prose prose-invert max-w-none">
              <ReactMarkdown>{toVersion.content}</ReactMarkdown>
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-slate-700 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-700 text-white rounded hover:bg-slate-600"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
};

export default VersionDiff;
