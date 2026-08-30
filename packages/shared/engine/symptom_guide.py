"""
필체크 — 증상 안내 & 임부/수유부 주의 엔진
==========================================

- 증상(두통·소화불량 등)을 입력하면 흔히 쓰는 약 '계열'과 주의점을 안내한다.
- 임부/수유부면 특별 주의를 함께 안내한다.

원칙:
  - 특정 제품을 '먹어라'가 아니라 계열·주의점 안내(진단·처방 아님).
  - 증상이 심하거나 지속되면 병원 진료를 권한다.
  - 임부/수유부/소아/고령자는 반드시 전문가 상담. 임부금기는 DUR이 공식 근거.
"""

import json
import os

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "..", "data")


def _load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


GUIDE = _load("symptom_pregnancy_guide.json")
SYMPTOMS = GUIDE["symptom_guide"]
PREGNANCY = GUIDE["pregnancy_caution"]


def guide_symptom(symptom_query, pregnant=False):
    """증상 문자열로 안내를 찾는다. 부분 매칭."""
    q = symptom_query.strip()
    matched = []
    for s in SYMPTOMS:
        if q in s["symptom"] or s["symptom"] in q or any(q in c for c in s["common_classes"]):
            matched.append(s)
    return {"query": q, "matches": matched, "pregnant": pregnant}


def format_symptom(result):
    L = ["=" * 62, "필체크 — 증상별 약 안내 (참고용)", "=" * 62]
    if not result["matches"]:
        L.append(f"\n'{result['query']}'에 대한 안내를 찾지 못했어요. 약사와 상담해 주세요.")
    for s in result["matches"]:
        L.append(f"\n[{s['symptom']}]")
        L.append(f"  흔히 쓰는 계열: {', '.join(s['common_classes'])}")
        L.append(f"  안내: {s['note']}")
        if s.get("caution_groups"):
            L.append(f"  주의 대상: {', '.join(s['caution_groups'])}")
        L.append(f"  병원에 가야 할 때: {s['see_doctor']}")

    if result["pregnant"]:
        L.append("\n" + "=" * 62)
        L.append("[임부·수유부 특별 주의]")
        L.append(f"  {PREGNANCY['설명']}")
        L.append("  자가복용을 피해야 할 것:")
        for a in PREGNANCY["generally_avoid_self_med"]:
            L.append(f"    · {a}")
        L.append("  비교적 널리 쓰이나 상담 필요:")
        for a in PREGNANCY["relatively_preferred"]:
            L.append(f"    · {a}")
        L.append(f"  ★ {PREGNANCY['always']}")

    L.append("\n" + "-" * 62)
    L.append("※ 진단·처방이 아니라 일반 정보 참고입니다.")
    L.append("※ 증상이 심하거나 지속되면 자가약 대신 진료를 받으세요.")
    L.append("※ 임부·수유부·소아·고령자는 복용 전 반드시 약사·의사와 상담하세요.")
    return "\n".join(L)


if __name__ == "__main__":
    print(format_symptom(guide_symptom("두통", pregnant=True)))
    print("\n\n")
    print(format_symptom(guide_symptom("소화불량")))
