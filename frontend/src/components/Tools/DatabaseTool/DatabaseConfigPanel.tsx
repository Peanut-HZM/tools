import React, { useState, useEffect } from 'react';
import { useDatabaseTool } from '../../../contexts/DatabaseToolContext';
import { CreateDatabaseRequest, UpdateDatabaseRequest, DatabaseType, Environment } from '../../../types/databaseTool';
import * as api from '../../../api/databaseToolApi';
import { useToast } from '../../../hooks/useToast';
import { useI18n } from '../../../i18n';
import { useAuth } from '../../../stores';
import { Card } from '@/components/ui/Card';

interface DatabaseConfigPanelProps {
  editConfigId?: string | null;
  onClose: () => void;
}

const DatabaseConfigPanel: React.FC<DatabaseConfigPanelProps> = ({ editConfigId, onClose }) => {
  const { refreshConfigs, configs } = useDatabaseTool();
  const toast = useToast();
  const { t } = useI18n();
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [decryptedPassword, setDecryptedPassword] = useState<string>('');
  
  const [formData, setFormData] = useState<CreateDatabaseRequest>({
    alias: '',
    db_type: DatabaseType.MYSQL,
    host: 'localhost',
    port: 3306,
    database_name: '',
    username: '',
    password: '',
    environment: Environment.DEV,
    charset: 'utf8mb4',
    connect_timeout: 10,
    max_pool_size: 10,
    ssl_mode: 'disable',
    is_active: true
  });

  useEffect(() => {
    if (editConfigId) {
      const config = configs.find(c => c.id === editConfigId);
      if (config) {
        setFormData({
          alias: config.alias,
          db_type: config.db_type,
          host: config.host,
          port: config.port,
          database_name: config.database_name,
          username: config.username,
          password: config.password || '',
          environment: config.environment,
          charset: config.charset,
          connect_timeout: config.connect_timeout,
          max_pool_size: config.max_pool_size,
          ssl_mode: config.ssl_mode,
          is_active: config.is_active
        });
      }
    }
  }, [editConfigId, configs]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? Number(value) : value
    }));
  };

  const handleTestConnection = async () => {
    setTesting(true);
    try {
      const result = await api.testConnection({
        ...formData,
        ssl_cert_path: undefined // Not supported in UI yet
      });
      if (result.success) {
        toast.success(`${t.database.status.success} (${result.elapsed_ms?.toFixed(0)}ms)`);
      } else {
        // 优先使用 error_code 对应的本地化文案，fallback 到后端返回的 message
        const errorMsg = (result.error_code && t.database.errors[result.error_code as keyof typeof t.database.errors])
          || result.message;
        toast.error(`${t.database.status.failed}: ${errorMsg}`);
      }
    } catch (error) {
      toast.error(t.database.status.failed);
    } finally {
      setTesting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (editConfigId) {
        // Update - only send password if actually changed (not masked placeholder)
        const updateData: UpdateDatabaseRequest = { ...formData };
        if (!updateData.password || updateData.password === '••••••••') {
          delete updateData.password;
        }
        
        await api.updateDatabase(editConfigId, updateData);
        toast.success(t.common.success);
      } else {
        // Create
        await api.createDatabase(formData);
        toast.success(t.common.success);
      }
      await refreshConfigs();
      onClose();
    } catch (error: any) {
      toast.error(error.message || t.common.error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!editConfigId || !window.confirm(t.fileTree.deleteConfirm.replace('{name}', formData.alias))) return;
    
    setLoading(true);
    try {
      await api.deleteDatabase(editConfigId);
      toast.success(t.common.success);
      await refreshConfigs();
      onClose();
    } catch (error: any) {
      toast.error(error.message || t.errors.deleteFailed);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-center p-6 border-b border-border">
          <h2 className="text-xl font-semibold text-ink">
            {editConfigId ? t.database.editConnection : t.database.addConnection}
          </h2>
          <button onClick={onClose} className="text-ink-muted hover:text-ink transition-colors">
            <i className="fas fa-times text-xl"></i>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          <div className="grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-6">
            
            {/* Alias & Environment */}
            <div className="sm:col-span-4">
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.database.config.alias}</label>
              <input
                type="text"
                name="alias"
                required
                value={formData.alias}
                onChange={handleChange}
                className="block w-full bg-canvas border border-border rounded-md shadow-sm py-2 px-3 text-ink focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent sm:text-sm transition-all"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.database.config.env}</label>
              <select
                name="environment"
                value={formData.environment}
                onChange={handleChange}
                className="block w-full bg-canvas border border-border rounded-md shadow-sm py-2 px-3 text-ink focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent sm:text-sm transition-all"
              >
                {Object.values(Environment).map(env => (
                  <option key={env} value={env}>{env.toUpperCase()}</option>
                ))}
              </select>
            </div>

            {/* DB Type */}
            <div className="sm:col-span-6">
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.database.config.type}</label>
              <select
                name="db_type"
                value={formData.db_type}
                onChange={handleChange}
                className="block w-full bg-canvas border border-border rounded-md shadow-sm py-2 px-3 text-ink focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent sm:text-sm transition-all"
              >
                {Object.values(DatabaseType).map(type => (
                  <option key={type} value={type}>{type.toUpperCase()}</option>
                ))}
              </select>
            </div>

            {/* Host & Port */}
            <div className="sm:col-span-4">
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.database.config.host}</label>
              <input
                type="text"
                name="host"
                required
                value={formData.host}
                onChange={handleChange}
                className="block w-full bg-canvas border border-border rounded-md shadow-sm py-2 px-3 text-ink focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent sm:text-sm transition-all"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.database.config.port}</label>
              <input
                type="number"
                name="port"
                required
                value={formData.port}
                onChange={handleChange}
                className="block w-full bg-canvas border border-border rounded-md shadow-sm py-2 px-3 text-ink focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent sm:text-sm transition-all"
              />
            </div>

            {/* Database Name */}
            <div className="sm:col-span-6">
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.database.config.database}</label>
              <input
                type="text"
                name="database_name"
                placeholder="Optional (Leave empty to list all databases)"
                value={formData.database_name}
                onChange={handleChange}
                className="block w-full bg-canvas border border-border rounded-md shadow-sm py-2 px-3 text-ink focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent sm:text-sm transition-all"
              />
            </div>

            {/* Username & Password */}
            <div className="sm:col-span-3">
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.database.config.username}</label>
              <input
                type="text"
                name="username"
                required
                value={formData.username}
                onChange={handleChange}
                className="block w-full bg-canvas border border-border rounded-md shadow-sm py-2 px-3 text-ink focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent sm:text-sm transition-all"
              />
            </div>
            <div className="sm:col-span-3">
              <label className="block text-sm font-medium text-ink-muted mb-1">{t.database.config.password}</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  placeholder={editConfigId ? (showPassword ? decryptedPassword : '••••••••') : ""}
                  required={!editConfigId}
                  value={formData.password}
                  onChange={handleChange}
                  className="block w-full bg-canvas border border-border rounded-md shadow-sm py-2 px-3 text-ink focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent sm:text-sm transition-all"
                />
                {editConfigId && (
                  <button
                    type="button"
                    onClick={() => {
                      if (!showPassword) {
                        api.decryptPassword(editConfigId).then((pw) => {
                          setDecryptedPassword(pw);
                          setShowPassword(true);
                        }).catch(() => {
                          toast.error(t.common.error);
                        });
                      } else {
                        setShowPassword(false);
                      }
                    }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-ink-muted hover:text-ink transition-colors"
                    title={showPassword ? 'Hide Password' : 'Show Password'}
                  >
                    <i className={`fas ${showPassword ? 'fa-eye-slash' : 'fa-eye'}`}></i>
                  </button>
                )}
              </div>
            </div>

          </div>

          <div className="flex justify-between pt-5 border-t border-border">
             {editConfigId ? (
               <button
                 type="button"
                 onClick={handleDelete}
                 disabled={loading}
                 className="bg-danger/10 text-danger border border-red-500/50 px-4 py-2 rounded-md text-sm font-medium hover:bg-danger/20 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
               >
                 {t.common.delete}
               </button>
             ) : <div></div>}
             
             <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testing || loading}
                  className="bg-surface-2 border border-border text-ink px-4 py-2 rounded-md text-sm font-medium hover:bg-surface-3 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-border transition-colors"
                >
                  {testing ? t.database.status.testing : t.database.testConnection}
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  disabled={loading}
                  className="bg-surface-2 border border-border text-ink px-4 py-2 rounded-md text-sm font-medium hover:bg-surface-3 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-border transition-colors"
                >
                  {t.common.cancel}
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="bg-accent border border-transparent text-ink-inverse px-4 py-2 rounded-md text-sm font-medium hover:bg-accent-hover focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent transition-colors"
                >
                  {loading ? t.common.loading : t.common.save}
                </button>
             </div>
          </div>
        </form>
      </Card>
    </div>
  );
};

export default DatabaseConfigPanel;
