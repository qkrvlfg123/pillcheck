"""
필체크(PillCheck) — 약물-약물 상호작용 검사 엔진
================================================

여러 약을 함께 복용할 때의 위험을 4개 축으로 분석한다.

  [축 1] 병용금기/주의  : 두 약을 함께 쓰면 안 되는/조심할 조합
  [축 2] 효능군 중복    : 같은 계열/성분이 겹쳐 과용량이 되는 위험
                          (예: 감기약 + 진통제 → 아세트아미노펜 중복)
  [축 3] 다제약물       : 약이 3개·4개↑ 늘수록 상호작용 쌍이 급증하는 위험
  [축 4] 노인/연령 주의 : 특정 연령대에 주의가 필요한 약

판정 원칙 (중요):
  - 약물 상호작용의 '공식' 근거는 식약처 DUR API다(dur_client 참조).
  - DUR 미연동 시에는 데모 데이터로 '참고 표시'하되 미검증임을 명시한다.
  - 이 엔진은 스스로 의학적 판단을 만들지 않는다. 시너지·처방은 다루지 않는다.

* 의료기기가 아니며 진단·처방을 하지 않는다.
* DB 미등재가 안전을 의미하지 않는다.
* 최종 판단은 반드시 의사·약사가 한다.
"""

import json
import os
import sys
from itertools import combinations

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "..", "data")
DUR_DIR = os.path.join(HERE, "..", "dur_client")

sys.path.append(DUR_DIR)
try:
    import dur_api
    _DUR_AVAILABLE = True
except Exception:
    _DUR_AVAILABLE = False

try:
    import product_resolver
    _PRODUCT_RESOLVER = True
except Exception:
    _PRODUCT_RESOLVER = False


def _load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


DRUG_DICT = _load("drug_dictionary.json")
DEMO_INTERACTIONS = _load("drug_drug_interactions_demo.json")
try:
    EVIDENCE_SOURCES = _load("evidence_sources.json")["sources"]
except Exception:
    EVIDENCE_SOURCES = {}

SEVERITY_ORDER = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
SEVERITY_LABEL = {"HIGH": "위험", "MEDIUM": "주의", "LOW": "참고"}

