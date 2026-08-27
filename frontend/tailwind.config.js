/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  safelist: [
    // iconColor classes from backend/app/data/tools_data.py
    // Tailwind JIT only scans frontend/src — these backend-defined classes
    // must be safelisted or they won't generate CSS rules
    'bg-blue-500', 'bg-blue-600', 'bg-violet-500', 'bg-emerald-500',
    'bg-indigo-500', 'bg-orange-500', 'bg-red-600', 'bg-purple-500',
  ],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        canvas: 'rgb(var(--bg-canvas) / <alpha-value>)',
        surface: {
          1: 'rgb(var(--bg-surface-1) / <alpha-value>)',
          2: 'rgb(var(--bg-surface-2) / <alpha-value>)',
          3: 'rgb(var(--bg-surface-3) / <alpha-value>)',
          overlay: 'var(--bg-overlay)',  // rgba 值，不能用 rgb() 包裹
        },
        ink: {
          DEFAULT: 'rgb(var(--ink-default) / <alpha-value>)',
          muted: 'rgb(var(--ink-muted) / <alpha-value>)',
          faint: 'rgb(var(--ink-faint) / <alpha-value>)',
          inverse: 'rgb(var(--ink-inverse) / <alpha-value>)',
        },
        accent: {
          DEFAULT: 'rgb(var(--accent-primary) / <alpha-value>)',
          hover: 'rgb(var(--accent-hover) / <alpha-value>)',
          press: 'rgb(var(--accent-press) / <alpha-value>)',
          secondary: 'rgb(var(--accent-secondary) / <alpha-value>)',
          warm: 'rgb(var(--accent-warm) / <alpha-value>)',
          cyan: 'rgb(var(--accent-cyan) / <alpha-value>)',
          success: 'rgb(var(--accent-success) / <alpha-value>)',
          warning: 'rgb(var(--accent-warning) / <alpha-value>)',
          danger: 'rgb(var(--accent-danger) / <alpha-value>)',
          info: 'rgb(var(--accent-info) / <alpha-value>)',
        },
        border: {
          DEFAULT: 'rgb(var(--border-default) / <alpha-value>)',
          strong: 'rgb(var(--border-strong) / <alpha-value>)',
          accent: 'var(--border-accent)',  // rgba 值，不能用 rgb() 包裹
          hairline: 'var(--hairline)',      // rgba 值，不能用 rgb() 包裹
        },
        // 兼容旧色名（避免业务组件全部报错，Phase 3 再清理）
        primary: 'rgb(var(--accent-primary) / <alpha-value>)',
        secondary: 'rgb(var(--accent-secondary) / <alpha-value>)',
        // 顶层语义别名：让 text-danger / bg-warning / border-success 等 shorthand 生效
        danger: 'rgb(var(--accent-danger) / <alpha-value>)',
        warning: 'rgb(var(--accent-warning) / <alpha-value>)',
        success: 'rgb(var(--accent-success) / <alpha-value>)',
        info: 'rgb(var(--accent-info) / <alpha-value>)',
      },
      fontFamily: {
        sans:  ['var(--font-sans)'],
        mono:  ['var(--font-mono)'],
        serif: ['var(--font-serif)'],
      },
      fontSize: {
        'display-2xl': ['var(--text-display-2xl)', { lineHeight: 'var(--leading-tight)' }],
        'display-xl':  ['var(--text-display-xl)',  { lineHeight: 'var(--leading-tight)' }],
        'display-lg':  ['var(--text-display-lg)',  { lineHeight: 'var(--leading-tight)' }],
        'display-md':  ['var(--text-display-md)',  { lineHeight: 'var(--leading-snug)' }],
        'display-sm':  ['var(--text-display-sm)',  { lineHeight: 'var(--leading-snug)' }],
        'heading-lg':  ['var(--text-heading-lg)',  { lineHeight: 'var(--leading-snug)' }],
        'heading-md':  ['var(--text-heading-md)',  { lineHeight: 'var(--leading-snug)' }],
        'heading-sm':  ['var(--text-heading-sm)',  { lineHeight: 'var(--leading-normal)' }],
        'body-lg':     ['var(--text-body-lg)',     { lineHeight: 'var(--leading-normal)' }],
        'body-md':     ['var(--text-body-md)',     { lineHeight: 'var(--leading-normal)' }],
        'body-sm':     ['var(--text-body-sm)',     { lineHeight: 'var(--leading-normal)' }],
        'caption':     ['var(--text-caption)',     { lineHeight: 'var(--leading-normal)' }],
      },
      borderRadius: {
        sm:   'var(--radius-sm)',
        md:   'var(--radius-md)',
        lg:   'var(--radius-lg)',
        xl:   'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
        pill: 'var(--radius-pill)',
      },
      boxShadow: {
        sm:    'var(--shadow-sm)',
        md:    'var(--shadow-md)',
        lg:    'var(--shadow-lg)',
        xl:    'var(--shadow-xl)',
        glow:  'var(--shadow-glow)',
        focus: 'var(--shadow-focus)',
      },
      transitionTimingFunction: {
        stripe: 'var(--ease-stripe)',
        bounce: 'var(--ease-bounce)',
        'in-out': 'var(--ease-in-out)',
        out: 'var(--ease-out)',
      },
      transitionDuration: {
        fast:   'var(--duration-fast)',
        normal: 'var(--duration-normal)',
        slow:   'var(--duration-slow)',
        slower: 'var(--duration-slower)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('tailwindcss-animate'),
  ],
};
