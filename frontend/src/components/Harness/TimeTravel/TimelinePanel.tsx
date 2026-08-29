// frontend/src/components/Harness/TimeTravel/TimelinePanel.tsx
import { useEffect, useState } from 'react';
import {
  listBranches,
  listCheckpoints,
  rollback,
  createBranch,
  mergeBranches,
} from '../../../api/harnessCheckpointsApi';
import type { Branch, Checkpoint } from '../../../types/harnessCheckpoint';
import { BranchTree } from './BranchTree';
import { CheckpointCard } from './CheckpointCard';
import { RollbackConfirmDialog } from './RollbackConfirmDialog';
import { BranchCreateDialog } from './BranchCreateDialog';
import { MergePickerDialog } from './MergePickerDialog';

export function TimelinePanel({ conversationId }: { conversationId: string }) {
  const [branches, setBranches] = useState<Branch[]>([]);
  const [activeBranchId, setActiveBranchId] = useState<string | null>(null);
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [selectedCheckpoint, setSelectedCheckpoint] = useState<Checkpoint | null>(null);
  const [showRollback, setShowRollback] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [showMerge, setShowMerge] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBranches = async () => {
    try {
      const list = await listBranches(conversationId);
      setBranches(list);
      if (!activeBranchId && list.length > 0) {
        const main = list.find((b) => b.name === '主线') || list[0];
        setActiveBranchId(main.id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const loadCheckpoints = async (branchId: string) => {
    try {
      const list = await listCheckpoints(conversationId, branchId);
      setCheckpoints(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  useEffect(() => {
    (async () => {
      setLoading(true);
      await loadBranches();
      setLoading(false);
    })();
  }, [conversationId]);

  useEffect(() => {
    if (activeBranchId) loadCheckpoints(activeBranchId);
  }, [activeBranchId]);

  const handleRollback = async () => {
    if (!selectedCheckpoint) return;
    await rollback(conversationId, selectedCheckpoint.id);
    await loadCheckpoints(activeBranchId!);
    setSelectedCheckpoint(null);
  };

  const handleCreateBranch = async (name: string, _startWithMessages: boolean) => {
    if (!selectedCheckpoint) return;
    await createBranch(conversationId, {
      source_checkpoint_id: selectedCheckpoint.id,
      name,
      start_with_messages: _startWithMessages,
    });
    await loadBranches();
  };

  const handleMerge = async (pickedIds: string[], newName: string) => {
    if (!activeBranchId) return;
    await mergeBranches(conversationId, activeBranchId, {
      picked_checkpoint_ids: pickedIds,
      new_branch_name: newName,
    });
    await loadBranches();
  };

  if (loading) return <div className="p-4 text-gray-500">加载中...</div>;
  if (error) return <div className="p-4 text-red-500">加载失败: {error}</div>;

  const activeBranch = branches.find((b) => b.id === activeBranchId);
  const head = checkpoints.find((c) => c.is_head);

  return (
    <div className="p-4 space-y-3">
      <h3 className="text-sm font-semibold flex items-center gap-2">
        🕐 时间旅行
        {activeBranch && (
          <span className="text-xs text-gray-500">当前: {activeBranch.name}</span>
        )}
      </h3>

      <BranchTree
        branches={branches}
        activeBranchId={activeBranchId}
        onSelectBranch={setActiveBranchId}
      />

      <div className="border-t pt-2 space-y-1">
        {checkpoints.map((cp) => (
          <CheckpointCard
            key={cp.id}
            checkpoint={cp}
            isSelected={selectedCheckpoint?.id === cp.id}
            onClick={() => setSelectedCheckpoint(cp)}
          />
        ))}
      </div>

      {selectedCheckpoint && (
        <div className="border-t pt-3 flex flex-wrap gap-2">
          <button
            onClick={() => setShowRollback(true)}
            className="px-3 py-1 text-sm bg-yellow-100 text-yellow-700 rounded"
          >
            回滚到此
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="px-3 py-1 text-sm bg-purple-100 text-purple-700 rounded"
          >
            从此创建分支
          </button>
          <button
            onClick={() => setShowMerge(true)}
            className="px-3 py-1 text-sm bg-pink-100 text-pink-700 rounded"
          >
            加入合并选择
          </button>
        </div>
      )}

      <RollbackConfirmDialog
        isOpen={showRollback}
        onClose={() => setShowRollback(false)}
        onConfirm={handleRollback}
        currentHeadLabel={head ? `step ${head.step_index}` : '未知'}
        targetLabel={`step ${selectedCheckpoint?.step_index}`}
      />
      <BranchCreateDialog
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        onConfirm={handleCreateBranch}
        sourceLabel={`step ${selectedCheckpoint?.step_index}`}
      />
      <MergePickerDialog
        isOpen={showMerge}
        onClose={() => setShowMerge(false)}
        onConfirm={handleMerge}
        branches={branches}
        checkpointsByBranch={{ [activeBranchId!]: checkpoints }}
      />
    </div>
  );
}