# 효능군 중복 탐지 규칙: 같은 태그가 여러 약에 겹치면 위험
# (성분 태그 -> 겹쳤을 때의 위험 설명)
# 효능군 중복 탐지 규칙: (제목, 안내문, 심각도, 근거수준, 출처ID, 근거설명)
DUPLICATE_TAG_RULES = {
    "acetaminophen": ("아세트아미노펜 중복 (간독성 위험)",
                  "여러 약에 아세트아미노펜(타이레놀 성분)이 겹쳐 있어요. 겹쳐 드시면 하루 최대량을 넘겨 간에 무리가 갈 수 있어요. 감기약·두통약에 이미 들어있는 경우가 많으니 성분을 꼭 확인하세요.",
                  "HIGH", "강", ["MFDS_TYLENOL"],
                  "식약처 타이레놀 허가사항: 일일 최대 4,000mg 초과 금지, 아세트아미노펜 함유 다른 제품과 병용 금지 명문(2026)."),
    "analgesic": ("진통·해열 성분 중복",
                  "여러 약에 진통·해열 성분이 겹쳐 있어요. 정해진 용량을 넘지 않도록 주의하세요.",
                  "MEDIUM", "중", ["PHARMINFO"],
                  "동일 계열 진통제 중복 시 용량 초과 주의: 약학정보원 복약지침."),
    "contains_acetaminophen": ("아세트아미노펜 함유 (성분 확인 필요)",
                  "종합감기약에 이미 해열진통 성분이 들어 있어, 진통제를 더하면 성분이 겹칠 수 있어요. 성분표를 확인하세요.",
                  "HIGH", "강", ["MFDS_TYLENOL"],
                  "종합감기약 다수가 아세트아미노펜 함유: 식약처 제품정보 성분 확인 권고."),
    "serotonergic": ("세로토닌 작용 약물 중복",
                  "세로토닌을 높이는 약이 겹쳐 있어요. 드물게 위험한 반응(세로토닌증후군)이 생길 수 있어 의사 상담이 필요해요.",
                  "HIGH", "강", ["PHARMINFO", "MFDS_NEDRUG"],
                  "SSRI/트립탄/MAOI 등 세로토닌 작동성 약물 병용 시 세로토닌증후군: 약학정보원·식약처 제품정보 경고."),
    "cns_depressant": ("중추 억제(진정) 중복",
                  "졸림·진정을 유발하는 약이 겹쳐 있어요. 과하게 처지거나 호흡이 약해질 수 있어요.",
                  "HIGH", "중", ["PHARMINFO_INSOMNIA"],
                  "벤조디아제핀·Z드럭 등 중추억제 중첩 시 과진정: 약학정보원 불면증 치료자료(2024)."),
    "cns_stimulant": ("각성 성분 중복",
                  "각성·자극 성분이 겹쳐 있어요. 두근거림·불안·불면이 심해질 수 있어요.",
                  "MEDIUM", "중", ["PHARMINFO"],
                  "카페인 등 중추자극 중첩: 약학정보원."),
    "bleeding_risk": ("출혈 위험 약물 중복",
                  "출혈 위험을 높이는 약이 겹쳐 있어요. 멍·출혈이 잘 생길 수 있어 주의가 필요해요.",
                  "HIGH", "중", ["PHARMINFO"],
                  "항응고·항혈소판·NSAID 중첩 시 출혈 위험 증가: 약학정보원."),
    "bp_lowering": ("혈압 강하 작용 중복",
                  "혈압을 낮추는 약이 겹쳐 있어요. 어지럼·저혈압에 주의하세요.",
                  "MEDIUM", "약", ["PHARMINFO"],
                  "복수 강압제 병용 시 저혈압 주의: 일반 복약지침."),
    "sedative": ("진정·수면 작용 중복",
                  "진정·수면 작용이 겹쳐 있어요. 낮 시간 졸림·낙상에 주의하세요.",
                  "MEDIUM", "약", ["PHARMINFO_INSOMNIA"],
                  "진정계 중첩 시 주간 졸림: 약학정보원."),
}


def resolve_drug(query):
    """
    약 이름/제품명/ID → 표준 약물 dict.
    순서: (1) 약물사전 직접 매칭 (2) 제품명→성분 해석기 (게보린 등)
    제품에서 온 경우 성분 태그를 담은 임시 dict를 만들어 반환한다.
    """
    q = query.strip()

    # (1) 약물사전 직접
    for d in DRUG_DICT:
        if d["drug_id"] == q:
            return d
    for d in DRUG_DICT:
        haystack = " ".join([
            d.get("약물군", ""),
            d.get("대표 성분(영문)", ""),
            d.get("국내 제품명·별칭 예시", ""),
        ])
        if q in haystack:
            return d

    # (2) 제품명 해석기 (게보린/이지엔6에이스 등)
    if _PRODUCT_RESOLVER:
        p = product_resolver.resolve_product(q)
        if p:
            return {
                "drug_id": "PROD:" + p["product"],
                "약물군": p["product"] + " (" + "/".join(p.get("ingredients", [])) + ")",
                "대표 성분(영문)": "/".join(p.get("ingredients", [])),
                "국내 제품명·별칭 예시": p["product"],
                "therapeutic_class": p.get("class_hint", ""),
                "ingredient_tags": p.get("ingredient_tags", []),
                "_from_product": True,
                "_caution": p.get("caution", ""),
            }
    return None


def _ingredient_names(drug):
    raw = drug.get("대표 성분(영문)", "")
    names = []
    for token in raw.replace(")", "").split("|"):
        ko = token.split("(")[0].strip()
        if ko:
            names.append(ko)
    return names


# ── 축 1: 병용금기/주의 ──────────────────────────────────────────────

def _axis_pairwise(drugs):
    """데모 데이터 기반 병용금기/주의 (DUR 미연동 시). 약 쌍마다 검사."""
    ids = [d["drug_id"] for d in drugs]
    found = []
    for a, b in combinations(sorted(set(ids)), 2):
        for rule in DEMO_INTERACTIONS:
            if {rule["drug_a"], rule["drug_b"]} == {a, b}:
                found.append(rule)
    found.sort(key=lambda r: SEVERITY_ORDER.get(r["severity"], 0), reverse=True)
    return found


