/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#050505",
        panel: "#0c0c0c",
        raised: "#161616",
        line: "#262626",
        "line-strong": "#3d3d3d",
        ink: "#f7f7f2",
        muted: "#b5b5ae",
        faint: "#92928b",
        accent: "#ffd400",
        "accent-strong": "#ffe14d",
        "accent-dim": "#332b00",
        actual: "#c9c9c2",
        danger: "#ff6b6b",
        warn: "#fb923c",
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Consolas", "Liberation Mono", "monospace"],
      },
      keyframes: {
        shimmer: {
          "0%": { opacity: "0.45" },
          "50%": { opacity: "0.8" },
          "100%": { opacity: "0.45" },
        },
      },
      animation: {
        shimmer: "shimmer 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
