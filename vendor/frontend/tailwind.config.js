/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Monochromatic Zinc Foundation (shadcn / Radix inspired)
        zinc: {
          50: '#fafafa',
          100: '#f4f4f5',
          200: '#e4e4e7',
          300: '#d4d4d8',
          400: '#a1a1aa',
          500: '#71717a',
          600: '#52525b',
          700: '#3f3f46',
          800: '#27272a',
          900: '#18181b',
          950: '#09090b',
        },
        // Mild Slate & Steel Palette (Soft, elegant alternative to pitch black)
        mild: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#090d16',
        },
        // Semantic, refined status indicators
        status: {
          emerald: '#10b981',
          amber: '#f59e0b',
          rose: '#f43f5e',
          slate: '#64748b',
        },
        // Brand Primary (Soft Deep Slate / Steel Charcoal)
        brand: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#090d16',
          accent: '#334155',
        },
        // Enterprise UI Surfaces
        enterprise: {
          header: '#1e293b',
          headerHover: '#334155',
          sidebar: '#ffffff',
          sidebarBg: '#f8fafc',
          sidebarBorder: '#e2e8f0',
          workspace: '#f1f5f9',
          card: '#ffffff',
          border: '#e2e8f0',
          borderSubtle: '#f8fafc',
          textPrimary: '#0f172a',
          textSecondary: '#475569',
          textMuted: '#64748b',
          accent: '#334155',
        }
      },
      borderRadius: {
        'outside': '0px',
        'outside-xs': '2px',
        'mid': '0.5rem',     // 8px medium-sharp
        'mid-sm': '0.375rem', // 6px
        'inside': '0.75rem',  // 12px soft
        'inside-sm': '0.5rem', // 8px
        'inside-pill': '9999px',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      boxShadow: {
        'xs': '0 1px 2px 0 rgba(0, 0, 0, 0.04)',
        'subtle': '0 1px 3px 0 rgba(0, 0, 0, 0.04), 0 1px 2px -1px rgba(0, 0, 0, 0.04)',
        'bento': '0 2px 8px -2px rgba(0, 0, 0, 0.05), 0 1px 4px -1px rgba(0, 0, 0, 0.03)',
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
        'popover': '0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.05)',
        'modal': '0 25px 50px -12px rgba(0, 0, 0, 0.15)',
      },
    },
  },
  plugins: [],
}