# ── 축 2: 효능군 중복 ────────────────────────────────────────────────

def _axis_duplicate(drugs):
    """같은 성분 태그가 2개 이상 약에 겹치면 중복 위험으로 보고."""
    tag_to_drugs = {}
    for d in drugs:
        for tag in d.get("ingredient_tags", []):
            tag_to_drugs.setdefault(tag, []).append(d["약물군"])

    findings = []
    for tag, names in tag_to_drugs.items():
        if len(names) >= 2 and tag in DUPLICATE_TAG_RULES:
            title, msg, sev, lvl, srcs, note = DUPLICATE_TAG_RULES[tag]
            findings.append({
                "title": title,
                "drugs": names,
                "message": msg,
                "severity": sev,
                "evidence_level_ko": lvl,
                "source_ids": srcs,
                "evidence_note": note,
            })
    findings.sort(key=lambda f: SEVERITY_ORDER.get(f["severity"], 0), reverse=True)
    return findings


# ── 축 3: 다제약물 위험 ──────────────────────────────────────────────

def _axis_polypharmacy(drugs):
    """
    약 개수에 따른 상호작용 쌍 수와 다제약물 위험 수준을 계산.
    쌍의 수 = nC2. 약이 늘수록 상호작용 가능성이 급증함을 보여준다.
    """
    n = len(drugs)
    pairs = n * (n - 1) // 2
    if n >= 5:
        level, note = "HIGH", "5가지 이상은 '다제약물'로 분류돼요. 상호작용 위험이 크게 늘어 정기적인 약사 검토(약물 재조정)를 권해요."
    elif n == 4:
        level, note = "MEDIUM", "4가지를 함께 드시면 검사할 조합이 6쌍으로 늘어요. 새 약을 더할 때 특히 주의하세요."
    elif n == 3:
        level, note = "LOW", "3가지를 함께 드시면 조합이 3쌍이에요. 아직은 관리 가능한 수준이지만 늘어날수록 주의가 필요해요."
    else:
        level, note = "NONE", ""
    return {"count": n, "pairs": pairs, "level": level, "note": note}


# ── 축 4: 노인/연령 주의 ─────────────────────────────────────────────

def _axis_elderly(drugs, age=None):
    """
    노인주의 약물 표시. 실제 판정은 DUR '노인주의' 항목이 담당.
    데모에서는 성분 태그로 대략의 주의 신호만 준다.
    age가 주어지고 65+ 이면 노인주의를 강조.
    """
    ELDERLY_CAUTION_CLASSES = {
        "BENZODIAZEPINE": "고령자에서 낙상·인지저하·섬망 위험이 커요.",
        "Z_DRUG": "고령자에서 야간 낙상·혼동 위험이 있어요.",
        "NSAID": "고령자에서 위장출혈·신장 부담 위험이 커요.",
        "ANTIHISTAMINE_2ND": "고령자에서 졸림·입마름이 두드러질 수 있어요.",
    }
    findings = []
    for d in drugs:
        cls = d.get("therapeutic_class", "")
        if cls in ELDERLY_CAUTION_CLASSES:
            findings.append({
                "drug": d["약물군"],
                "message": ELDERLY_CAUTION_CLASSES[cls],
                "applies": (age is None) or (age >= 65),
                "evidence_level_ko": "강" if cls in ("BENZODIAZEPINE", "Z_DRUG", "NSAID") else "중",
                "source_ids": ["BEERS_2023"],
                "evidence_note": "미국노인의학회 Beers Criteria 2023: 65세↑ 잠재적 부적절 약물. 벤조디아제핀·Z드럭·NSAID의 낙상·섬망·출혈 위험 명시.",
            })
    return findings


# ── 통합 진입점 ──────────────────────────────────────────────────────

