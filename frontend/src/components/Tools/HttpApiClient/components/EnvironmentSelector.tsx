import { Environment } from '../../../../services/httpClientApi';

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
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedEnv = environments.find(env => env.id === e.target.value);
    if (selectedEnv && onEnvironmentChange) {
      onEnvironmentChange(selectedEnv);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-400">环境:</span>
      <select
        value={activeEnvironment?.id || ''}
        onChange={handleChange}
        className="bg-slate-700 text-white px-3 py-1.5 rounded border border-slate-600 text-sm
                   focus:border-purple-500 focus:outline-none"
      >
        {environments.map(env => (
          <option key={env.id} value={env.id}>
            {env.name} {env.is_active ? '(当前)' : ''}
          </option>
        ))}
      </select>

      {activeEnvironment && Object.keys(activeEnvironment.variables).length > 0 && (
        <div className="flex items-center gap-1 ml-2" title="环境变量">
          {Object.entries(activeEnvironment.variables).slice(0, 3).map(([key, value]) => (
            <span
              key={key}
              className="text-xs bg-slate-700 px-2 py-1 rounded text-slate-400"
            >
              {key}={value}
            </span>
          ))}
          {Object.keys(activeEnvironment.variables).length > 3 && (
            <span className="text-xs text-slate-500">
              +{Object.keys(activeEnvironment.variables).length - 3}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
