/**
 * 主题切换组件
 */
import { useState, useEffect } from 'react';
import { Palette } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from '@/components/ui/DropdownMenu';
import { themes, applyTheme, getSavedTheme, saveTheme } from '../../../themes/cursorThemes';

export default function ThemeSwitcher() {
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
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="p-2 hover:bg-surface-2 rounded transition-colors text-ink-muted hover:text-ink-inverse outline-none"
        title="切换主题"
        aria-label="切换主题"
      >
        <Palette className="w-4 h-4" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuLabel className="text-xs text-ink-muted">选择主题</DropdownMenuLabel>
        <DropdownMenuRadioGroup value={currentTheme} onValueChange={handleThemeChange}>
          {themes.map((theme) => (
            <DropdownMenuRadioItem key={theme.id} value={theme.id}>
              {theme.name}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