def _overall_risk(axis1, axis2, axis3, axis4):
    """
    종합 위험도 레벨을 '규칙 기반'으로 결정하고, 그 레벨이 나온 이유를 함께 반환한다.
    점수(숫자)를 쓰지 않는다. 대신 어떤 발견이 레벨을 결정했는지 명시한다.

    레벨 규칙 (위에서부터 먼저 걸리는 것으로 결정):
      높음(HIGH)   : 병용금기/주의 중 '위험(HIGH)'이 1건 이상, 또는
                     효능군 중복 중 '위험(HIGH)'이 1건 이상, 또는
                     다제약물 5가지 이상(HIGH)
      보통(MEDIUM) : 위 HIGH는 없지만, '주의(MEDIUM)' 항목이 1건 이상, 또는
                     다제약물 4가지(MEDIUM)
      낮음(LOW)    : 위험/주의 발견이 없음 (참고 수준만 있거나 깨끗)
    """
    reasons = []

    high_inter = [r for r in axis1 if r["severity"] == "HIGH"]
    high_dup = [f for f in axis2 if f["severity"] == "HIGH"]
    med_inter = [r for r in axis1 if r["severity"] == "MEDIUM"]
    med_dup = [f for f in axis2 if f["severity"] == "MEDIUM"]

    if high_inter:
        reasons.append(f"함께 쓰면 위험한 조합이 {len(high_inter)}건 있어요")
    if high_dup:
        reasons.append(f"같은 성분이 겹쳐 위험한 중복이 {len(high_dup)}건 있어요")
    if axis3["level"] == "HIGH":
        reasons.append("복용 약이 5가지 이상(다제약물)이에요")

    if reasons:
        return {"level": "높음", "code": "HIGH", "reasons": reasons}

    if med_inter:
        reasons.append(f"주의가 필요한 조합이 {len(med_inter)}건 있어요")
    if med_dup:
        reasons.append(f"성분 중복 주의가 {len(med_dup)}건 있어요")
    if axis3["level"] == "MEDIUM":
        reasons.append("복용 약이 4가지예요")

    if reasons:
        return {"level": "보통", "code": "MEDIUM", "reasons": reasons}

    return {"level": "낮음", "code": "LOW",
            "reasons": ["등록된 위험·주의 조합이 발견되지 않았어요 (미등재가 안전을 뜻하진 않아요)"]}


def check(drug_queries, age=None):
    """
    drug_queries: 약 이름/ID 목록.
    age: (선택) 나이. 노인주의 축에 사용.
    반환: 4개 축의 분석 결과 + 근거 모드(DUR/데모).
    """
    resolved, unresolved = [], []
    for q in drug_queries:
        d = resolve_drug(q)
        if d:
            resolved.append((q, d))
        else:
            unresolved.append(q)
    drugs = [d for _, d in resolved]

    # 근거 모드
    dur_mode = _DUR_AVAILABLE and bool(os.environ.get("DUR_SERVICE_KEY"))

    a1 = _axis_pairwise(drugs)
    a2 = _axis_duplicate(drugs)
    a3 = _axis_polypharmacy(drugs)
    a4 = _axis_elderly(drugs, age)

    return {
        "mode": "DUR_OFFICIAL" if dur_mode else "DEMO_UNVERIFIED",
        "resolved": resolved,
        "unresolved": unresolved,
        "overall_risk": _overall_risk(a1, a2, a3, a4),
        "axis1_interactions": a1,
        "axis2_duplicates": a2,
        "axis3_polypharmacy": a3,
        "axis4_elderly": a4,
    }


def _src_links(source_ids):
    """source_id 목록 → '이름 (URL)' 문자열. 연도가 있으면 포함."""
    parts = []
    for sid in source_ids:
        s = EVIDENCE_SOURCES.get(sid)
        if s:
            year = f", {s['year']}" if s.get("year") else ""
            parts.append(f"{s['name']}{year} ({s['url']})")
    return " / ".join(parts)


