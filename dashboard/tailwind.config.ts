import type { Config } from 'tailwindcss';

export default {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        risk: {
          on: '#10b981',
          off: '#ef4444',
          transition: '#f59e0b',
        },
        signal: {
          strong: '#06b6d4',
          moderate: '#8b5cf6',
          weak: '#6b7280',
          dead: '#4b5563',
        },
      },
      typography: {
        sm: {
          css: {
            fontSize: '0.875rem',
            lineHeight: '1.25rem',
          },
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
