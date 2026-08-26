/**
 * 主题切换组件
 */
import { useState, useEffect } from 'react';
import { Palette, Check } from 'lucide-react';
import { themes, applyTheme, getSavedTheme, saveTheme } from '../../../themes/cursorThemes';

export default function ThemeSwitcher() {
  const [isOpen, setIsOpen] = useState(false);
  const [currentTheme, setCurrentTheme] = useState(() => getSavedTheme()?.id || 'deep-space');

  useEffect(() => {
    const savedTheme = getSavedTheme();
    if (savedTheme) {
      applyTheme(savedTheme);
      setCurrentTheme(savedTheme.id);
    }
  }, []);

  const handleThemeChange = (themeId: string) => {
    const theme = themes.find(t => t.id === themeId);
    if (theme) {
      applyTheme(theme);
      saveTheme(themeId);
      setCurrentTheme(themeId);
      setIsOpen(false);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 hover:bg-surface-2 rounded transition-colors text-ink-muted hover:text-ink-inverse"
        title="切换主题"
      >
        <Palette className="w-4 h-4" />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 p-3 bg-surface-1 border border-border rounded-lg shadow-lg z-50 w-48">
          <div className="text-xs text-ink-muted mb-2">选择主题</div>

          {themes.map((theme) => (
            <button
              key={theme.id}
              onClick={() => handleThemeChange(theme.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded text-sm mb-1 transition-colors text-ink-inverse ${
                currentTheme === theme.id
                  ? 'bg-accent text-ink-inverse'
                  : 'hover:bg-surface-2'
              }`}
            >
              <span>{theme.name}</span>
              {currentTheme === theme.id && <Check className="w-4 h-4" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
