/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Claude Code Cowork-inspired dark palette
        bg: {
          primary: '#0d0d0d',
          secondary: '#141414',
          tertiary: '#1a1a1a',
          elevated: '#1f1f1f',
          hover: '#262626',
        },
        border: {
          subtle: '#262626',
          DEFAULT: '#333333',
          strong: '#404040',
        },
        text: {
          primary: '#f5f5f5',
          secondary: '#a3a3a3',
          tertiary: '#737373',
          muted: '#525252',
        },
        accent: {
          blue: '#3b82f6',
          green: '#22c55e',
          yellow: '#eab308',
          red: '#ef4444',
          purple: '#a855f7',
          orange: '#f97316',
        },
        status: {
          running: '#3b82f6',
          success: '#22c55e',
          warning: '#eab308',
          error: '#ef4444',
          pending: '#737373',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '0.875rem' }],
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      },
      borderRadius: {
        'sm': '4px',
        'md': '6px',
        'lg': '8px',
        'xl': '12px',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.2s ease-out',
        'scale-in': 'scaleIn 0.15s ease-out',
        'stagger-in': 'staggerIn 0.3s ease-out forwards',
        'status-pulse': 'statusPulse 2s ease-in-out infinite',
        'shake': 'shake 0.4s ease-in-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { transform: 'scale(0.95)', opacity: '0' },
          '100%': { transform: 'scale(1)', opacity: '1' },
        },
        staggerIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        statusPulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '25%': { transform: 'translateX(-4px)' },
          '75%': { transform: 'translateX(4px)' },
        },
      },
      boxShadow: {
        'elevated-sm': '0 2px 8px rgba(0, 0, 0, 0.3)',
        'elevated-md': '0 4px 16px rgba(0, 0, 0, 0.4)',
        'elevated-lg': '0 8px 32px rgba(0, 0, 0, 0.5)',
        'glow-blue': '0 0 20px rgba(59, 130, 246, 0.3)',
        'glow-green': '0 0 20px rgba(34, 197, 94, 0.25)',
        'glow-accent': '0 0 20px rgba(217, 119, 87, 0.3)',
      },
    },
  },
  plugins: [],
}
