import React, { useState, useEffect } from 'react';
import { getStreamInfo, operateStream } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';

interface Props {
  configId: string;
  keyName: string;
}

export const StreamEditor: React.FC<Props> = ({ configId, keyName }) => {
  const { addToast } = useToast();
  const [info, setInfo] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [newFields, setNewFields] = useState<{ key: string; value: string }[]>([{ key: '', value: '' }]);

  const load = async () => {
    try {
      const data = await getStreamInfo(configId, keyName);
      setInfo(data);
    } catch (e) {
      addToast('Failed to load stream', 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [configId, keyName]);

  const handleAdd = async () => {
    const fields: Record<string, string> = {};
    newFields.forEach(f => { if (f.key) fields[f.key] = f.value; });
    if (Object.keys(fields).length === 0) return;
    try {
      await operateStream(configId, keyName, { action: 'add', fields });
      addToast('Entry added', 'success');
      setNewFields([{ key: '', value: '' }]);
      load();
    } catch (e) {
      addToast('Failed to add entry', 'error');
    }
  };

  const handleDelete = async (entryId: string) => {
    if (!confirm(`Delete entry ${entryId}?`)) return;
    try {
      await operateStream(configId, keyName, { action: 'delete', entry_id: entryId });
      addToast('Entry deleted', 'success');
      load();
    } catch (e) {
      addToast('Failed to delete', 'error');
    }
  };

  if (loading) return <div className="text-slate-400">Loading...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-400">Length: {info?.length || 0} | Groups: {info?.groups?.length || 0}</div>
      </div>

      <div className="border border-slate-700 rounded-md overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr><th className="px-3 py-2 text-left">ID</th><th className="px-3 py-2 text-left">Fields</th><th className="px-3 py-2 text-right">Actions</th></tr>
          </thead>
          <tbody>
            {info?.entries?.map((entry: any) => (
              <tr key={entry.id} className="border-t border-slate-700 hover:bg-slate-800/50">
                <td className="px-3 py-2 font-mono text-slate-300">{entry.id}</td>
                <td className="px-3 py-2">
                  {Object.entries(entry.fields).map(([k, v]) => (
                    <span key={k} className="inline-block mr-2 text-xs bg-slate-700 px-1.5 py-0.5 rounded">
                      {k}: {String(v)}
                    </span>
                  ))}
                </td>
                <td className="px-3 py-2 text-right">
                  <button onClick={() => handleDelete(entry.id)} className="text-red-400 hover:text-red-300 text-xs">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="border border-slate-700 rounded-md p-3">
        <div className="text-sm font-medium text-slate-300 mb-2">Add Entry</div>
        {newFields.map((f, i) => (
          <div key={i} className="flex space-x-2 mb-2">
            <input value={f.key} onChange={e => {
              const nf = [...newFields];
              nf[i].key = e.target.value;
              setNewFields(nf);
            }} placeholder="Field" className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200" />
            <input value={f.value} onChange={e => {
              const nf = [...newFields];
              nf[i].value = e.target.value;
              setNewFields(nf);
            }} placeholder="Value" className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-sm text-slate-200" />
          </div>
        ))}
        <div className="flex space-x-2">
          <button onClick={() => setNewFields([...newFields, { key: '', value: '' }])} className="text-xs text-blue-400 hover:text-blue-300">+ Add field</button>
          <button onClick={handleAdd} className="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">Add Entry</button>
        </div>
      </div>
    </div>
  );
};
