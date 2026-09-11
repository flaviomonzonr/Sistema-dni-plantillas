/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        chavin: {
          primary: '#101BCB',
          dark: '#080F72',
          green: '#A8E63D',
          bg: '#F4F7FB',
          surface: '#FFFFFF',
          text: '#1E293B',
          muted: '#64748B',
          border: '#E2E8F0',
          hover: '#080F72',
        },
        slate: {
          50: '#F8FAFC',
          100: '#F1F5F9',
          200: '#E2E8F0',
          300: '#CBD5E1',
          400: '#94A3B8',
          500: '#64748B',
          600: '#475569',
          700: '#334155',
          800: '#1E293B',
          900: '#0F172A',
          950: '#020617',
        }
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
        'card-hover': '0 10px 25px -5px rgba(8, 15, 114, 0.08), 0 8px 10px -6px rgba(8, 15, 114, 0.04)',
        'sidebar': '4px 0 20px rgba(8, 15, 114, 0.15)',
        'glow-green': '0 0 15px rgba(168, 230, 61, 0.35)',
        'glow-blue': '0 0 15px rgba(16, 27, 203, 0.3)',
      }
    },
  },
  plugins: [],
}
