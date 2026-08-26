import React, { useState } from 'react';
import { setRedisKey } from '../../../api/redisToolApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n } from '../../../i18n';
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/Select";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  configId: string;
  onSuccess: () => void;
}

export const AddKeyModal: React.FC<Props> = ({ isOpen, onClose, configId, onSuccess }) => {
  const { addToast } = useToast();
  const { t } = useI18n();
  const [key, setKey] = useState('');
  const [type, setType] = useState('string');
  const [value, setValue] = useState('');
  const [ttl, setTtl] = useState<number>(-1);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      let parsedValue: any = value;
      if (type !== 'string') {
        try {
          parsedValue = JSON.parse(value);
        } catch (e) {
          addToast(t.redis.invalidJson, 'error');
          return;
        }
      }

      await setRedisKey(configId, {
        key,
        type,
        value: parsedValue,
        ttl
      });
      addToast(t.redis.keyCreated, 'success');
      onSuccess();
      onClose();
      // Reset form
      setKey('');
      setType('string');
      setValue('');
      setTtl(-1);
    } catch (error) {
      addToast(t.common.error, 'error');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-surface-1 rounded-lg shadow-md w-full max-w-md p-6 border border-border">
        <h2 className="text-xl font-bold mb-4 text-ink-inverse">{t.redis.addKey}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-ink-muted mb-1">{t.redis.keys}</label>
            <Input
              type="text"
              required
              className="w-full"
              value={key}
              onChange={e => setKey(e.target.value)}
              placeholder="my:key:name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-ink-muted mb-1">{t.redis.type}</label>
            <Select
              value={type}
              onValueChange={setType}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="string">{t.redis.keyType.string}</SelectItem>
                <SelectItem value="list">{t.redis.keyType.list} (JSON Array)</SelectItem>
                <SelectItem value="set">{t.redis.keyType.set} (JSON Array)</SelectItem>
                <SelectItem value="hash">{t.redis.keyType.hash} (JSON Object)</SelectItem>
                <SelectItem value="zset">{t.redis.keyType.zset} (JSON Object/Array)</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div>
            <label className="block text-sm font-medium text-ink-muted mb-1">{t.redis.ttl}</label>
            <Input
              type="number"
              className="w-full"
              value={ttl}
              onChange={e => setTtl(parseInt(e.target.value))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-ink-muted mb-1">{t.redis.value}</label>
            <textarea
              required
              rows={4}
              className="w-full bg-canvas border border-border rounded-md px-3 py-2 text-sm text-ink-inverse focus:outline-none focus:border-blue-500 font-mono"
              value={value}
              onChange={e => setValue(e.target.value)}
              placeholder={type === 'string' ? 'Value' : 'JSON content'}
            />
          </div>
          <div className="flex justify-end space-x-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
            >
              {t.common.cancel}
            </Button>
            <Button
              type="submit"
            >
              {t.common.create}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
