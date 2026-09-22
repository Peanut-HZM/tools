/**
 * EnvironmentSelector - 环境选择器（顶栏）
 *
 * 下拉切换环境（直接调后端激活）+ 打开环境管理弹窗
 */

import { Environment } from '../../../../services/httpClientApi';
import { Settings2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select';

interface EnvironmentSelectorProps {
  environments: Environment[];
  activeEnvironment: Environment | null;
  onEnvironmentChange: (envId: string) => void;
  onManage: () => void;
}

export default function EnvironmentSelector({
  environments,
  activeEnvironment,
  onEnvironmentChange,
  onManage,
}: EnvironmentSelectorProps) {
  return (
    <div className="flex items-center gap-1">
      <Select
        value={activeEnvironment?.id || '__none__'}
        onValueChange={onEnvironmentChange}
      >
        <SelectTrigger className="h-8 text-xs w-36 gap-1" title="切换环境">
          <SelectValue placeholder="无环境" />
        </SelectTrigger>
        <SelectContent>
          {environments.map(env => (
            <SelectItem key={env.id} value={env.id} className="text-xs">
              {env.name}
            </SelectItem>
          ))}
          {environments.length === 0 && (
            <SelectItem value="__none__" disabled>
              暂无环境
            </SelectItem>
          )}
        </SelectContent>
      </Select>

      <Button
        variant="ghost"
        size="icon"
        onClick={onManage}
        title="管理环境（前置 URL / 变量）"
        className="h-8 w-8 text-ink-muted hover:text-ink"
      >
        <Settings2 className="w-4 h-4" />
      </Button>
    </div>
  );
}
