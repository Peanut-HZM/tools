// frontend/src/components/Harness/TimeTravel/BranchTree.tsx
import type { Branch } from '../../../types/harnessCheckpoint';

export function BranchTree({
  branches,
  activeBranchId,
  onSelectBranch,
}: {
  branches: Branch[];
  activeBranchId: string | null;
  onSelectBranch: (branchId: string) => void;
}) {
  return (
    <div className="space-y-1">
      {branches.map((b) => (
        <div
          key={b.id}
          onClick={() => onSelectBranch(b.id)}
          className={`flex items-center gap-2 p-2 rounded cursor-pointer ${
            b.id === activeBranchId ? 'bg-blue-50' : 'hover:bg-gray-50'
          } ${b.is_archived ? 'opacity-50' : ''}`}
        >
          <span className="text-sm flex-1 truncate">{b.name}</span>
          {b.is_archived && <span className="text-xs text-gray-400">archived</span>}
          {b.id === activeBranchId && <span className="text-xs text-blue-600">●</span>}
        </div>
      ))}
    </div>
  );
}
