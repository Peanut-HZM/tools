import React, { useState, useEffect } from 'react';
import { getHyperLogLogInfo, operateHyperLogLog } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';

interface Props {
  configId: string;
  keyName: string;
}

export const HyperLogLogEditor: React.FC<Props> = ({ configId, keyName }) => {
  const { addToast } = useToast();
  const [info, setInfo] = useState<any>(null);
  const [element, setElement] = useState('');

  const load = async () => {
    try {
      const data = await getHyperLogLogInfo(configId, keyName);
      setInfo(data);
    } catch (e) {
      addToast('Failed to load HLL', 'error');
    }
  };

  useEffect(() => { load(); }, [configId, keyName]);

  const handleAdd = async () => {
    if (!element.trim()) return;
    try {
      await operateHyperLogLog(configId, keyName, { action: 'add', elements: [element.trim()] });
      addToast('Element added', 'success');
      setElement('');
      load();
    } catch (e) {
      addToast('Failed to add', 'error');
    }
  };

  return (
    <div className="space-y-4">
      <div className="text-sm text-slate-400">
        Cardinality (estimated unique elements): <span className="text-white font-mono text-lg">{info?.cardinality || 0}</span>
      </div>

      <div className="border border-slate-700 rounded-md p-3 space-y-2">
        <div className="text-sm font-medium text-slate-300">Add Element</div>
        <div className="flex space-x-2">
          <input
            value={element}
            onChange={e => setElement(e.target.value)}
            placeholder="Element value"
            className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
          />
          <button onClick={handleAdd} className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">Add</button>
        </div>
      </div>
    </div>
  );
};
