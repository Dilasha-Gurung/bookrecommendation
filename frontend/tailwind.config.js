/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1C2A27",        // near-black green-ink text
        paper: "#FAF7F0",      // warm off-white page background
        forest: "#1F3A34",     // deep forest green (primary)
        forestlight: "#2E534B",
        gold: "#C89B4C",       // muted gold accent (spines / CTAs)
        goldsoft: "#E7D6AE",
        rule: "#DFD9C8",       // hairline rule / border color
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        body: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
