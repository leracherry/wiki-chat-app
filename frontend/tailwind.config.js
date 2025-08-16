/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cohere: {
          dark: '#39594d',
          light: '#e9e6de',
          border: '#e0e0e1',
          background: '#fafafb',
        },
        wikipedia: {
          label: '#d18ee2',
        },
        user: {
          message: '#39594d',
        },
        brand: {
          base: '#39594d',
          hover: '#ff7859',
        }
      }
    },
  },
  plugins: [],
}

