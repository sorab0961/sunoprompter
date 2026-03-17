/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        night: "#0f172a",
        accent: "#7dd3fc",
        card: "#111827",
      },
    },
  },
  plugins: [],
};
