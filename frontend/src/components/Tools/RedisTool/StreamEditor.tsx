import React, { useState, useEffect } from 'react';
import { getStreamInfo, operateStream } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

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

  if (loading) return <div className="text-ink-muted">Loading...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-ink-muted">Length: {info?.length || 0} | Groups: {info?.groups?.length || 0}</div>
      </div>

      <Card className="overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-canvas text-ink-muted">
            <tr><th className="px-3 py-2 text-left">ID</th><th className="px-3 py-2 text-left">Fields</th><th className="px-3 py-2 text-right">Actions</th></tr>
          </thead>
          <tbody>
            {info?.entries?.map((entry: any) => (
              <tr key={entry.id} className="border-t border-border hover:bg-surface-1/50">
                <td className="px-3 py-2 font-mono text-ink-muted">{entry.id}</td>
                <td className="px-3 py-2">
                  {Object.entries(entry.fields).map(([k, v]) => (
                    <Badge key={k} variant="secondary" className="mr-2 text-xs">
                      {k}: {String(v)}
                    </Badge>
                  ))}
                </td>
                <td className="px-3 py-2 text-right">
                  <Button variant="link" size="sm" onClick={() => handleDelete(entry.id)} className="h-auto px-0 py-0 text-danger hover:text-red-300">Delete</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card className="p-3">
        <div className="text-sm font-medium text-ink-muted mb-2">Add Entry</div>
        {newFields.map((f, i) => (
          <div key={i} className="flex space-x-2 mb-2">
            <Input value={f.key} onChange={e => {
              const nf = [...newFields];
              nf[i].key = e.target.value;
              setNewFields(nf);
            }} placeholder="Field" className="flex-1" />
            <Input value={f.value} onChange={e => {
              const nf = [...newFields];
              nf[i].value = e.target.value;
              setNewFields(nf);
            }} placeholder="Value" className="flex-1" />
          </div>
        ))}
        <div className="flex space-x-2">
          <Button variant="link" size="sm" onClick={() => setNewFields([...newFields, { key: '', value: '' }])} className="h-auto px-0 py-0">+ Add field</Button>
          <Button size="sm" onClick={handleAdd}>Add Entry</Button>
        </div>
      </Card>
    </div>
  );
};
