import React, { useState, useEffect } from 'react';

interface Version {
  id: string;
  version_number: number;
  created_at: string;
  status: 'draft' | 'confirmed' | 'archived';
}

interface VersionHistoryProps {
  conversationId: string;
  versions: Version[];
  onSelect: (version: Version) => void;
  onRollback: (version: Version) => void;
  onCompare: (v1: Version, v2: Version) => void;
}

const VersionHistory: React.FC<VersionHistoryProps> = ({
  conversationId,
  versions,
  onSelect,
  onRollback,
  onCompare,
}) => {
  const [selectedVersions, setSelectedVersions] = useState<Version[]>([]);

  const toggleVersionSelection = (version: Version) => {
    setSelectedVersions((prev) => {
      const exists = prev.find((v) => v.id === version.id);
      if (exists) {
        return prev.filter((v) => v.id !== version.id);
      }
      if (prev.length >= 2) {
        return [prev[1], version];
      }
      return [...prev, version];
    });
  };

  const handleCompare = () => {
    if (selectedVersions.length === 2) {
      onCompare(selectedVersions[0], selectedVersions[1]);
    }
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<string, string> = {
      draft: 'bg-yellow-500/20 text-yellow-400',
      confirmed: 'bg-green-500/20 text-green-400',
      archived: 'bg-slate-500/20 text-slate-400',
    };
    const labels: Record<string, string> = {
      draft: '草稿',
      confirmed: '已确认',
      archived: '已归档',
    };
    return (
      <span className={`px-2 py-1 rounded text-xs ${styles[status] || styles.draft}`}>
        {labels[status] || status}
      </span>
    );
  };

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700">
      <div className="p-4 border-b border-slate-700 flex justify-between items-center">
        <h3 className="text-white font-semibold">版本历史</h3>
        {selectedVersions.length === 2 && (
          <button
            onClick={handleCompare}
            className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
          >
            对比选中版本
          </button>
        )}
      </div>

      <div className="max-h-96 overflow-y-auto">
        {versions.length === 0 ? (
          <div className="p-8 text-center text-slate-400">
            暂无版本历史
          </div>
        ) : (
          versions.map((version) => (
            <div
              key={version.id}
              className={`p-4 border-b border-slate-700 hover:bg-slate-700/50 cursor-pointer ${
                selectedVersions.find((v) => v.id === version.id)
                  ? 'bg-slate-700/50 border-l-4 border-l-blue-500'
                  : ''
              }`}
              onClick={() => onSelect(version)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={!!selectedVersions.find((v) => v.id === version.id)}
                    onChange={(e) => {
                      e.stopPropagation();
                      toggleVersionSelection(version);
                    }}
                    className="w-4 h-4 rounded border-slate-600"
                  />
                  <span className="text-white font-medium">
                    版本 {version.version_number}
                  </span>
                  {getStatusBadge(version.status)}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-slate-400 text-sm">
                    {new Date(version.created_at).toLocaleString()}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm(`确定要回滚到版本 ${version.version_number} 吗？`)) {
                        onRollback(version);
                      }
                    }}
                    className="px-2 py-1 text-xs text-red-400 hover:text-red-300 border border-red-400/30 rounded"
                  >
                    回滚
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default VersionHistory;
