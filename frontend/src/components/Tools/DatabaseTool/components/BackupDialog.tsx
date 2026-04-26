import React, { useState, useEffect, useCallback } from 'react';
import * as api from '../../../../api/databaseToolApi';
import { useToast } from '../../../../hooks/useToast';
import { useI18n } from '../../../../i18n';
import { BackupMode } from '../../../../types/databaseTool';

interface BackupDialogProps {
  isOpen: boolean;
  onClose: () => void;
  configId: string;
  databaseName: string;
  preselectedTables?: string[];
}

interface TableInfo {
  name: string;
  rowCount: number;
  selected: boolean;
}

const BackupDialog: React.FC<BackupDialogProps> = ({
  isOpen,
  onClose,
  configId,
  databaseName,
  preselectedTables,
}) => {
  const toast = useToast();
  const { t } = useI18n();
  const [tables, setTables] = useState<TableInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [backingUp, setBackingUp] = useState(false);
  const [backupResult, setBackupResult] = useState<api.BackupResponse | null>(null);

  const [backupMode, setBackupMode] = useState<BackupMode>('structure_and_data');
  const [includeDrop, setIncludeDrop] = useState(false);
  const [includeIfNotExists, setIncludeIfNotExists] = useState(true);
  const [selectAll, setSelectAll] = useState(true);

  const fetchTables = useCallback(async () => {
    setLoading(true);
    try {
      const structure = await api.getDatabaseStructure(configId, databaseName);
      const tableItems = structure.tables || [];

      const infos: TableInfo[] = await Promise.all(
        tableItems.map(async (item) => {
          let rowCount = 0;
          try {
            const countRes = await api.getTableRowCount(configId, item.name, databaseName);
            rowCount = countRes.row_count;
          } catch {
            // ignore
          }
          return {
            name: item.name,
            rowCount,
            selected: preselectedTables ? preselectedTables.includes(item.name) : true,
          };
        })
      );

      setTables(infos);
      setSelectAll(infos.every((t) => t.selected));
    } catch (error: any) {
      toast.error(`Failed to load tables: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [configId, databaseName, preselectedTables, toast]);

  useEffect(() => {
    if (isOpen) {
      fetchTables();
      setBackupResult(null);
      setBackingUp(false);
    }
  }, [isOpen, fetchTables]);

  const handleSelectAll = () => {
    const newValue = !selectAll;
    setSelectAll(newValue);
    setTables((prev) => prev.map((t) => ({ ...t, selected: newValue })));
  };

  const handleToggleTable = (index: number) => {
    setTables((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], selected: !next[index].selected };
      setSelectAll(next.every((t) => t.selected));
      return next;
    });
  };

  const handleBackup = async () => {
    const selectedTables = tables.filter((t) => t.selected).map((t) => t.name);
    if (selectedTables.length === 0) {
      toast.error(t.database.dialog.backup.atLeastOneTable);
      return;
    }

    setBackingUp(true);
    try {
      const result = await api.backupDatabase(configId, {
        database_name: databaseName,
        backup_mode: backupMode,
        tables: selectedTables,
        include_drop: includeDrop,
        include_if_not_exists: includeIfNotExists,
      });
      setBackupResult(result);
      toast.success(`Backup created: ${result.file_name} (${formatSize(result.file_size)})`);
    } catch (error: any) {
      toast.error(t.database.dialog.backup.backupFailed.replace('{error}', error.message));
    } finally {
      setBackingUp(false);
    }
  };

  const handleDownload = () => {
    if (!backupResult) return;
    const url = api.getBackupDownloadUrl(backupResult.backup_id);
    window.open(url, '_blank');
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatNumber = (n: number): string => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return `${n}`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col border border-slate-700">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b border-slate-700">
          <h3 className="text-lg font-medium text-slate-100 flex items-center gap-2">
            <i className="fas fa-archive text-blue-400"></i>
            {t.database.dialog.backup.title}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <i className="fas fa-times"></i>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4 space-y-4">
          {backupResult ? (
            /* Result View */
            <div className="space-y-4">
              <div className="bg-green-900/20 border border-green-800/50 rounded-lg p-4">
                <div className="flex items-center gap-2 text-green-400 mb-2">
                  <i className="fas fa-check-circle"></i>
                  <span className="font-medium">{t.database.dialog.backup.backupSuccess}</span>
                </div>
                <div className="text-sm text-slate-300 space-y-1">
                  <p>{t.database.dialog.backup.backupFile}: <span className="text-slate-100">{backupResult.file_name}</span></p>
                  <p>{t.database.dialog.backup.backupSize}: <span className="text-slate-100">{formatSize(backupResult.file_size)}</span></p>
                  <p>{t.database.dialog.backup.backupTables}: <span className="text-slate-100">{backupResult.tables_count}</span></p>
                  <p>{t.database.dialog.backup.backupModeLabel}: <span className="text-slate-100 capitalize">{backupResult.backup_mode.replace(/_/g, ' ')}</span></p>
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setBackupResult(null)}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded text-sm transition-colors"
                >
                  {t.database.dialog.backup.newBackup}
                </button>
                <button
                  onClick={handleDownload}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm transition-colors flex items-center gap-2"
                >
                  <i className="fas fa-download"></i>
                  {t.database.dialog.backup.download}
                </button>
              </div>
            </div>
          ) : (
            /* Backup Form */
            <>
              {/* Table Selection */}
              <div className="border border-slate-700 rounded-lg overflow-hidden">
                <div className="bg-slate-900/50 px-3 py-2 flex items-center justify-between border-b border-slate-700">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectAll}
                      onChange={handleSelectAll}
                      className="rounded border-slate-600 bg-slate-700 text-blue-600"
                    />
                    <span className="text-sm text-slate-300 font-medium">
                      {t.database.dialog.backup.selectTables} {t.database.dialog.backup.selectedCount.replace('{selected}', String(tables.filter((t) => t.selected).length)).replace('{total}', String(tables.length))}
                    </span>
                  </label>
                  {loading && <i className="fas fa-spinner fa-spin text-slate-500 text-xs"></i>}
                </div>
                <div className="max-h-48 overflow-y-auto">
                  {loading && tables.length === 0 ? (
                    <div className="p-4 text-center text-slate-500 text-sm">
                      <i className="fas fa-spinner fa-spin mr-2"></i>
                      {t.database.dialog.backup.loadingTables}
                    </div>
                  ) : (
                    tables.map((table, idx) => (
                      <label
                        key={table.name}
                        className="flex items-center gap-3 px-3 py-2 hover:bg-slate-700/30 cursor-pointer border-b border-slate-800/50 last:border-0"
                      >
                        <input
                          type="checkbox"
                          checked={table.selected}
                          onChange={() => handleToggleTable(idx)}
                          className="rounded border-slate-600 bg-slate-700 text-blue-600"
                        />
                        <i className="fas fa-table text-slate-500 text-xs"></i>
                        <span className="text-sm text-slate-200 flex-1">{table.name}</span>
                        <span className="text-xs text-slate-500">{formatNumber(table.rowCount)} rows</span>
                      </label>
                    ))
                  )}
                </div>
              </div>

              {/* Backup Mode */}
              <div className="space-y-2">
                <p className="text-sm text-slate-400 font-medium flex items-center gap-2">
                  <i className="fas fa-sliders-h text-xs text-slate-500"></i>
                  {t.database.dialog.backup.backupMode}
                </p>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { value: 'structure_and_data' as BackupMode, label: t.database.dialog.backup.modeStructureData, icon: 'fa-cubes', desc: t.database.dialog.backup.modeDescFull, color: 'blue' },
                    { value: 'structure_only' as BackupMode, label: t.database.dialog.backup.modeStructureOnly, icon: 'fa-project-diagram', desc: t.database.dialog.backup.modeDescDDL, color: 'amber' },
                    { value: 'data_only' as BackupMode, label: t.database.dialog.backup.modeDataOnly, icon: 'fa-database', desc: t.database.dialog.backup.modeDescInsert, color: 'emerald' },
                  ].map((mode) => {
                    const isActive = backupMode === mode.value;
                    const colorMap: Record<string, { active: string; inactive: string; icon: string }> = {
                      blue: {
                        active: 'border-blue-500/60 bg-blue-500/10 shadow-sm shadow-blue-500/5',
                        inactive: 'border-slate-700/50 hover:border-slate-600 hover:bg-slate-700/20',
                        icon: 'text-blue-400',
                      },
                      amber: {
                        active: 'border-amber-500/60 bg-amber-500/10 shadow-sm shadow-amber-500/5',
                        inactive: 'border-slate-700/50 hover:border-slate-600 hover:bg-slate-700/20',
                        icon: 'text-amber-400',
                      },
                      emerald: {
                        active: 'border-emerald-500/60 bg-emerald-500/10 shadow-sm shadow-emerald-500/5',
                        inactive: 'border-slate-700/50 hover:border-slate-600 hover:bg-slate-700/20',
                        icon: 'text-emerald-400',
                      },
                    };
                    const colors = colorMap[mode.color];
                    return (
                      <label
                        key={mode.value}
                        className={`flex flex-col items-center gap-1.5 p-3 rounded-lg border cursor-pointer transition-all ${
                          isActive ? colors.active : colors.inactive
                        }`}
                      >
                        <input
                          type="radio"
                          name="backupMode"
                          value={mode.value}
                          checked={isActive}
                          onChange={() => setBackupMode(mode.value)}
                          className="sr-only"
                        />
                        <i className={`fas ${mode.icon} text-base ${isActive ? colors.icon : 'text-slate-500'}`}></i>
                        <span className={`text-xs font-medium ${isActive ? 'text-slate-100' : 'text-slate-400'}`}>{mode.label}</span>
                        <span className="text-[10px] text-slate-500">{mode.desc}</span>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Options */}
              <div className="bg-slate-900/30 rounded-lg border border-slate-700/30 p-3 space-y-2">
                <label className="flex items-center gap-2.5 cursor-pointer group">
                  <div className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
                    includeDrop ? 'bg-blue-600 border-blue-500' : 'border-slate-600 group-hover:border-slate-500'
                  }`}>
                    {includeDrop && <i className="fas fa-check text-white text-[8px]"></i>}
                    <input
                      type="checkbox"
                      checked={includeDrop}
                      onChange={(e) => setIncludeDrop(e.target.checked)}
                      className="sr-only"
                    />
                  </div>
                  <span className="text-sm text-slate-300">{t.database.dialog.backup.includeDropTable}</span>
                </label>
                <label className="flex items-center gap-2.5 cursor-pointer group">
                  <div className={`w-4 h-4 rounded border flex items-center justify-center transition-colors ${
                    includeIfNotExists ? 'bg-blue-600 border-blue-500' : 'border-slate-600 group-hover:border-slate-500'
                  }`}>
                    {includeIfNotExists && <i className="fas fa-check text-white text-[8px]"></i>}
                    <input
                      type="checkbox"
                      checked={includeIfNotExists}
                      onChange={(e) => setIncludeIfNotExists(e.target.checked)}
                      className="sr-only"
                    />
                  </div>
                  <span className="text-sm text-slate-300">{t.database.dialog.backup.includeIfNotExists}</span>
                </label>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        {!backupResult && (
          <div className="p-4 border-t border-slate-700 flex justify-end gap-2">
            <button
              onClick={onClose}
              disabled={backingUp}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded text-sm transition-colors disabled:opacity-50"
            >
              {t.common.cancel}
            </button>
            <button
              onClick={handleBackup}
              disabled={backingUp || tables.filter((t) => t.selected).length === 0}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded text-sm transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {backingUp && <i className="fas fa-spinner fa-spin text-xs"></i>}
              <i className="fas fa-archive"></i>
              {backingUp ? t.database.dialog.backup.backingUp : t.database.dialog.backup.startBackup}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default BackupDialog;
