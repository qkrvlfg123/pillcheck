"use client";

import { useState } from "react";
import Markdown from "./Markdown";

// 좌: 마크다운 입력 / 우: 실시간 미리보기 (책 9장 컨셉)
export default function MarkdownEditor({
  defaultTitle = "",
  defaultContent = "",
  submitLabel,
  action,
  cancelHref,
}: {
  defaultTitle?: string;
  defaultContent?: string;
  submitLabel: string;
  action: (formData: FormData) => void;
  cancelHref: string;
}) {
  const [content, setContent] = useState(defaultContent);

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "13px 15px", borderRadius: 10,
    border: "1px solid var(--line)", background: "var(--bg-elev)",
    color: "var(--text)", fontSize: 15,
  };

  return (
    <form action={action} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div>
        <label style={{ display: "block", marginBottom: 7, fontSize: 14, color: "var(--text-dim)" }}>제목</label>
        <input name="title" required defaultValue={defaultTitle} style={inputStyle}
          placeholder="예: 감기약과 두통약, 같이 먹어도 될까요?" />
      </div>

      <div>
        <label style={{ display: "block", marginBottom: 7, fontSize: 14, color: "var(--text-dim)" }}>
          내용 <span style={{ fontSize: 12 }}>(마크다운 지원: # 제목, **굵게**, - 목록)</span>
        </label>

        <div className="editor-split" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <textarea name="content" required rows={16} value={content}
            onChange={(e) => setContent(e.target.value)}
            style={{ ...inputStyle, lineHeight: 1.7, resize: "vertical", fontFamily: "inherit" }}
            placeholder={"쉬운 말로 건강 정보를 나눠주세요.\n\n# 제목\n**굵게**\n- 목록"} />
          <div style={{
            border: "1px solid var(--line)", borderRadius: 10, padding: "13px 16px",
            background: "var(--bg-elev)", minHeight: 200, overflow: "auto",
          }}>
            {content.trim()
              ? <Markdown>{content}</Markdown>
              : <span style={{ color: "var(--text-dim)", fontSize: 14 }}>여기에 미리보기가 나와요.</span>}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 10 }}>
        <button type="submit"
          style={{ padding: "12px 24px", borderRadius: 999, border: "none",
            background: "var(--teal)", color: "var(--bg)", fontSize: 15, fontWeight: 600, cursor: "pointer" }}>
          {submitLabel}
        </button>
        <a href={cancelHref}
          style={{ padding: "12px 24px", borderRadius: 999, border: "1px solid var(--line)",
            color: "var(--text-dim)", fontSize: 15, textDecoration: "none",
            display: "inline-flex", alignItems: "center" }}>
          취소
        </a>
      </div>

      <style>{`
        @media (max-width: 640px) {
          .editor-split { grid-template-columns: 1fr !important; }
        }
      `}</style>
    </form>
  );
}