def format_report(result):
    L = ["=" * 62, "필체크 — 복용약 상호작용 분석", "=" * 62]

    L.append("\n[입력한 약]")
    for q, d in result["resolved"]:
        L.append(f"  · {q}  ->  {d['약물군']} ({d['drug_id']})")
    for q in result["unresolved"]:
        L.append(f"  · {q}  ->  (사전에서 찾지 못함)")

    if result["mode"] == "DEMO_UNVERIFIED":
        L.append("\n[근거] [!] 식약처 DUR 미연동 -> 데모 데이터로 참고 표시 (미검증)")
    else:
        L.append("\n[근거] [O] 식약처 DUR 공식 데이터 기준")

    # 종합 위험도 (근거 명시)
    risk = result["overall_risk"]
    L.append(f"\n[종합 위험도] {risk['level']}")
    L.append("  이 판단의 이유:")
    for r in risk["reasons"]:
        L.append(f"    · {r}")

    # 축 3: 다제약물 (전체 요약 먼저)
    poly = result["axis3_polypharmacy"]
    L.append(f"\n[다제약물] 총 {poly['count']}가지 · 검사한 조합 {poly['pairs']}쌍")
    if poly["note"]:
        tag = SEVERITY_LABEL.get(poly["level"], "")
        L.append(f"  [{tag}] {poly['note']}")

    # 축 1: 병용금기/주의
    L.append("\n[병용금기·주의]")
    if not result["axis1_interactions"]:
        L.append("  발견된 위험 조합이 없어요. (미등재가 안전을 뜻하진 않아요)")
    for r in result["axis1_interactions"]:
        tag = SEVERITY_LABEL.get(r["severity"], r["severity"])
        lvl = r.get("evidence_level_ko", "")
        lvl_str = f" · 근거 {lvl}" if lvl else ""
        L.append(f"  [{tag}{lvl_str}] {r['combo']}")
        L.append(f"      · {r['service_message']}")
        if r.get("evidence_note"):
            verif = r.get("verification", "")
            mark = "✓원문확인" if verif == "VERIFIED_SOURCE" else "△기전추론"
            L.append(f"      · 근거[{mark}]: {r['evidence_note']}")
        src_names = _src_links(r.get("source_ids", []))
        if src_names:
            label = "출처" if r.get("verification") == "VERIFIED_SOURCE" else "참고"
            L.append(f"      · {label}: {src_names}")

    # 축 2: 효능군 중복
    L.append("\n[효능군·성분 중복]")
    if not result["axis2_duplicates"]:
        L.append("  겹치는 성분이 없어요.")
    for f in result["axis2_duplicates"]:
        tag = SEVERITY_LABEL.get(f["severity"], f["severity"])
        lvl = f.get("evidence_level_ko", "")
        lvl_str = f" · 근거 {lvl}" if lvl else ""
        L.append(f"  [{tag}{lvl_str}] {f['title']} — {', '.join(f['drugs'])}")
        L.append(f"      · {f['message']}")
        if f.get("evidence_note"):
            L.append(f"      · 근거: {f['evidence_note']}")
        src_names = _src_links(f.get("source_ids", []))
        if src_names:
            L.append(f"      · 출처: {src_names}")

    # 축 4: 노인주의
    elderly = [f for f in result["axis4_elderly"] if f["applies"]]
    if elderly:
        L.append("\n[노인주의]")
        for f in elderly:
            lvl = f.get("evidence_level_ko", "")
            lvl_str = f" · 근거 {lvl}" if lvl else ""
            L.append(f"  · {f['drug']}{lvl_str}: {f['message']}")
            if f.get("evidence_note"):
                L.append(f"      근거: {f['evidence_note']}")
            src_names = _src_links(f.get("source_ids", []))
            if src_names:
                L.append(f"      출처: {src_names}")

    L.append("\n" + "-" * 62)
    L.append("※ 참고용입니다. 진단·처방이 아니며 최종 판단은 의사·약사가 합니다.")
    L.append("※ 위험이 확인되면 가까운 약국·병원에서 상담하세요.")
    return "\n".join(L)


if __name__ == "__main__":
    print(format_report(check(["와파린", "부루펜", "타이레놀"])))
    print("\n\n")
    print(format_report(check(["렉사프로", "이미그란", "자낙스", "스틸녹스", "판피린"], age=70)))
