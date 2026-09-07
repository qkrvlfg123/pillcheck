"""
근거 검증 + 근거 장부 생성 도구
================================

(1) verify(): 모든 규칙이 정의된 출처·근거수준을 갖췄는지 코드 검증
(2) build_ledger(): 근거 전체를 한눈에 볼 수 있는 EVIDENCE_LEDGER.md 생성

'출처 이름만 있고 실체 없는' 상태를 잡고, 근거를 문서로 정리한다.
"""

import json
import os

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "..", "data")
SHARED_DIR = os.path.join(HERE, "..")


def _load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


def verify():
    sources = _load("evidence_sources.json")["sources"]
    interactions = _load("drug_drug_interactions_demo.json")

    problems = []
    stats = {"STRONG": 0, "MODERATE": 0, "LIMITED": 0}
    verif_stats = {"VERIFIED_SOURCE": 0, "MECHANISM_INFERRED": 0}

    for r in interactions:
        iid = r.get("interaction_id", "?")
        if not r.get("evidence_level"):
            problems.append(f"{iid}: 근거수준 없음")
        else:
            stats[r["evidence_level"]] = stats.get(r["evidence_level"], 0) + 1
        v = r.get("verification")
        if not v:
            problems.append(f"{iid}: 검증상태(verification) 없음")
        else:
            verif_stats[v] = verif_stats.get(v, 0) + 1
        if not r.get("evidence_note"):
            problems.append(f"{iid}: 근거 설명 없음")
        if not r.get("source_ids"):
            problems.append(f"{iid}: 출처 없음")
        for sid in r.get("source_ids", []):
            if sid not in sources:
                problems.append(f"{iid}: 정의되지 않은 출처 '{sid}'")

    return problems, stats, verif_stats, len(interactions)


def build_ledger():
    """근거 장부(EVIDENCE_LEDGER.md) 생성 — 모든 근거를 한 파일로."""
    sources = _load("evidence_sources.json")["sources"]
    interactions = _load("drug_drug_interactions_demo.json")

    L = ["# 근거 장부 (Evidence Ledger)", "",
         "필체크의 모든 규칙과 그 근거를 한눈에 정리한 자동 생성 문서입니다.",
         "`verify_evidence.py`로 생성됩니다. 규칙이 바뀌면 다시 생성하세요.", ""]

    # 근거수준 요약
    from collections import Counter
    c = Counter(r.get("evidence_level") for r in interactions)
    vc = Counter(r.get("verification") for r in interactions)
    L.append("## 요약")
    L.append(f"- 약물 상호작용 규칙: {len(interactions)}건 "
             f"(강 {c.get('STRONG',0)} / 중 {c.get('MODERATE',0)} / 약 {c.get('LIMITED',0)})")
    L.append(f"- 검증상태: 원문확인 {vc.get('VERIFIED_SOURCE',0)}건 / "
             f"기전추론(원문미확인) {vc.get('MECHANISM_INFERRED',0)}건")
    L.append(f"- 공식 근거원: {len(sources)}곳")
    L.append("")
    L.append("> **정직성 고지**: '원문확인'은 이 프로젝트에서 약학정보원·식약처 등 "
             "실제 출처를 확인한 것입니다. '기전추론'은 널리 알려진 약리 기전이나 "
             "이 프로젝트에서 특정 원문을 대조하지는 않은 것으로, 참고용이며 "
             "실제 판정은 식약처 DUR·약사 확인이 우선합니다.")
    L.append("")

    # 근거원 목록
    L.append("## 공식 근거원")
    L.append("")
    L.append("| ID | 이름 | 연도 | URL |")
    L.append("| --- | --- | --- | --- |")
    for sid, s in sources.items():
        L.append(f"| {sid} | {s['name']} | {s.get('year','-')} | {s['url']} |")
    L.append("")

    # 상호작용별 근거
    L.append("## 약물 상호작용 근거 (전체)")
    L.append("")
    order = {"STRONG": 0, "MODERATE": 1, "LIMITED": 2}
    for r in sorted(interactions, key=lambda x: order.get(x.get("evidence_level"), 9)):
        lvl = {"STRONG": "강", "MODERATE": "중", "LIMITED": "약"}.get(r.get("evidence_level"), "?")
        verif = "✓원문확인" if r.get("verification") == "VERIFIED_SOURCE" else "△기전추론(원문미확인)"
        L.append(f"### [{lvl}·{verif}] {r['combo']}")
        L.append(f"- 심각도: {r['severity']}")
        L.append(f"- 근거: {r.get('evidence_note','-')}")
        label = "출처" if r.get("verification") == "VERIFIED_SOURCE" else "참고문헌"
        src = " / ".join(f"{sources[s]['name']} ({sources[s]['url']})"
                         for s in r.get("source_ids", []) if s in sources)
        L.append(f"- {label}: {src or '-'}")
        L.append("")

    out_path = os.path.join(SHARED_DIR, "EVIDENCE_LEDGER.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return out_path


if __name__ == "__main__":
    problems, stats, verif_stats, total = verify()
    print(f"검증: 상호작용 {total}건 / 근거수준 강={stats.get('STRONG',0)} 중={stats.get('MODERATE',0)} 약={stats.get('LIMITED',0)}")
    print(f"검증상태: 원문확인={verif_stats.get('VERIFIED_SOURCE',0)} / 기전추론={verif_stats.get('MECHANISM_INFERRED',0)}")
    if problems:
        print(f"[문제 {len(problems)}건]")
        for p in problems:
            print("  ✗", p)
    else:
        print("[OK] 모든 규칙이 출처·근거수준·검증상태를 갖추었습니다.")
    path = build_ledger()
    print(f"[생성] 근거 장부: {path}")
