import { Environment } from '../../../../services/httpClientApi';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select';

interface EnvironmentSelectorProps {
  environments: Environment[];
  activeEnvironment: Environment | null;
  onEnvironmentChange?: (env: Environment) => void;
}

export default function EnvironmentSelector({
  environments,
  activeEnvironment,
  onEnvironmentChange,
}: EnvironmentSelectorProps) {
  const handleChange = (value: string) => {
    const selectedEnv = environments.find(env => env.id === value);
    if (selectedEnv && onEnvironmentChange) {
      onEnvironmentChange(selectedEnv);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-ink-muted">环境:</span>
      <Select
        value={activeEnvironment?.id || ''}
        onValueChange={handleChange}
      >
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {environments.map(env => (
            <SelectItem key={env.id} value={env.id}>
              {env.name} {env.is_active ? '(当前)' : ''}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {activeEnvironment && Object.keys(activeEnvironment.variables).length > 0 && (
        <div className="flex items-center gap-1 ml-2" title="环境变量">
          {Object.entries(activeEnvironment.variables).slice(0, 3).map(([key, value]) => (
            <span
              key={key}
              className="text-xs bg-surface-2 px-2 py-1 rounded text-ink-muted"
            >
              {key}={value}
            </span>
          ))}
          {Object.keys(activeEnvironment.variables).length > 3 && (
            <span className="text-xs text-ink-faint">
              +{Object.keys(activeEnvironment.variables).length - 3}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
