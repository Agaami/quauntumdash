/** @type {import('tailwindcss').Config} */
import defaultTheme from 'tailwindcss/defaultTheme';

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', ...defaultTheme.fontFamily.sans],
      },
      // New "Frosted Glass" Light Mode Palette
      colors: {
        'light-bg': '#f7f7f8', // Very light neutral background
        'primary': '#007aff',  // Apple blue
        'text-dark': '#1c1c1e', // Near-black for main text
        'text-light': '#6b6b6e', // Gray for subtext
        'border-light': 'rgba(0, 0, 0, 0.1)', // Subtle border
        
        // This is our new "frosted glass" color
        'glass-bg': 'rgba(255, 255, 255, 0.7)',
      }
    },
  },
  plugins: [],
}