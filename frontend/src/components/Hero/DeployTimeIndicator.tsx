import { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../config/api';

export default function DeployTimeIndicator() {
  const [deployTime, setDeployTime] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/deploy/timestamp`)
      .then((res) => {
        if (!res.ok) throw new Error('Not found');
        return res.json();
      })
      .then((data) => {
        if (data.timestamp) {
          // 将 ISO 时间转换为本地时间显示
          const date = new Date(data.timestamp + 'Z');
          const formatted = date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false,
          });
          setDeployTime(formatted);
        }
      })
      .catch(() => {
        // 获取失败时不显示
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  if (loading || !deployTime) return null;

  return (
    <div className="flex items-center gap-1.5 text-xs text-slate-500 ml-auto">
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span>上次部署：{deployTime}</span>
    </div>
  );
}
