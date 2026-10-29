/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { 50: "#eef4fb", 100: "#d9e6f5", 200: "#b6cfec", 500: "#2f6bb3", 600: "#235a9c", 700: "#1c4a82", 800: "#173c68", 900: "#12304f", 950: "#0c2038" },
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "sans-serif"] },
    },
  },
  plugins: [],
};
