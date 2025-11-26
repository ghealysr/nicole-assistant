import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Nicole V7 color palette (from master plan)
        cream: '#F5F4ED',
        lavender: '#B8A8D4',
        'lavender-text': '#9B8AB8',
        mint: '#BCD1CB',
        'mint-dark': '#7A9B93',
        beige: '#E3DACC',
        'dark-gray': '#212121',
        'light-gray': '#fafaf9',
        'text-primary': '#1d1d1f',
        'text-secondary': '#6e6e73',
        'text-tertiary': '#9e9b8f',
        'border-light': '#d8d7cc',
        'border-line': '#d1cec4',
      },
      fontFamily: {
        sans: ['-apple-system', 'SF Pro Display', 'sans-serif'],
        serif: ['Georgia', 'serif'],
      },
    },
  },
  plugins: [],
};

export default config;
