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
        className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
        title="切换主题"
      >
        <Palette className="w-4 h-4" />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-50 w-48">
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">选择主题</div>

          {themes.map((theme) => (
            <button
              key={theme.id}
              onClick={() => handleThemeChange(theme.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded text-sm mb-1 transition-colors ${
                currentTheme === theme.id
                  ? 'bg-blue-500 text-white'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-700'
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
