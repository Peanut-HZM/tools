import React, { useState } from 'react';
import { useI18n } from '../../../../i18n';
import { Loader2 } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';

interface CreateDatabaseDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (name: string, charset: string) => Promise<void>;
}

const CreateDatabaseDialog: React.FC<CreateDatabaseDialogProps> = ({ isOpen, onClose, onSubmit }) => {
  const { t } = useI18n();
  const [name, setName] = useState('');
  const [charset, setCharset] = useState('utf8mb4');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setLoading(true);
    setError(null);
    try {
      await onSubmit(name, charset);
      onClose();
      setName('');
    } catch (err: any) {
      setError(err.message || t.database.dialog.createDatabase.error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-96 p-4">
        <h3 className="text-lg font-semibold text-ink mb-4">{t.database.dialog.createDatabase.title}</h3>
        
        {error && (
          <div className="bg-red-900/30 text-danger p-2 rounded text-sm mb-4 border border-red-800/50">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-ink-muted mb-1">{t.database.dialog.createDatabase.name}</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-canvas border border-border rounded px-3 py-2 text-ink focus:outline-none focus:border-accent"
                placeholder="my_database"
                autoFocus
              />
            </div>
            
            <div>
              <label className="block text-sm text-ink-muted mb-1">{t.database.dialog.createDatabase.charset}</label>
              <Select
                value={charset}
                onValueChange={setCharset}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="utf8mb4">utf8mb4</SelectItem>
                  <SelectItem value="utf8">utf8</SelectItem>
                  <SelectItem value="latin1">latin1</SelectItem>
                  <SelectItem value="ascii">ascii</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex justify-end space-x-2 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-ink-muted hover:text-ink-inverse hover:bg-surface-2 rounded transition-colors"
              disabled={loading}
            >
              {t.database.dialog.createDatabase.cancel}
            </button>
            <button
              type="submit"
              className="px-3 py-1.5 bg-accent text-ink-inverse rounded hover:bg-accent-hover transition-colors disabled:opacity-50 flex items-center"
              disabled={loading || !name.trim()}
            >
              {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {t.database.dialog.createDatabase.create}
            </button>
          </div>
        </form>
      </Card>
    </div>
  );
};

export default CreateDatabaseDialog;
