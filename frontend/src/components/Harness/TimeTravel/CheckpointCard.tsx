// frontend/src/components/Harness/TimeTravel/CheckpointCard.tsx
import type { Checkpoint } from '../../../types/harnessCheckpoint';

export function CheckpointCard({
  checkpoint,
  isSelected,
  onClick,
}: {
  checkpoint: Checkpoint;
  isSelected: boolean;
  onClick: () => void;
}) {
  const bg = isSelected ? 'bg-blue-50' : 'hover:bg-gray-50';
  return (
    <div
      onClick={onClick}
      className={`flex items-center gap-3 p-2 rounded cursor-pointer ${bg}`}
    >
      <KindBadge kind={checkpoint.checkpoint_kind} />
      <span className="text-sm flex-1 truncate">
        step {checkpoint.step_index} — {checkpoint.phase}
      </span>
      {checkpoint.label && (
        <span className="text-xs text-gray-500">{checkpoint.label}</span>
      )}
      <span className="text-xs text-gray-400">
        {new Date(checkpoint.created_at).toLocaleTimeString()}
      </span>
      {checkpoint.is_head && <span className="text-xs text-green-600">HEAD</span>}
    </div>
  );
}

function KindBadge({ kind }: { kind: string }) {
  const color = {
    auto: 'bg-gray-100 text-gray-700',
    manual: 'bg-yellow-100 text-yellow-700',
    branch_point: 'bg-purple-100 text-purple-700',
    merge_commit: 'bg-pink-100 text-pink-700',
  }[kind] || 'bg-gray-100 text-gray-700';
  return <span className={`text-xs px-2 py-0.5 rounded ${color}`}>{kind}</span>;
}
