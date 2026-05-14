import React, { useState, useEffect } from 'react';
import { getBitmapInfo, operateBitmap } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';

interface Props {
  configId: string;
  keyName: string;
}

export const BitmapEditor: React.FC<Props> = ({ configId, keyName }) => {
  const { addToast } = useToast();
  const [info, setInfo] = useState<any>(null);
  const [offset, setOffset] = useState(0);
  const [bitValue, setBitValue] = useState(1);

  const load = async () => {
    try {
      const data = await getBitmapInfo(configId, keyName);
      setInfo(data);
    } catch (e) {
      addToast('Failed to load bitmap', 'error');
    }
  };

  useEffect(() => { load(); }, [configId, keyName]);

  const handleSetBit = async () => {
    try {
      await operateBitmap(configId, keyName, { action: 'setbit', offset, value: bitValue });
      addToast('Bit updated', 'success');
      load();
    } catch (e) {
      addToast('Failed to set bit', 'error');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center space-x-4 text-sm text-slate-400">
        <span>Bit count: {info?.bit_count || 0}</span>
        <span>Size: {info?.size_in_bytes || 0} bytes</span>
        <span>Bit length: {info?.bit_length || 0}</span>
      </div>

      <div className="border border-slate-700 rounded-md p-3 space-y-3">
        <div className="text-sm font-medium text-slate-300">Set Bit</div>
        <div className="flex space-x-2 items-center">
          <input
            type="number"
            value={offset}
            onChange={e => setOffset(parseInt(e.target.value) || 0)}
            placeholder="Offset"
            className="w-32 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
          />
          <select
            value={bitValue}
            onChange={e => setBitValue(parseInt(e.target.value))}
            className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200"
          >
            <option value={1}>1</option>
            <option value={0}>0</option>
          </select>
          <button onClick={handleSetBit} className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">Set</button>
        </div>
      </div>
    </div>
  );
};
