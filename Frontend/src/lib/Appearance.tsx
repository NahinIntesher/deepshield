'use client';

import {createContext, useContext, useEffect, useState} from 'react';

export type Appearance = 'light' | 'dark';
const Context = createContext<{theme: Appearance; setTheme: (value: Appearance) => void}>({theme: 'light', setTheme: () => {}});

export function AppearanceProvider({children}: {children: React.ReactNode}) {
  const [theme, updateTheme] = useState<Appearance>('light');
  useEffect(() => {
    const saved = localStorage.getItem('deepshield-theme');
    if (saved === 'light' || saved === 'dark') updateTheme(saved);
    else if (saved === 'auto') {
      const migrated = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      localStorage.setItem('deepshield-theme', migrated);
      updateTheme(migrated);
    }
  }, []);
  useEffect(() => {
    const apply = () => {
      document.documentElement.classList.toggle('dark', theme === 'dark');
      document.documentElement.dataset.appearance = theme;
    };
    apply();
  }, [theme]);
  function setTheme(value: Appearance) {
    localStorage.setItem('deepshield-theme', value);
    updateTheme(value);
  }
  return <Context.Provider value={{theme, setTheme}}>{children}</Context.Provider>;
}

export const useAppearance = () => useContext(Context);
