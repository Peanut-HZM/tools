import React, { useState, useEffect } from 'react';
import { getHyperLogLogInfo, operateHyperLogLog } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";

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
      <div className="text-sm text-ink-muted">
        Cardinality (estimated unique elements): <span className="text-ink-inverse font-mono text-lg">{info?.cardinality || 0}</span>
      </div>

      <div className="border border-border rounded-md p-3 space-y-2">
        <div className="text-sm font-medium text-ink-muted">Add Element</div>
        <div className="flex space-x-2">
          <Input
            value={element}
            onChange={e => setElement(e.target.value)}
            placeholder="Element value"
            className="flex-1"
          />
          <Button size="sm" onClick={handleAdd}>Add</Button>
        </div>
      </div>
    </div>
  );
};
