import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#12312e",       // 딥 틸 (본문/제목)
        teal: {
          DEFAULT: "#0f6e56", // 신뢰의 청록
          soft: "#e1f5ee",
          deep: "#085041",
        },
        cream: "#f7f4ec",      // 따뜻한 배경
        amber: "#ba7517",      // 경고
        coral: "#d85a30",      // 위험
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      fontSize: {
        // 고령자 배려: 기본 크기를 키움
        base: ["1.125rem", { lineHeight: "1.7" }],
        lg: ["1.25rem", { lineHeight: "1.7" }],
      },
    },
  },
  plugins: [],
};
export default config;
