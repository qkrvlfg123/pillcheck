"use client";

import { useState } from "react";

// 랜딩용 데모. 실제 판정은 10번 챗봇 + 식약처 DUR이 담당.
// 일상어(감기약·두통약)로 보여주고, 누르면 제품명 예시까지 펼쳐진다.
type Demo = {
  label: string;      // 버튼에 보이는 일상어
  drugs: string[];    // 각 약의 "종류 (제품명 예시)"
  level: string;      // 위험도
  text: string;       // 안내
};

const DEMOS: Demo[] = [
  {
    label: "목감기약 + 두통약",
    drugs: ["목감기약 (판피린·판콜 등)", "두통약 (타이레놀·게보린 등)"],
    level: "위험",
    text: "감기약과 두통약에 같은 성분(아세트아미노펜)이 겹치는 경우가 많아요. 겹쳐 드시면 하루 최대량을 넘겨 간에 무리가 갈 수 있어요.",
  },
  {
    label: "우울증약 + 편두통약",
    drugs: ["우울증약 (렉사프로·졸로푸트 등)", "편두통약 (이미그란 등)"],
    level: "위험",
    text: "두 약 모두 세로토닌을 높여, 함께 쓰면 드물게 위험한 반응(세로토닌증후군)이 생길 수 있어요. 반드시 의사와 상의하세요.",
  },
  {
    label: "수면제 + 신경안정제",
    drugs: ["수면제 (스틸녹스 등)", "신경안정제 (자낙스 등)"],
    level: "위험",
    text: "함께 드시면 지나치게 처지거나 호흡이 약해질 수 있어요. 같이 복용하는 건 피하는 게 좋아요.",
  },
];

export default function DrugDemo() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div className="rounded-2xl border border-teal/20 bg-white p-6 shadow-sm sm:p-8">
      <p className="mb-4 text-base font-medium text-teal-deep">
        예시로 눌러보세요 — 함께 먹는 약을 고르면
      </p>
      <div className="flex flex-wrap gap-3">
        {DEMOS.map((demo, i) => (
          <button
            key={demo.label}
            onClick={() => setOpenIndex(openIndex === i ? null : i)}
            className={`rounded-full border px-5 py-3 text-base transition ${
              openIndex === i
                ? "border-teal bg-teal text-white"
                : "border-teal/30 bg-teal-soft text-teal-deep hover:border-teal"
            }`}
          >
            {demo.label}
          </button>
        ))}
      </div>

      <div className="mt-6 min-h-[140px] rounded-xl bg-cream p-6">
        {openIndex === null ? (
          <p className="text-base text-ink/50">
            위에서 약 조합을 선택하면, 어떤 약들인지와 함께 안내가 나와요.
          </p>
        ) : (
          <div className="rise">
            {/* 어떤 약들인지 (제품명 예시) */}
            <div className="mb-4 flex flex-wrap gap-2">
              {DEMOS[openIndex].drugs.map((d) => (
                <span
                  key={d}
                  className="rounded-lg bg-teal-soft px-3 py-1.5 text-sm text-teal-deep"
                >
                  {d}
                </span>
              ))}
            </div>
            {/* 위험도 + 안내 */}
            <span className="inline-block rounded-full bg-coral px-3 py-1 text-sm font-medium text-white">
              {DEMOS[openIndex].level}
            </span>
            <p className="mt-3 text-lg leading-relaxed text-ink">
              {DEMOS[openIndex].text}
            </p>
          </div>
        )}
      </div>

      <p className="mt-4 text-sm text-ink/50">
        * 미리보기입니다. 실제 서비스는 약 이름(제품명)이나 종류로 물어보면 식약처
        공식 데이터(DUR)로 확인해요. 참고용이며 최종 판단은 의사·약사가 합니다.
      </p>
    </div>
  );
}
