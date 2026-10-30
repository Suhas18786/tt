/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { 50: "#eef1ff", 100: "#dfe5ff", 200: "#c2ccff", 500: "#4257e6", 600: "#3043d1", 700: "#2535ae", 800: "#1f2c8a", 900: "#151d5e", 950: "#0d1240" },
        paper: "#f6f7fb",
      },
      fontFamily: {
        sans: ["Figtree", "ui-sans-serif", "system-ui", "Segoe UI", "Roboto", "sans-serif"],
        display: ["Bricolage Grotesque", "Figtree", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: { card: "0 1px 2px rgba(16,24,40,.05), 0 1px 3px rgba(16,24,40,.04)", pop: "0 12px 32px -8px rgba(21,29,94,.25)" },
    },
  },
  plugins: [],
};
