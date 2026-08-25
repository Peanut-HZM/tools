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
      draft: 'bg-accent-warning/20 text-accent-warning',
      confirmed: 'bg-green-500/20 text-green-400',
      archived: 'bg-surface-2/20 text-ink-muted',
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
    <div className="bg-surface-1 rounded-lg border border-border">
      <div className="p-4 border-b border-border flex justify-between items-center">
        <h3 className="text-ink-inverse font-semibold">版本历史</h3>
        {selectedVersions.length === 2 && (
          <button
            onClick={handleCompare}
            className="px-3 py-1 bg-accent text-white rounded text-sm hover:bg-accent-hover"
          >
            对比选中版本
          </button>
        )}
      </div>

      <div className="max-h-96 overflow-y-auto">
        {versions.length === 0 ? (
          <div className="p-8 text-center text-ink-muted">
            暂无版本历史
          </div>
        ) : (
          versions.map((version) => (
            <div
              key={version.id}
              className={`p-4 border-b border-border hover:bg-surface-2/50 cursor-pointer ${
                selectedVersions.find((v) => v.id === version.id)
                  ? 'bg-surface-2/50 border-l-4 border-l-accent-info'
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
                    className="w-4 h-4 rounded border-border"
                  />
                  <span className="text-ink-inverse font-medium">
                    版本 {version.version_number}
                  </span>
                  {getStatusBadge(version.status)}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-ink-muted text-sm">
                    {new Date(version.created_at).toLocaleString()}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm(`确定要回滚到版本 ${version.version_number} 吗？`)) {
                        onRollback(version);
                      }
                    }}
                    className="px-2 py-1 text-xs text-danger hover:text-danger border border-danger/30 rounded"
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
