import React, { useState } from 'react';
import { useI18n } from '../../../../i18n';

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
      <div className="bg-slate-800 rounded-lg shadow-xl border border-slate-700 w-96 p-4">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">{t.database.dialog.createDatabase.title}</h3>
        
        {error && (
          <div className="bg-red-900/30 text-red-400 p-2 rounded text-sm mb-4 border border-red-800/50">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">{t.database.dialog.createDatabase.name}</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
                placeholder="my_database"
                autoFocus
              />
            </div>
            
            <div>
              <label className="block text-sm text-slate-400 mb-1">{t.database.dialog.createDatabase.charset}</label>
              <select
                value={charset}
                onChange={(e) => setCharset(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-200 focus:outline-none focus:border-blue-500"
              >
                <option value="utf8mb4">utf8mb4</option>
                <option value="utf8">utf8</option>
                <option value="latin1">latin1</option>
                <option value="ascii">ascii</option>
              </select>
            </div>
          </div>

          <div className="flex justify-end space-x-2 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-slate-300 hover:text-white hover:bg-slate-700 rounded transition-colors"
              disabled={loading}
            >
              {t.database.dialog.createDatabase.cancel}
            </button>
            <button
              type="submit"
              className="px-3 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-500 transition-colors disabled:opacity-50 flex items-center"
              disabled={loading || !name.trim()}
            >
              {loading && <i className="fas fa-spinner fa-spin mr-2"></i>}
              {t.database.dialog.createDatabase.create}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateDatabaseDialog;
