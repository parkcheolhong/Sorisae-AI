'use client';

import { useEffect, useState } from 'react';

type ThemeMode = 'light' | 'dark';

function applyTheme(theme: ThemeMode) {
  document.documentElement.dataset.theme = theme;
  window.localStorage.setItem('ops-theme', theme);
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<ThemeMode>('light');

  useEffect(() => {
    const stored = window.localStorage.getItem('ops-theme');
    const resolved = stored === 'dark' ? 'dark' : 'light';
    setTheme(resolved);
    applyTheme(resolved);
  }, []);

  const updateTheme = (nextTheme: ThemeMode) => {
    setTheme(nextTheme);
    applyTheme(nextTheme);
  };

  return (
    <div className="themeToggle">
      <button type="button" className={theme === 'light' ? 'themeChip is-active' : 'themeChip'} onClick={() => updateTheme('light')}>Light</button>
      <button type="button" className={theme === 'dark' ? 'themeChip is-active' : 'themeChip'} onClick={() => updateTheme('dark')}>Dark</button>
    </div>
  );
}
