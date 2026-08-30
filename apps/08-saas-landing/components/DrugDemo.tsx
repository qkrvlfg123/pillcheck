"use client";

import { useState } from "react";

// 랜딩용 데모. 실제 판정은 10번 챗봇 + 식약처 DUR이 담당.
// 여기서는 "이런 걸 할 수 있어요"를 보여주는 미리보기.
const DEMO: Record<string, { level: string; text: string }> = {
  "와파린+부루펜": {
    level: "위험",
    text: "함께 드시면 위장 출혈 위험이 높아져요. 진통이 필요하면 약사와 상의하세요.",
  },
  "렉사프로+이미그란": {
    level: "위험",
    text: "우울약과 편두통약을 함께 쓰면 드물게 위험한 반응이 생길 수 있어요. 의사와 상의하세요.",
  },
  "자낙스+졸피뎀": {
    level: "위험",
    text: "신경안정제와 수면제를 같이 드시면 지나치게 처질 수 있어 함께 복용은 피하세요.",
  },
};

const EXAMPLES = ["와파린 + 부루펜", "렉사프로 + 이미그란", "자낙스 + 졸피뎀"];

export default function DrugDemo() {
  const [selected, setSelected] = useState<string | null>(null);

  const key = selected?.replace(/\s/g, "");
  const result = key ? DEMO[key] : null;

  return (
    <div className="rounded-2xl border border-teal/20 bg-white p-6 shadow-sm sm:p-8">
      <p className="mb-4 text-base font-medium text-teal-deep">
        예시로 눌러보세요 — 함께 먹는 약을 고르면
      </p>
      <div className="flex flex-wrap gap-3">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => setSelected(ex)}
            className={`rounded-full border px-5 py-3 text-base transition ${
              selected === ex
                ? "border-teal bg-teal text-white"
                : "border-teal/30 bg-teal-soft text-teal-deep hover:border-teal"
            }`}
          >
            {ex}
          </button>
        ))}
      </div>

      <div className="mt-6 min-h-[120px] rounded-xl bg-cream p-6">
        {!result ? (
          <p className="text-base text-ink/50">
            위에서 약 조합을 선택하면 여기에 안내가 나와요.
          </p>
        ) : (
          <div className="rise">
            <span className="inline-block rounded-full bg-coral px-3 py-1 text-sm font-medium text-white">
              {result.level}
            </span>
            <p className="mt-3 text-lg leading-relaxed text-ink">{result.text}</p>
          </div>
        )}
      </div>

      <p className="mt-4 text-sm text-ink/50">
        * 미리보기입니다. 실제 서비스는 식약처 공식 데이터(DUR)로 확인하며, 참고용이고
        최종 판단은 의사·약사가 합니다.
      </p>
    </div>
  );
}
