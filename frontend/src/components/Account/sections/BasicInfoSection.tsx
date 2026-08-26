import React from 'react';
import { UserResponse } from '@/api/authApi';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import SettingCard from '../SettingCard';
import InfoRow from '../InfoRow';
import UserAvatar from '../components/UserAvatar';
import { User, Mail, Hash, Shield, Calendar } from 'lucide-react';
import { useToast } from '@/hooks/useToast';

interface BasicInfoSectionProps {
  user: UserResponse | null;
  loading: boolean;
  onRefresh: () => void;
}

export default function BasicInfoSection({ user, loading, onRefresh }: BasicInfoSectionProps) {
  const { success, error } = useToast();

  const handleCopyUserId = async () => {
    if (!user?.user_id) return;

    try {
      await navigator.clipboard.writeText(user.user_id);
      success('用户 ID 已复制到剪贴板');
    } catch (err) {
      error('复制失败，请手动复制');
    }
  };

  const getRoleBadge = (role: string) => {
    if (role === 'admin') {
      return <Badge>{role}</Badge>;
    }
    return <Badge variant="secondary">{role}</Badge>;
  };

  if (loading) {
    return (
      <SettingCard title="基本信息" icon={<User className="w-5 h-5 text-accent" />}>
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-surface-2 rounded w-1/3"></div>
          <div className="h-4 bg-surface-2 rounded w-2/3"></div>
          <div className="h-4 bg-surface-2 rounded w-1/2"></div>
        </div>
      </SettingCard>
    );
  }

  if (!user) {
    return (
      <SettingCard title="基本信息" icon={<User className="w-5 h-5 text-accent" />}>
        <p className="text-ink-muted text-sm">暂无用户信息</p>
        <Button onClick={onRefresh} size="sm" className="mt-3">
          重新加载
        </Button>
      </SettingCard>
    );
  }

  return (
    <SettingCard title="基本信息" icon={<User className="w-5 h-5 text-accent" />}>
      <div className="flex items-start gap-6 mb-6">
        <UserAvatar username={user.username} size="lg" />
        <div className="flex-1 pt-2">
          <h4 className="text-xl font-semibold text-ink-inverse">{user.username}</h4>
          <div className="mt-1">{getRoleBadge(user.role)}</div>
        </div>
      </div>

      <div className="space-y-1">
        <InfoRow
          label="用户 ID"
          value={<span className="font-mono text-xs">{user.user_id}</span>}
          copyable
          onCopy={handleCopyUserId}
        />
        <InfoRow
          label="用户名"
          value={user.username}
        />
        <InfoRow
          label="邮箱"
          value={user.email}
        />
        <InfoRow
          label="角色"
          value={getRoleBadge(user.role)}
        />
        <InfoRow
          label="注册时间"
          value={new Date(user.created_at).toLocaleString('zh-CN')}
        />
      </div>
    </SettingCard>
  );
}
