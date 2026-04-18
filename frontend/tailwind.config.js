/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0f14",
        panel: "#121821",
        panel2: "#1a2330",
        ink: "#e6edf3",
        muted: "#8b96a5",
        accent: "#6ee7b7",
        danger: "#fb7185",
        warn: "#fbbf24",
      },
    },
  },
  plugins: [],
};
