import React, { useState, useEffect } from 'react';
import { Loader2, Pencil } from 'lucide-react';
import { getRedisKeyContent, setRedisKey, RedisKeyContent } from '../../../api/redisToolApi';
import { StreamEditor } from './StreamEditor';
import { BitmapEditor } from './BitmapEditor';
import { HyperLogLogEditor } from './HyperLogLogEditor';
import { GeoEditor } from './GeoEditor';
import { useToast } from '../../../hooks/useToast';
import { useI18n } from '../../../i18n';
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

interface Props {
  configId: string;
  keyName: string;
  onKeyUpdated: () => void;
}

export const KeyDetail: React.FC<Props> = ({ configId, keyName, onKeyUpdated }) => {
  const { addToast } = useToast();
  const { t } = useI18n();
  const [content, setContent] = useState<RedisKeyContent | null>(null);
  const [loading, setLoading] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState('');
  const [editTTL, setEditTTL] = useState<number>(-1);

  const loadContent = async () => {
    setLoading(true);
    try {
      const data = await getRedisKeyContent(configId, keyName);
      setContent(data);
      // Format value for editing based on type
      let val = data.value;
      if (typeof val === 'object') {
          val = JSON.stringify(val, null, 2);
      }
      setEditValue(val);
      setEditTTL(data.ttl);
    } catch (error) {
      addToast(t.common.error, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadContent();
    setEditing(false);
  }, [configId, keyName]);

  const handleSave = async () => {
    if (!content) return;
    try {
      let value = editValue;
      // Parse value if original was object (list, set, hash, zset)
      if (content.type !== 'string') {
          try {
              value = JSON.parse(editValue);
          } catch (e) {
              addToast(t.redis.invalidJson, 'error');
              return;
          }
      }

      await setRedisKey(configId, {
        key: keyName,
        type: content.type,
        value: value,
        ttl: editTTL
      });
      addToast(t.redis.keyUpdated, 'success');
      setEditing(false);
      loadContent();
      onKeyUpdated();
    } catch (error) {
      addToast(t.common.error, 'error');
    }
  };

  // Helper to format value
  const formatValue = (value: any) => {
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    // Try to parse string as JSON
    if (typeof value === 'string') {
      try {
        const parsed = JSON.parse(value);
        if (typeof parsed === 'object' && parsed !== null) {
          return JSON.stringify(parsed, null, 2);
        }
      } catch (e) {
        // Not a JSON string, return as is
      }
    }
    return value;
  };

  if (loading) {
    return (
        <div className="flex justify-center items-center h-full text-ink-faint">
            <Loader2 className="w-4 h-4 mr-2 animate-spin" /> {t.common.loading}
        </div>
    );
  }

  if (!content) {
    return <div className="p-8 text-center text-ink-faint">{t.redis.noKeysFound}</div>;
  }

  return (
    <div className="flex flex-col h-full bg-canvas">
      <Card className="rounded-b-none border-b shadow-sm">
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <h3 className="text-lg font-medium text-ink break-all">{content.key}</h3>
              <div className="mt-1 flex space-x-4 text-sm text-ink-muted">
                <Badge variant="secondary" className="uppercase font-mono">{content.type}</Badge>
                <span>TTL: {content.ttl === -1 ? 'None' : `${content.ttl}s`}</span>
              </div>
            </div>
            <div className="space-x-2">
              {!editing ? (
                <Button
                  variant="secondary"
                  onClick={() => setEditing(true)}
                >
                  <Pencil className="w-3.5 h-3.5 mr-1" /> {t.common.edit || 'Edit'}
                </Button>
              ) : (
                <>
                  <Button
                    variant="secondary"
                    onClick={() => { setEditing(false); loadContent(); }}
                  >
                    {t.common.cancel}
                  </Button>
                  <Button
                    onClick={handleSave}
                  >
                    {t.common.save}
                  </Button>
                </>
              )}
            </div>
          </div>
          {editing && (
              <div className="mt-4">
                  <label className="block text-sm font-medium text-ink-muted mb-1">{t.redis.ttl}</label>
                  <Input
                      type="number"
                      value={editTTL}
                      onChange={(e) => setEditTTL(parseInt(e.target.value))}
                      className="block w-32"
                  />
              </div>
          )}
        </CardHeader>
      </Card>
      <CardContent className="flex-1 p-4 overflow-hidden flex flex-col">
        {editing ? (
          <div className="h-full flex flex-col">
            <label className="block text-sm font-medium text-ink-muted mb-2">
              {t.redis.value} {content.type !== 'string' && '(JSON)'}
            </label>
            <textarea
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className="flex-1 w-full bg-surface-1 border border-border rounded-md text-ink font-mono text-sm p-4 focus:outline-none focus:border-blue-500 resize-none"
            />
          </div>
        ) : (
          <Card className="flex-1 overflow-auto">
            <CardContent className="p-4">
              {content.type === 'stream' && (
                <StreamEditor configId={configId} keyName={keyName} />
              )}
              {content.type === 'bitmap' && (
                <BitmapEditor configId={configId} keyName={keyName} />
              )}
              {content.type === 'hyperloglog' && (
                <HyperLogLogEditor configId={configId} keyName={keyName} />
              )}
              {content.type === 'geo' && (
                <GeoEditor configId={configId} keyName={keyName} />
              )}
              {['string', 'list', 'set', 'zset', 'hash'].includes(content.type) && (
                <pre className="font-mono text-sm text-ink-muted whitespace-pre-wrap break-all">
                  {formatValue(content.value)}
                </pre>
              )}
            </CardContent>
          </Card>
        )}
      </CardContent>
    </div>
  );
};
