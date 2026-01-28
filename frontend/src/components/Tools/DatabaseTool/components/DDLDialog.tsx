import React, { useState, useEffect } from 'react';
import { useI18n } from '../../../../i18n';
import * as api from '../../../../api/databaseToolApi';
import { useToast } from '../../../../hooks/useToast';

interface DDLDialogProps {
  isOpen: boolean;
  onClose: () => void;
  configId: string;
  databaseName: string;
  tableName: string;
}

const DDLDialog: React.FC<DDLDialogProps> = ({ isOpen, onClose, configId, databaseName, tableName }) => {
  const { t } = useI18n();
  const toast = useToast();
  const [ddl, setDdl] = useState<string>('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchDDL();
    }
  }, [isOpen, configId, databaseName, tableName]);

  const fetchDDL = async () => {
    setLoading(true);
    try {
      const sql = await api.getTableDDL(configId, tableName, databaseName);
      setDdl(sql);
    } catch (error) {
      console.error(error);
      toast.error(t.common.error);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(ddl);
    toast.success(t.common.success);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
      <div className="bg-slate-800 rounded-lg shadow-xl w-3/4 max-w-4xl max-h-[90vh] flex flex-col border border-slate-700">
        <div className="flex justify-between items-center p-4 border-b border-slate-700">
          <h3 className="text-lg font-medium text-slate-100">
            DDL: {tableName}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <i className="fas fa-times"></i>
          </button>
        </div>
        
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="flex justify-center items-center h-32">
              <i className="fas fa-spinner fa-spin text-2xl text-blue-500"></i>
            </div>
          ) : (
            <pre className="bg-slate-900 p-4 rounded text-sm text-slate-300 font-mono overflow-auto whitespace-pre-wrap">
              {ddl}
            </pre>
          )}
        </div>
        
        <div className="p-4 border-t border-slate-700 flex justify-end gap-2">
          <button
            onClick={handleCopy}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded text-sm transition-colors"
          >
            <i className="fas fa-copy mr-2"></i>
            Copy
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm transition-colors"
          >
            {t.common.close}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DDLDialog;
