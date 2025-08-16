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
          dark: '#39594f',
          light: '#e8e6de',
          border: '#e0e0e1',
          background: '#fafafa',
        },
        wikipedia: {
          label: '#d28fe3',
        },
        user: {
          message: '#39594d',
        },
        brand: {
          base: '#ff7859',
          hover: '#ff7859',
        },
        accent: '#d28fe3',
        ink: '#000000',
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Noto Sans',
          'Ubuntu',
          'Cantarell',
          'Helvetica Neue',
          'Arial',
          'sans-serif'
        ]
      }
    },
  },
  plugins: [],
}
