import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0c1116",
        bone: "#f5f0e8",
        acid: "#c6ff4a",
        coral: "#ff6f61",
        cyan: "#7de2d1",
        plum: "#7b4cff",
      },
      boxShadow: {
        panel: "0 18px 60px rgba(9, 13, 18, 0.16)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["SFMono-Regular", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
