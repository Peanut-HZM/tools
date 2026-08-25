import { useState } from 'react';
import { useI18n } from '../../i18n';
import { submitContactMessage } from '../../services/contactApi';

interface ContactModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ContactModal({ isOpen, onClose }: ContactModalProps) {
  const { t } = useI18n();

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    content: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = t.contactModal.nameRequired;
    }

    if (!formData.email.trim()) {
      newErrors.email = t.contactModal.emailRequired;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = t.contactModal.emailInvalid;
    }

    if (!formData.content.trim()) {
      newErrors.content = t.contactModal.contentRequired;
    } else if (formData.content.trim().length < 10) {
      newErrors.content = t.contactModal.contentMinLength;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    setSubmitStatus('idle');

    try {
      await submitContactMessage({
        name: formData.name.trim(),
        email: formData.email.trim(),
        subject: formData.subject.trim() || undefined,
        content: formData.content.trim(),
      });

      setSubmitStatus('success');
      setFormData({ name: '', email: '', subject: '', content: '' });

      // 关闭弹窗延迟
      setTimeout(() => {
        onClose();
        setSubmitStatus('idle');
      }, 2000);
    } catch (error) {
      console.error('提交留言失败:', error);
      setSubmitStatus('error');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    // 清除错误
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* 背景遮罩 */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      />

      {/* 弹窗内容 */}
      <div className="relative bg-surface-1 rounded-xl shadow-lg w-full max-w-md mx-4 overflow-hidden animate-fade-in">
        {/* 头部 */}
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-white">{t.contactModal.title}</h3>
            <p className="text-sm text-ink-faint mt-1">{t.contactModal.subtitle}</p>
          </div>
          <button
            onClick={onClose}
            className="text-ink-faint hover:text-white transition-colors p-1 rounded-lg hover:bg-surface-2"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* 表单 */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* 姓名 */}
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-ink-muted mb-1">
              {t.contactModal.name}
            </label>
            <input
              type="text"
              id="name"
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder={t.contactModal.namePlaceholder}
              className={`w-full px-3 py-2 bg-surface-2 border rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.name ? 'border-red-500' : 'border-border'
              }`}
            />
            {errors.name && (
              <p className="mt-1 text-sm text-danger">{errors.name}</p>
            )}
          </div>

          {/* 邮箱 */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-ink-muted mb-1">
              {t.contactModal.email}
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder={t.contactModal.emailPlaceholder}
              className={`w-full px-3 py-2 bg-surface-2 border rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                errors.email ? 'border-red-500' : 'border-border'
              }`}
            />
            {errors.email && (
              <p className="mt-1 text-sm text-danger">{errors.email}</p>
            )}
          </div>

          {/* 主题 */}
          <div>
            <label htmlFor="subject" className="block text-sm font-medium text-ink-muted mb-1">
              {t.contactModal.subject}
            </label>
            <input
              type="text"
              id="subject"
              name="subject"
              value={formData.subject}
              onChange={handleChange}
              placeholder={t.contactModal.subjectPlaceholder}
              className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* 留言内容 */}
          <div>
            <label htmlFor="content" className="block text-sm font-medium text-ink-muted mb-1">
              {t.contactModal.content}
            </label>
            <textarea
              id="content"
              name="content"
              value={formData.content}
              onChange={handleChange}
              placeholder={t.contactModal.contentPlaceholder}
              rows={5}
              className={`w-full px-3 py-2 bg-surface-2 border rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none ${
                errors.content ? 'border-red-500' : 'border-border'
              }`}
            />
            {errors.content && (
              <p className="mt-1 text-sm text-danger">{errors.content}</p>
            )}
          </div>

          {/* 提交状态提示 */}
          {submitStatus === 'success' && (
            <div className="p-3 bg-green-900 bg-opacity-50 border border-green-700 rounded-lg text-green-300 text-sm">
              {t.contactModal.submitSuccess}
            </div>
          )}

          {submitStatus === 'error' && (
            <div className="p-3 bg-red-900 bg-opacity-50 border border-red-700 rounded-lg text-red-300 text-sm">
              {t.contactModal.submitFailed}
            </div>
          )}

          {/* 按钮 */}
          <div className="flex space-x-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-surface-2 hover:bg-surface-3 text-ink-muted rounded-lg transition-colors border border-border cursor-pointer disabled:opacity-50"
            >
              {t.contactModal.cancel}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? t.contactModal.submitting : t.contactModal.submit}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
