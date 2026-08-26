import React, { useState, useEffect, useCallback } from 'react';
import * as api from '../../../../api/databaseToolApi';
import { useToast } from '../../../../hooks/useToast';
import { useI18n } from '../../../../i18n';
import { BackupRecord } from '../../../../types/databaseTool';
import { History, X, Loader2, Inbox, FileArchive, Download, Trash2, ChevronLeft, ChevronRight, Boxes, Workflow, Database, File } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';

interface BackupHistoryDialogProps {
  isOpen: boolean;
  onClose: () => void;
  configId: string;
  databaseName?: string;
}

const BackupHistoryDialog: React.FC<BackupHistoryDialogProps> = ({
  isOpen,
  onClose,
  configId,
  databaseName,
}) => {
  const toast = useToast();
  const { t } = useI18n();
  const [records, setRecords] = useState<BackupRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchBackups = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api.listBackups(configId, databaseName, page, 20);
      setRecords(result.records);
      setTotalPages(result.total_pages);
    } catch (error: any) {
      toast.error(`Failed to load backups: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [configId, databaseName, page, toast]);

  useEffect(() => {
    if (isOpen) {
      fetchBackups();
    }
  }, [isOpen, fetchBackups]);

  const handleDownload = (record: BackupRecord) => {
    const url = api.getBackupDownloadUrl(record.id);
    window.open(url, '_blank');
  };

  const handleDelete = async (record: BackupRecord) => {
    const confirmMsg = t.database.dialog.backup.deleteBackupConfirm.replace('{file}', record.file_name);
    if (!window.confirm(confirmMsg)) return;

    setDeletingId(record.id);
    try {
      await api.deleteBackup(record.id);
      toast.success(t.database.dialog.backup.deleteSuccess);
      await fetchBackups();
    } catch (error: any) {
      toast.error(t.database.dialog.backup.deleteFailed);
    } finally {
      setDeletingId(null);
    }
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatDate = (iso: string): string => {
    const d = new Date(iso);
    return d.toLocaleString();
  };

  const getModeBadge = (mode: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'> = {
      structure_and_data: 'default',
      structure_only: 'warning',
      data_only: 'success',
    };
    const icons: Record<string, any> = {
      structure_and_data: Boxes,
      structure_only: Workflow,
      data_only: Database,
    };
    const labels: Record<string, string> = {
      structure_and_data: t.database.dialog.backup.modeStructureData,
      structure_only: t.database.dialog.backup.modeStructureOnly,
      data_only: t.database.dialog.backup.modeDataOnly,
    };
    const Icon = icons[mode] || File;
    return (
      <Badge variant={variants[mode] || 'secondary'} className="gap-1 text-[10px] py-0.5">
        <Icon className="w-2 h-2" />
        {labels[mode] || mode.replace(/_/g, ' ')}
      </Badge>
    );
  };

  if (!isOpen) return null;

  const th = t.database.dialog.backupHistory;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <Card className="w-full max-w-3xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b border-border">
          <h3 className="text-lg font-medium text-ink flex items-center gap-2">
            <History className="w-4 h-4 text-accent-info" />
            {th.title}
            {databaseName && <span className="text-sm text-ink-faint">({databaseName})</span>}
          </h3>
          <button onClick={onClose} className="text-ink-muted hover:text-ink transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {loading && records.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-ink-faint">
              <Loader2 className="w-8 h-8 mb-2 opacity-50 animate-spin" />
              <span className="text-sm">{th.loading}</span>
            </div>
          ) : records.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-ink-faint">
              <Inbox className="w-8 h-8 mb-2 opacity-30" />
              <p className="text-sm">{th.noBackups}</p>
            </div>
          ) : (
            <div className="border border-border/50 rounded-lg overflow-hidden">
              <table className="min-w-full divide-y divide-border">
                <thead>
                  <tr className="bg-canvas/70">
                    <th className="px-3 py-2.5 text-left text-[10px] font-semibold text-ink-faint uppercase tracking-wider">{th.columnFile}</th>
                    <th className="px-3 py-2.5 text-left text-[10px] font-semibold text-ink-faint uppercase tracking-wider">{th.columnMode}</th>
                    <th className="px-3 py-2.5 text-left text-[10px] font-semibold text-ink-faint uppercase tracking-wider">{th.columnSize}</th>
                    <th className="px-3 py-2.5 text-left text-[10px] font-semibold text-ink-faint uppercase tracking-wider">{th.columnTables}</th>
                    <th className="px-3 py-2.5 text-left text-[10px] font-semibold text-ink-faint uppercase tracking-wider">{th.columnDate}</th>
                    <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-ink-faint uppercase tracking-wider">{th.columnActions}</th>
                  </tr>
                </thead>
                <tbody className="bg-surface-1/50 divide-y divide-border">
                  {records.map((record) => (
                    <tr key={record.id} className="hover:bg-surface-2/20 transition-colors group/row">
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <FileArchive className="w-3 h-3 text-ink-faint group-hover/row:text-ink-faint transition-colors" />
                          <div className="text-sm text-ink truncate max-w-[180px]" title={record.file_name}>
                            {record.file_name}
                          </div>
                        </div>
                        {record.status !== 'success' && (
                          <span className="text-[10px] text-danger font-medium">{record.status}</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5">{getModeBadge(record.backup_mode)}</td>
                      <td className="px-3 py-2.5 text-sm text-ink-muted font-mono">{formatSize(record.file_size)}</td>
                      <td className="px-3 py-2.5 text-sm text-ink-muted">{record.tables_count}</td>
                      <td className="px-3 py-2.5 text-xs text-ink-faint whitespace-nowrap">
                        {formatDate(record.created_at)}
                      </td>
                      <td className="px-3 py-2.5 text-right">
                        <div className="flex items-center justify-end gap-1 opacity-70 group-hover/row:opacity-100 transition-opacity">
                          <button
                            onClick={() => handleDownload(record)}
                            className="p-1.5 text-ink-faint hover:text-accent hover:bg-surface-2/50 rounded transition-colors"
                            title={th.download}
                          >
                            <Download className="w-3 h-3" />
                          </button>
                          <button
                            onClick={() => handleDelete(record)}
                            disabled={deletingId === record.id}
                            className="p-1.5 text-ink-faint hover:text-danger hover:bg-surface-2/50 rounded transition-colors disabled:opacity-50"
                            title={th.delete}
                          >
                            {deletingId === record.id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <Trash2 className="w-3 h-3" />
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-4">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || loading}
                className="px-3 py-1 bg-surface-2 hover:bg-surface-3 text-ink-muted rounded text-sm disabled:opacity-50"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-ink-muted">
                {th.page.replace('{current}', String(page)).replace('{total}', String(totalPages))}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages || loading}
                className="px-3 py-1 bg-surface-2 hover:bg-surface-3 text-ink-muted rounded text-sm disabled:opacity-50"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
};

export default BackupHistoryDialog;
