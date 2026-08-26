import { useState, useEffect } from 'react';
import { useI18n } from '../../i18n';
import {
  getContactMessages,
  updateContactMessage,
  deleteContactMessage,
  batchUpdateMessageStatus,
  batchDeleteMessages,
  ContactMessage,
} from '../../services/contactApi';
import { useToast } from '../../hooks/useToast';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
type MessageStatus = 'unread' | 'read' | 'processing' | 'resolved';

export default function ContactMessagesManagement() {
  const { t } = useI18n();
  const { toasts, addToast, removeToast, error, success } = useToast();

  const [messages, setMessages] = useState<ContactMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [keyword, setKeyword] = useState('');

  // 详情弹窗
  const [selectedMessage, setSelectedMessage] = useState<ContactMessage | null>(null);
  const [replyContent, setReplyContent] = useState('');

  // 批量选择
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  useEffect(() => {
    fetchMessages();
  }, [page, statusFilter]);

  const fetchMessages = async () => {
    setLoading(true);
    try {
      const data = await getContactMessages(page, pageSize, statusFilter !== 'all' ? statusFilter : undefined, keyword || undefined);
      setMessages(data.items);
      setTotal(data.total);
    } catch (err) {
      error(t.admin.contactMessages.replyFailed);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setPage(1);
    fetchMessages();
  };

  const handleStatusChange = async (id: string, status: MessageStatus) => {
    try {
      await updateContactMessage(id, { status });
      success(t.admin.contactMessages.replySuccess);
      fetchMessages();
    } catch (err) {
      error(t.admin.contactMessages.replyFailed);
    }
  };

  const handleReply = async (id: string) => {
    try {
      await updateContactMessage(id, { admin_reply: replyContent });
      success(t.admin.contactMessages.replySuccess);
      setSelectedMessage(null);
      setReplyContent('');
      fetchMessages();
    } catch (err) {
      error(t.admin.contactMessages.replyFailed);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm(t.admin.contactMessages.deleteConfirm)) {
      return;
    }

    try {
      await deleteContactMessage(id);
      success(t.admin.contactMessages.deleteSuccess);
      fetchMessages();
    } catch (err) {
      error(t.admin.contactMessages.deleteFailed);
    }
  };

  const handleBatchUpdate = async (status: MessageStatus) => {
    if (selectedIds.length === 0) {
      error('请先选择要更新的留言');
      return;
    }

    try {
      await batchUpdateMessageStatus(selectedIds, status);
      success(`成功更新 ${selectedIds.length} 条留言状态`);
      setSelectedIds([]);
      fetchMessages();
    } catch (err) {
      error('批量更新失败');
    }
  };

  const handleBatchDelete = async () => {
    if (selectedIds.length === 0) {
      error('请先选择要删除的留言');
      return;
    }

    if (!window.confirm(t.admin.contactMessages.batchDeleteConfirm.replace('{count}', String(selectedIds.length)))) {
      return;
    }

    try {
      await batchDeleteMessages(selectedIds);
      success(`成功删除 ${selectedIds.length} 条留言`);
      setSelectedIds([]);
      fetchMessages();
    } catch (err) {
      error('批量删除失败');
    }
  };

  const toggleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(messages.map(m => m.id));
    } else {
      setSelectedIds([]);
    }
  };

  const toggleSelect = (id: string, checked: boolean) => {
    if (checked) {
      setSelectedIds(prev => [...prev, id]);
    } else {
      setSelectedIds(prev => prev.filter(sid => sid !== id));
    }
  };

  const getStatusBadgeClass = (status: string) => {
    const classes = {
      unread: 'bg-blue-900 text-blue-300 border-blue-700',
      read: 'bg-gray-700 text-gray-300 border-gray-600',
      processing: 'bg-yellow-900 text-yellow-300 border-yellow-700',
      resolved: 'bg-green-900 text-green-300 border-green-700',
    };
    return classes[status as keyof typeof classes] || classes.read;
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      unread: t.admin.contactMessages.status.unread,
      read: t.admin.contactMessages.status.read,
      processing: t.admin.contactMessages.status.processing,
      resolved: t.admin.contactMessages.status.resolved,
    };
    return labels[status] || status;
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div>      {/* 页面标题 */}
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-ink-inverse mb-2">{t.admin.contactMessages.title}</h2>
        <p className="text-ink-muted">{t.admin.contactMessages.listTitle}</p>
      </div>

      {/* 筛选和操作栏 */}
      <Card className="p-4 mb-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          {/* 筛选器 */}
          <div className="flex items-center gap-3">
            {/* 状态筛选 */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink-inverse text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer"
            >
              <option value="all">{t.admin.contactMessages.filter.all}</option>
              <option value="unread">{t.admin.contactMessages.filter.unread}</option>
              <option value="read">{t.admin.contactMessages.filter.read}</option>
              <option value="processing">{t.admin.contactMessages.filter.processing}</option>
              <option value="resolved">{t.admin.contactMessages.filter.resolved}</option>
            </select>

            {/* 关键词搜索 */}
            <input
              type="text"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder={t.admin.contactMessages.keywordSearch}
              className="px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink-inverse text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64"
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <Button
              onClick={handleSearch}
              size="sm"
            >
              <i className="fas fa-search mr-1"></i> 搜索
            </Button>
          </div>

          {/* 批量操作 */}
          {selectedIds.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-ink-muted text-sm">已选择 {selectedIds.length} 条</span>
              <button
                onClick={() => handleBatchUpdate('read')}
                className="px-3 py-1.5 bg-gray-600 hover:bg-gray-500 text-ink-inverse rounded text-sm cursor-pointer"
              >
                标记为已读
              </button>
              <button
                onClick={() => handleBatchUpdate('processing')}
                className="px-3 py-1.5 bg-yellow-600 hover:bg-yellow-500 text-ink-inverse rounded text-sm cursor-pointer"
              >
                处理中
              </button>
              <button
                onClick={() => handleBatchUpdate('resolved')}
                className="px-3 py-1.5 bg-green-600 hover:bg-green-500 text-ink-inverse rounded text-sm cursor-pointer"
              >
                已完成
              </button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleBatchDelete}
              >
                删除
              </Button>
            </div>
          )}
        </div>
      </Card>

      {/* 留言列表 */}
      <Card className="overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        ) : messages.length === 0 ? (
          <div className="flex items-center justify-center py-12 text-ink-muted">
            <i className="fas fa-inbox text-4xl mb-4"></i>
            <p>{t.admin.contactMessages.noData}</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-canvas border-b border-border">
              <tr>
                <th className="px-4 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={selectedIds.length === messages.length && messages.length > 0}
                    onChange={(e) => toggleSelectAll(e.target.checked)}
                    className="cursor-pointer"
                  />
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">
                  {t.admin.contactMessages.name}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">
                  {t.admin.contactMessages.email}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">
                  {t.admin.contactMessages.subject}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">
                  {t.admin.contactMessages.statusLabel}
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-ink-muted uppercase tracking-wider">
                  {t.admin.contactMessages.createdAt}
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-ink-muted uppercase tracking-wider">
                  {t.admin.contactMessages.actions}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {messages.map((message) => (
                <tr
                  key={message.id}
                  className={`hover:bg-surface-2/50 transition-colors ${
                    message.status === 'unread' ? 'bg-blue-900/10' : ''
                  }`}
                >
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(message.id)}
                      onChange={(e) => toggleSelect(message.id, e.target.checked)}
                      className="cursor-pointer"
                    />
                  </td>
                  <td className="px-4 py-3 text-ink-inverse">{message.name}</td>
                  <td className="px-4 py-3 text-ink-muted">{message.email}</td>
                  <td className="px-4 py-3 text-ink-muted max-w-xs truncate" title={message.subject || ''}>
                    {message.subject || '-'}
                  </td>
                  <td className="px-4 py-3">
                    <select
                      value={message.status}
                      onChange={(e) => handleStatusChange(message.id, e.target.value as MessageStatus)}
                      className={`px-2 py-1 rounded text-xs border cursor-pointer ${getStatusBadgeClass(message.status)}`}
                    >
                      <option value="unread">{t.admin.contactMessages.status.unread}</option>
                      <option value="read">{t.admin.contactMessages.status.read}</option>
                      <option value="processing">{t.admin.contactMessages.status.processing}</option>
                      <option value="resolved">{t.admin.contactMessages.status.resolved}</option>
                    </select>
                  </td>
                  <td className="px-4 py-3 text-ink-muted text-sm">
                    {new Date(message.created_at).toLocaleString('zh-CN')}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        size="sm"
                        onClick={() => {
                          setSelectedMessage(message);
                          setReplyContent(message.admin_reply || '');
                        }}
                      >
                        {t.admin.contactMessages.viewDetail}
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDelete(message.id)}
                      >
                        {t.admin.contactMessages.delete}
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6">
          <p className="text-ink-muted text-sm">
            共 {total} 条留言，第 {page} 页 / 共 {totalPages} 页
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              上一页
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
            >
              下一页
            </Button>
          </div>
        </div>
      )}

      {/* 详情弹窗 */}
      {selectedMessage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => setSelectedMessage(null)} />
          <div className="relative bg-surface-1 rounded-xl shadow-lg w-full max-w-2xl mx-4 max-h-[80vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-border flex items-center justify-between sticky top-0 bg-surface-1 z-10">
              <h3 className="text-xl font-semibold text-ink-inverse">{t.admin.contactMessages.detailTitle}</h3>
              <button
                onClick={() => setSelectedMessage(null)}
                className="text-ink-muted hover:text-ink-inverse transition-colors p-1 rounded-lg hover:bg-surface-2 cursor-pointer"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-4">
              {/* 基本信息 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-ink-muted">{t.admin.contactMessages.name}</label>
                  <p className="text-ink-inverse">{selectedMessage.name}</p>
                </div>
                <div>
                  <label className="text-sm text-ink-muted">{t.admin.contactMessages.email}</label>
                  <p className="text-ink-inverse">{selectedMessage.email}</p>
                </div>
                <div>
                  <label className="text-sm text-ink-muted">{t.admin.contactMessages.subject}</label>
                  <p className="text-ink-inverse">{selectedMessage.subject || '-'}</p>
                </div>
                <div>
                  <label className="text-sm text-ink-muted">{t.admin.contactMessages.status}</label>
                  <p className="text-ink-inverse">{getStatusLabel(selectedMessage.status)}</p>
                </div>
                <div>
                  <label className="text-sm text-ink-muted">{t.admin.contactMessages.createdAt}</label>
                  <p className="text-ink-inverse">{new Date(selectedMessage.created_at).toLocaleString('zh-CN')}</p>
                </div>
              </div>

              {/* 留言内容 */}
              <div>
                <label className="text-sm text-ink-muted mb-1 block">{t.admin.contactMessages.content}</label>
                <div className="bg-surface-2 rounded-lg p-4 text-ink-inverse whitespace-pre-wrap">
                  {selectedMessage.content}
                </div>
              </div>

              {/* 管理员回复 */}
              <div>
                <label className="text-sm text-ink-muted mb-1 block">{t.admin.contactMessages.adminReply}</label>
                <textarea
                  value={replyContent}
                  onChange={(e) => setReplyContent(e.target.value)}
                  placeholder={t.admin.contactMessages.replyPlaceholder}
                  rows={4}
                  className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-ink-inverse placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>

              {/* 操作按钮 */}
              <div className="flex justify-end gap-3 pt-4 border-t border-border">
                <select
                  value={selectedMessage.status}
                  onChange={(e) => handleStatusChange(selectedMessage.id, e.target.value as MessageStatus)}
                  className={`px-3 py-2 rounded border cursor-pointer ${getStatusBadgeClass(selectedMessage.status)}`}
                >
                  <option value="unread">{t.admin.contactMessages.status.unread}</option>
                  <option value="read">{t.admin.contactMessages.status.read}</option>
                  <option value="processing">{t.admin.contactMessages.status.processing}</option>
                  <option value="resolved">{t.admin.contactMessages.status.resolved}</option>
                </select>
                <Button
                  onClick={() => handleReply(selectedMessage.id)}
                >
                  {t.admin.contactMessages.saveReply}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
