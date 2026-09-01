import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

export const ACCENT_PALETTES = {
  emerald: {
    id: 'emerald',
    name: 'Emerald Green',
    primary: '#10b981',
    hover: '#059669',
    subtle: '#ecfdf5',
    subtleBorder: '#a7f3d0',
    text: '#065f46',
    ring: 'rgba(16, 185, 129, 0.35)',
    gradient: 'from-emerald-600 to-teal-700',
    badge: 'bg-emerald-50 text-emerald-900 border-emerald-200',
    swatchClass: 'bg-emerald-500',
  },
  indigo: {
    id: 'indigo',
    name: 'Royal Indigo',
    primary: '#6366f1',
    hover: '#4f46e5',
    subtle: '#eef2ff',
    subtleBorder: '#c7d2fe',
    text: '#3730a3',
    ring: 'rgba(99, 102, 241, 0.35)',
    gradient: 'from-indigo-600 to-violet-700',
    badge: 'bg-indigo-50 text-indigo-900 border-indigo-200',
    swatchClass: 'bg-indigo-500',
  },
  violet: {
    id: 'violet',
    name: 'Electric Violet',
    primary: '#8b5cf6',
    hover: '#7c3aed',
    subtle: '#f5f3ff',
    subtleBorder: '#ddd6fe',
    text: '#5b21b6',
    ring: 'rgba(139, 92, 246, 0.35)',
    gradient: 'from-violet-600 to-purple-700',
    badge: 'bg-violet-50 text-violet-900 border-violet-200',
    swatchClass: 'bg-violet-500',
  },
  amber: {
    id: 'amber',
    name: 'Solar Amber',
    primary: '#f59e0b',
    hover: '#d97706',
    subtle: '#fffbeb',
    subtleBorder: '#fde68a',
    text: '#92400e',
    ring: 'rgba(245, 158, 11, 0.35)',
    gradient: 'from-amber-500 to-orange-600',
    badge: 'bg-amber-50 text-amber-900 border-amber-200',
    swatchClass: 'bg-amber-500',
  },
  teal: {
    id: 'teal',
    name: 'Nordic Teal',
    primary: '#14b8a6',
    hover: '#0d9488',
    subtle: '#f0fdfa',
    subtleBorder: '#99f6e4',
    text: '#115e59',
    ring: 'rgba(20, 184, 166, 0.35)',
    gradient: 'from-teal-600 to-emerald-700',
    badge: 'bg-teal-50 text-teal-900 border-teal-200',
    swatchClass: 'bg-teal-500',
  },
  rose: {
    id: 'rose',
    name: 'Crimson Rose',
    primary: '#f43f5e',
    hover: '#e11d48',
    subtle: '#fff1f2',
    subtleBorder: '#fecdd3',
    text: '#9f1239',
    ring: 'rgba(244, 63, 94, 0.35)',
    gradient: 'from-rose-600 to-pink-700',
    badge: 'bg-rose-50 text-rose-900 border-rose-200',
    swatchClass: 'bg-rose-500',
  },
  slate: {
    id: 'slate',
    name: 'Mild Slate & Steel',
    primary: '#334155',
    hover: '#1e293b',
    subtle: '#f1f5f9',
    subtleBorder: '#cbd5e1',
    text: '#1e293b',
    ring: 'rgba(51, 65, 85, 0.35)',
    gradient: 'from-slate-700 to-slate-900',
    badge: 'bg-slate-100 text-slate-800 border-slate-200',
    swatchClass: 'bg-slate-700',
  },
  zinc: {
    id: 'zinc',
    name: 'Mild Graphite',
    primary: '#3f3f46',
    hover: '#27272a',
    subtle: '#f4f4f5',
    subtleBorder: '#e4e4e7',
    text: '#27272a',
    ring: 'rgba(63, 63, 70, 0.35)',
    gradient: 'from-zinc-700 to-zinc-800',
    badge: 'bg-zinc-100 text-zinc-800 border-zinc-200',
    swatchClass: 'bg-zinc-700',
  },
};

const ThemeContext = createContext({
  accentColor: 'emerald',
  accent: ACCENT_PALETTES.emerald,
  setAccentColor: () => {},
  themeMode: 'light',
  setThemeMode: () => {},
  density: 'comfortable',
  setDensity: () => {},
  availablePalettes: ACCENT_PALETTES,
});

const STORAGE_KEY = 'caltrack_workforce_theme_preferences';

export function ThemeProvider({ children }) {
  const [accentColor, setAccentColorState] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        const col = parsed.accentColor === 'blue' ? 'indigo' : parsed.accentColor;
        if (col && ACCENT_PALETTES[col]) {
          return col;
        }
      }
    } catch (_) {}
    return 'emerald';
  });

  const [themeMode, setThemeModeState] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.themeMode) return parsed.themeMode;
      }
    } catch (_) {}
    return 'light';
  });

  const [density, setDensityState] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.density) return parsed.density;
      }
    } catch (_) {}
    return 'comfortable';
  });

  const activePalette = ACCENT_PALETTES[accentColor === 'blue' ? 'indigo' : accentColor] || ACCENT_PALETTES.emerald;

  // Apply CSS variables dynamically to the document root
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--accent-primary', activePalette.primary);
    root.style.setProperty('--accent-hover', activePalette.hover);
    root.style.setProperty('--accent-subtle', activePalette.subtle);
    root.style.setProperty('--accent-subtle-border', activePalette.subtleBorder);
    root.style.setProperty('--accent-text', activePalette.text);
    root.style.setProperty('--accent-ring', activePalette.ring);
    root.setAttribute('data-accent', accentColor);
    root.setAttribute('data-density', density);

    // Save to localStorage
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          accentColor,
          themeMode,
          density,
        })
      );
    } catch (_) {}
  }, [accentColor, themeMode, density, activePalette]);

  const setAccentColor = useCallback((colorKey) => {
    const key = colorKey === 'blue' ? 'indigo' : colorKey;
    if (ACCENT_PALETTES[key]) {
      setAccentColorState(key);
    }
  }, []);

  const setThemeMode = useCallback((mode) => {
    setThemeModeState(mode);
  }, []);

  const setDensity = useCallback((d) => {
    setDensityState(d);
  }, []);

  return (
    <ThemeContext.Provider
      value={{
        accentColor,
        accent: activePalette,
        setAccentColor,
        themeMode,
        setThemeMode,
        density,
        setDensity,
        availablePalettes: ACCENT_PALETTES,
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return ctx;
}
