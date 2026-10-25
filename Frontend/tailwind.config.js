/** @type {import('tailwindcss').Config} */
const accentScale = {50:'#effaf3',100:'#dbf3e4',200:'#b9e5cb',300:'#88d1aa',400:'#51b583',500:'#2e9666',600:'#21784f',700:'#195f40',800:'#174c35',900:'#123e2c',950:'#08271b'};

module.exports = {
  darkMode: 'class',
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-quicksand)', 'sans-serif'],
        mono: ['var(--font-quicksand)', 'sans-serif'],
      },
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        brand: accentScale,
        deepfake: {
          real: "#185c3d",
          fake: "#b54436",
          warning: "#f28a43",
          info: "#185c3d"
        }
      },
      boxShadow: {
        'glass': '0 4px 20px -2px rgba(15, 23, 42, 0.05), 0 2px 6px -1px rgba(15, 23, 42, 0.02)',
        'glass-hover': '0 12px 30px -4px rgba(37, 99, 235, 0.08), 0 4px 10px -2px rgba(15, 23, 42, 0.03)',
        'glass-elevated': '0 20px 40px -6px rgba(15, 23, 42, 0.08), 0 8px 16px -4px rgba(15, 23, 42, 0.03)',
      }
    },
  },
  plugins: [],
};
