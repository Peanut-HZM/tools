/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        canvas: 'var(--bg-canvas)',
        surface: {
          1: 'var(--bg-surface-1)',
          2: 'var(--bg-surface-2)',
          3: 'var(--bg-surface-3)',
          overlay: 'var(--bg-overlay)',
        },
        ink: {
          DEFAULT: 'var(--ink-default)',
          muted: 'var(--ink-muted)',
          faint: 'var(--ink-faint)',
          inverse: 'var(--ink-inverse)',
        },
        accent: {
          DEFAULT: 'var(--accent-primary)',
          hover: 'var(--accent-hover)',
          press: 'var(--accent-press)',
          secondary: 'var(--accent-secondary)',
          warm: 'var(--accent-warm)',
          success: 'var(--accent-success)',
          warning: 'var(--accent-warning)',
          danger: 'var(--accent-danger)',
          info: 'var(--accent-info)',
        },
        border: {
          DEFAULT: 'var(--border-default)',
          strong: 'var(--border-strong)',
          accent: 'var(--border-accent)',
          hairline: 'var(--hairline)',
        },
        // 兼容旧色名（避免业务组件全部报错，Phase 3 再清理）
        primary: 'var(--accent-primary)',
        secondary: 'var(--accent-success)',
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