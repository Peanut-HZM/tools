import React, { useState, useEffect } from 'react';
import { X, Loader2, Trash2, Plus, Save } from 'lucide-react';
import { useI18n } from '../../../../i18n';
import * as api from '../../../../api/databaseToolApi';
import { useToast } from '../../../../hooks/useToast';
import { ColumnDefinition, TableModificationRequest } from '../../../../types/databaseTool';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';

interface ModifyTableDialogProps {
  isOpen: boolean;
  onClose: () => void;
  configId: string;
  databaseName: string;
  tableName: string;
  schemaName?: string;
  onSuccess?: () => void;
}

const COMMON_TYPES = [
  'INT', 'VARCHAR', 'TEXT', 'DATETIME', 'TIMESTAMP', 
  'BIGINT', 'DECIMAL', 'FLOAT', 'DOUBLE', 'BOOLEAN', 'BLOB'
];

const ModifyTableDialog: React.FC<ModifyTableDialogProps> = ({
  isOpen, onClose, configId, databaseName, tableName, schemaName, onSuccess
}) => {
  const { t } = useI18n();
  const toast = useToast();
  const [columns, setColumns] = useState<ColumnDefinition[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [tableComment, setTableComment] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchSchema();
    }
  }, [isOpen, configId, databaseName, tableName]);

  const fetchSchema = async () => {
    setLoading(true);
    try {
      const schema = await api.getTableSchema(configId, tableName, databaseName);
      if (schema) {
        // Map schema columns to ColumnDefinition
        // Note: api.getTableSchema returns generic dicts, we need to adapt
        const cols: ColumnDefinition[] = schema.columns.map((col: any) => ({
          name: col.name,
          type: col.type, // This might need normalization (e.g. VARCHAR(255) -> VARCHAR, 255)
          // For simplicity, we assume col.type from backend is the full string "VARCHAR(255)"
          // But for editing we might want to split it. 
          // However, our backend modify implementation expects full type string or split?
          // The backend modify implementation expects "type" and "length".
          // But "type" in SQLA reflection often includes length.
          // Let's try to parse it roughly.
          length: extractLength(col.type),
          nullable: col.nullable,
          default_value: col.default,
          comment: col.comment,
          primary_key: schema.primary_key?.includes(col.name) || false,
          auto_increment: col.autoincrement || false
        }));
        
        // Clean up type name (remove length)
        cols.forEach(c => {
            if (c.type.includes('(')) {
                c.type = c.type.split('(')[0];
            }
        });

        setColumns(cols);
        setTableComment(schema.comment || '');
      }
    } catch (error) {
      console.error(error);
      toast.error('Failed to load table schema');
    } finally {
      setLoading(false);
    }
  };

  const extractLength = (typeStr: string): string | undefined => {
      const match = typeStr.match(/\(([^)]+)\)/);
      return match ? match[1] : undefined;
  };

  const handleAddColumn = () => {
    setColumns([...columns, {
      name: 'new_column',
      type: 'VARCHAR',
      length: '255',
      nullable: true,
      default_value: '',
      comment: '',
      primary_key: false,
      auto_increment: false
    }]);
  };

  const handleRemoveColumn = (index: number) => {
    const newCols = [...columns];
    newCols.splice(index, 1);
    setColumns(newCols);
  };

  const handleChange = (index: number, field: keyof ColumnDefinition, value: any) => {
    const newCols = [...columns];
    newCols[index] = { ...newCols[index], [field]: value };
    setColumns(newCols);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const request: TableModificationRequest = {
        database_name: databaseName,
        schema_name: schemaName,
        table_name: tableName,
        columns: columns,
        comment: tableComment
      };
      
      await api.modifyTableStructure(configId, request);
      toast.success('Table structure updated');
      if (onSuccess) onSuccess();
      onClose();
    } catch (error: any) {
      console.error(error);
      toast.error(`Failed to update: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
      <Card className="w-11/12 max-w-6xl max-h-[90vh] flex flex-col">
        <div className="flex justify-between items-center p-4 border-b border-border">
          <h3 className="text-lg font-medium text-ink">
            Modify Table: {tableName}
          </h3>
          <button onClick={onClose} className="text-ink-muted hover:text-ink-inverse">
            <X className="w-4 h-4" />
          </button>
        </div>
        
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="flex justify-center items-center h-32">
              <Loader2 className="w-8 h-8 animate-spin text-accent-info" />
            </div>
          ) : (
            <div className="space-y-4">
               {/* Table Comment */}
               <div className="flex items-center gap-2">
                   <label className="text-sm text-ink-muted w-24">Table Comment:</label>
                   <Input
                       type="text"
                       value={tableComment}
                       onChange={(e) => setTableComment(e.target.value)}
                       className="flex-1"
                   />
               </div>

               {/* Columns List */}
               <div className="border border-border rounded overflow-hidden">
                   <table className="min-w-full divide-y divide-slate-700">
                       <thead className="bg-canvas">
                           <tr>
                               <th className="px-3 py-2 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">Name</th>
                               <th className="px-3 py-2 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">Type</th>
                               <th className="px-3 py-2 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">Length</th>
                               <th className="px-3 py-2 text-center text-xs font-medium text-ink-muted uppercase tracking-wider">Nullable</th>
                               <th className="px-3 py-2 text-center text-xs font-medium text-ink-muted uppercase tracking-wider">PK</th>
                               <th className="px-3 py-2 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">Default</th>
                               <th className="px-3 py-2 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">Comment</th>
                               <th className="px-3 py-2 text-center text-xs font-medium text-ink-muted uppercase tracking-wider">Action</th>
                           </tr>
                       </thead>
                       <tbody className="bg-surface-1 divide-y divide-slate-700">
                           {columns.map((col, idx) => (
                               <tr key={idx} className="hover:bg-surface-2/30">
                                   <td className="px-3 py-2">
                                       <Input
                                           type="text"
                                           value={col.name}
                                           onChange={(e) => handleChange(idx, 'name', e.target.value)}
                                           className="text-xs"
                                       />
                                   </td>
                                   <td className="px-3 py-2">
                                       <Input
                                           list={`types-${idx}`}
                                           value={col.type}
                                           onChange={(e) => handleChange(idx, 'type', e.target.value)}
                                           className="text-xs uppercase"
                                       />
                                       <datalist id={`types-${idx}`}>
                                           {COMMON_TYPES.map(t => <option key={t} value={t} />)}
                                       </datalist>
                                   </td>
                                   <td className="px-3 py-2">
                                       <Input
                                           type="text"
                                           value={col.length || ''}
                                           onChange={(e) => handleChange(idx, 'length', e.target.value)}
                                           className="w-20 text-xs"
                                           placeholder="Length"
                                       />
                                   </td>
                                   <td className="px-3 py-2 text-center">
                                       <input 
                                           type="checkbox" 
                                           checked={col.nullable} 
                                           onChange={(e) => handleChange(idx, 'nullable', e.target.checked)}
                                           className="rounded border-border bg-surface-2 text-accent-info"
                                       />
                                   </td>
                                   <td className="px-3 py-2 text-center">
                                       <input 
                                           type="checkbox" 
                                           checked={col.primary_key} 
                                           onChange={(e) => handleChange(idx, 'primary_key', e.target.checked)}
                                           className="rounded border-border bg-surface-2 text-accent-info"
                                       />
                                   </td>
                                   <td className="px-3 py-2">
                                       <Input
                                           type="text"
                                           value={col.default_value || ''}
                                           onChange={(e) => handleChange(idx, 'default_value', e.target.value)}
                                           className="text-xs"
                                       />
                                   </td>
                                   <td className="px-3 py-2">
                                       <Input
                                           type="text"
                                           value={col.comment || ''}
                                           onChange={(e) => handleChange(idx, 'comment', e.target.value)}
                                           className="text-xs"
                                       />
                                   </td>
                                   <td className="px-3 py-2 text-center">
                                       <button 
                                           onClick={() => handleRemoveColumn(idx)}
                                           className="text-danger hover:text-red-300"
                                           title="Remove Column"
                                       >
                                           <Trash2 className="w-4 h-4" />
                                       </button>
                                   </td>
                               </tr>
                           ))}
                       </tbody>
                   </table>
                   <div className="p-2 bg-canvas/50 border-t border-border">
                       <button 
                           onClick={handleAddColumn}
                           className="text-accent-info hover:text-accent-info text-xs flex items-center gap-1"
                       >
                           <Plus className="w-4 h-4" /> Add Column
                       </button>
                   </div>
               </div>
            </div>
          )}
        </div>
        
        <div className="p-4 border-t border-border flex justify-end gap-2">
          <Button
            variant="secondary"
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || loading}
            className="flex items-center gap-2"
          >
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            Save Changes
          </Button>
        </div>
      </Card>
    </div>
  );
};

export default ModifyTableDialog;
