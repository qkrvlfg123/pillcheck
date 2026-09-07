import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// 마크다운을 렌더링하는 공용 컴포넌트 (다크/라이트 테마 변수 사용)
export default function Markdown({ children }: { children: string }) {
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
      <style>{`
        .md { font-size: 1.05rem; line-height: 1.85; color: var(--text); }
        .md h1 { font-size: 1.7rem; font-weight: 800; margin: 1.4em 0 0.5em; letter-spacing: -0.02em; }
        .md h2 { font-size: 1.4rem; font-weight: 700; margin: 1.3em 0 0.5em; letter-spacing: -0.02em; }
        .md h3 { font-size: 1.2rem; font-weight: 700; margin: 1.2em 0 0.4em; }
        .md p { margin: 0 0 1.1em; }
        .md a { color: var(--teal); text-decoration: underline; }
        .md ul, .md ol { margin: 0 0 1.1em; padding-left: 1.4em; }
        .md li { margin: 0.3em 0; }
        .md blockquote {
          border-left: 3px solid var(--teal);
          margin: 1.2em 0; padding: 0.2em 1em;
          color: var(--text-dim); background: var(--bg-elev); border-radius: 6px;
        }
        .md code {
          background: var(--bg-elev); padding: 0.15em 0.4em;
          border-radius: 5px; font-size: 0.9em;
        }
        .md pre {
          background: var(--bg-elev); padding: 14px 16px; border-radius: 10px;
          overflow-x: auto; border: 1px solid var(--line);
        }
        .md pre code { background: transparent; padding: 0; }
        .md hr { border: none; border-top: 1px solid var(--line); margin: 1.6em 0; }
        .md table { border-collapse: collapse; width: 100%; margin: 1.2em 0; }
        .md th, .md td { border: 1px solid var(--line); padding: 8px 12px; text-align: left; }
        .md th { background: var(--bg-elev); }
        .md strong { font-weight: 700; }
        .md img { max-width: 100%; border-radius: 10px; }
      `}</style>
    </div>
  );
}
