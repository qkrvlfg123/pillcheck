import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#12312e",
        teal: { DEFAULT: "#0f6e56", soft: "#e1f5ee", deep: "#085041" },
        cream: "#f7f4ec",
        amber: "#ba7517",
      },
      fontSize: { base: ["1.0625rem", { lineHeight: "1.75" }] },
    },
  },
  plugins: [],
};
export default config;
