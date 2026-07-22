/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ink: 'rgb(var(--c-ink) / <alpha-value>)',
        paper: 'rgb(var(--c-paper) / <alpha-value>)',
        surface: 'rgb(var(--c-surface) / <alpha-value>)',
        'surface-2': 'rgb(var(--c-surface-2) / <alpha-value>)',
        edge: 'rgb(var(--c-edge) / <alpha-value>)',
        'edge-strong': 'rgb(var(--c-edge-strong) / <alpha-value>)',
        muted: 'rgb(var(--c-muted) / <alpha-value>)',
        allow: 'rgb(var(--c-allow) / <alpha-value>)',
        deny: 'rgb(var(--c-deny) / <alpha-value>)',
        pending: 'rgb(var(--c-pending) / <alpha-value>)',
        accent: 'rgb(var(--c-accent) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"SF Mono"', 'Menlo', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      borderRadius: {
        xs: '2px',
        sm: '4px',
        md: '6px',
        lg: '8px',
      },
      boxShadow: {
        'panel': '0 1px 0 0 rgb(var(--c-edge) / 0.6), 0 1px 3px 0 rgb(0 0 0 / 0.08)',
        'panel-raised': '0 1px 0 0 rgb(var(--c-edge) / 0.8), 0 4px 12px 0 rgb(0 0 0 / 0.12)',
        'focus': '0 0 0 2px rgb(var(--c-bg) / 1), 0 0 0 4px rgb(var(--c-accent) / 0.7)',
      },
      transitionTimingFunction: {
        'decisive': 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
};
