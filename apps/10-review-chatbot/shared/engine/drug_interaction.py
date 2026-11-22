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
  - 기본 판정은 이 저장소의 규칙 데이터(data/drug_drug_interactions_demo.json)로 한다.
  - check(..., use_dur=True)를 주면 식약처 DUR 공식 데이터(dur_client)로 보강한다(네트워크 필요):
    허가정보 API로 약→품목기준코드를 구한 뒤 DUR 병용금기·노인주의·임부금기를 실시간 조회해
    결과의 result["dur"]에 담고, 출처를 '식약처 DUR'로 표시한다. 키/네트워크가 없으면
    available=False로만 두고 로컬 판정은 그대로 유지한다(기본값 use_dur=False).
  - DUR 병용금기는 '절대 금기'만 등재하므로 로컬 규칙을 대체하지 않고 보강만 한다.
  - 약 이름은 정확히 일치할 때만 해석한다. 못 찾은 약이 있으면 '낮음'이 아니라 '판단 불가'로 답한다.
  - 이 엔진은 스스로 의학적 판단을 만들지 않는다. 시너지·처방은 다루지 않는다.

* 의료기기가 아니며 진단·처방을 하지 않는다.
* DB 미등재가 안전을 의미하지 않는다.
* 최종 판단은 반드시 의사·약사가 한다.
"""

import json
import os
import re
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

try:
    import dur_check
    _DUR_CHECK = True
except Exception:
    _DUR_CHECK = False


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


def _ingredient_names(drug):
    raw = drug.get("대표 성분(영문)", "")
    names = []
    for token in raw.replace(")", "").split("|"):
        ko = token.split("(")[0].strip()
        if ko:
            names.append(ko)
    return names


# ── 이름 해석 ────────────────────────────────────────────────────────
#
# 약 이름은 '정확히 일치'할 때만 인정한다.
# 이전에는 입력이 사전 문자열의 일부이기만 하면 매칭했는데(q in haystack),
# 빈 문자열이나 "제" 같은 한 글자가 와파린으로, "진통제"가 소염진통제로 해석되는 오류가 있었다.
# 약 안전 안내에서 엉뚱한 약으로 해석하는 것은 "모른다"고 답하는 것보다 위험하므로,
# 일치하지 않으면 해석하지 않는다(unresolved).

# 제형 접미사: "리피토정" → "리피토"처럼 접미사를 뗀 이름으로 한 번 더 찾는다.
_FORM_SUFFIXES = ("필름코팅정", "연질캡슐", "서방정", "현탁액", "내복액", "캡슐", "시럽", "정", "액")


def _norm(text):
    """비교용 정규화: 공백 제거 + 대소문자 무시."""
    return re.sub(r"\s+", "", str(text)).casefold()


def _strip_form(q):
    for suf in _FORM_SUFFIXES:
        if q.endswith(suf) and len(q) - len(suf) >= 2:
            return q[:-len(suf)]
    return None


def _dict_tokens(d):
    """약물사전 한 항목에서 '이 이름이면 이 약'이라고 볼 수 있는 이름 조각을 뽑는다."""
    raw = []
    # 계열 이름이 "분류-세부" 꼴이면 세부 쪽만 이름으로 인정한다.
    # 앞쪽 분류어("위장약", "혈압약", "수면제")는 여러 약을 가리키는 일상어라서 엔진이 임의로 고르지 않는다.
    # (일상어는 채팅 쪽의 일상어 매핑이 '대략 확인'이라는 안내와 함께 처리한다.)
    group = d.get("약물군", "")
    detail = group.split("-", 1)[1] if "-" in group else group
    raw += re.split(r"[/()·]", detail)
    for fld in ("대표 성분(영문)", "국내 제품명·별칭 예시"):
        for part in str(d.get(fld, "")).split("|"):
            raw += re.split(r"[()]", part)
    tokens = set()
    for t in raw:
        t = _norm(t)
        # 설명 문구("처방 확인 필요", "MAOI 계열", "… 등 복합")는 이름이 아니다
        if len(t) < 2 or any(x in t for x in ("처방", "계열", "복합", "등")):
            continue
        tokens.add(t)
    tokens.add(_norm(d.get("약물군", "")))       # 계열 전체 이름은 항상 인정
    return tokens


def _build_dict_index():
    """이름 → 약물사전 항목. 둘 이상의 약에 걸리는 이름("혈압약", "항우울제")은 넣지 않는다."""
    owners = {}
    for d in DRUG_DICT:
        for t in _dict_tokens(d):
            owners.setdefault(t, set()).add(d["drug_id"])
    by_id = {d["drug_id"]: d for d in DRUG_DICT}
    return {t: by_id[next(iter(ids))] for t, ids in owners.items() if len(ids) == 1}


_DICT_BY_ID = {d["drug_id"]: d for d in DRUG_DICT}
_DICT_INDEX = _build_dict_index()

# 제품의 효능군(class_hint) → 약물사전 ID. 사전의 therapeutic_class와 이름이 다른 것만 따로 적는다.
_CLASS_TO_RX = {d.get("therapeutic_class"): d["drug_id"] for d in DRUG_DICT if d.get("therapeutic_class")}
_CLASS_TO_RX.update({
    "ANTIHYPERTENSIVE_ARB": "RX003",
    "COMBO_ANALGESIC": "RX013",
    "NSAID_COMBO": "RX012",
    "ANTIDIABETIC_METFORMIN": "RX008",
    "ANTIDIABETIC_SU": "RX008",
    "ANTIBIOTIC_QUINOLONE": "RX009",
})
# 성분 이름 → 약물사전 ID (복합제의 각 성분에도 상호작용 규칙이 적용되도록)
_INGREDIENT_TO_RX = {}
for _d in DRUG_DICT:
    for _name in _ingredient_names(_d):
        _n = _norm(_name)
        if len(_n) >= 3 and "복합" not in _n and "계열" not in _n:
            _INGREDIENT_TO_RX[_n] = _d["drug_id"]
_INGREDIENT_TO_RX[_norm("카페인")] = "RX024"            # 무수카페인·카페인무수물 표기 통일
_INGREDIENT_TO_RX[_norm("아세틸살리실산")] = "RX012"      # 아스피린의 성분명


def _product_rule_ids(p):
    """제품이 어떤 약물사전 항목(들)에 해당하는지. 상호작용 규칙은 이 ID로 찾는다.

    이전에는 제품에 'PROD:제품명'이라는 ID만 붙여서, 제품명으로 입력한 약은
    병용금기·주의 규칙이 하나도 걸리지 않았다(와파린 + 타이레놀정 → '낮음').
    """
    ids = []
    cls = _CLASS_TO_RX.get(p.get("class_hint", ""))
    if cls:
        ids.append(cls)
    for ing in p.get("ingredients", []):
        n = _norm(ing)
        for name, rx in _INGREDIENT_TO_RX.items():
            if name in n and rx not in ids:
                ids.append(rx)
    return ids


def _from_product(p):
    return {
        "drug_id": "PROD:" + p["product"],
        "약물군": p["product"] + " (" + "/".join(p.get("ingredients", [])) + ")",
        "대표 성분(영문)": "/".join(p.get("ingredients", [])),
        "국내 제품명·별칭 예시": p["product"],
        "therapeutic_class": p.get("class_hint", ""),
        "ingredient_tags": p.get("ingredient_tags", []),
        "rule_ids": _product_rule_ids(p),
        "_from_product": True,
        "_caution": p.get("caution", ""),
    }


def _resolve_exact(q):
    if q in _DICT_BY_ID:                         # 약물사전 ID 직접 입력
        return _DICT_BY_ID[q]
    if _PRODUCT_RESOLVER:                        # 제품명이 계열명보다 구체적이므로 먼저 본다
        p = product_resolver.resolve_product(q)
        if p:
            return _from_product(p)
    return _DICT_INDEX.get(_norm(q))


def resolve_drug(query):
    """
    약 이름/제품명/ID → 표준 약물 dict. 못 찾으면 None.
    순서: (1) 약물사전 ID (2) 제품명 (3) 약물사전의 성분명·별칭·계열명 (4) 제형 접미사를 떼고 다시
    모든 단계가 정확 일치이며, 두 글자 미만 입력은 해석하지 않는다.
    """
    q = str(query or "").strip()
    if len(_norm(q)) < 2:
        return None
    d = _resolve_exact(q)
    if d is None:
        stripped = _strip_form(_norm(q))
        if stripped:
            d = _resolve_exact(stripped)
    return d


def rule_ids_of(drug):
    """상호작용 규칙을 찾을 때 쓰는 약물사전 ID 목록."""
    return drug.get("rule_ids") or [drug["drug_id"]]


# ── 축 1: 병용금기/주의 ──────────────────────────────────────────────

def _axis_pairwise(drugs):
    """자체 구축 규칙 기반 병용금기/주의. 약 쌍마다 검사한다.
    복합제는 여러 약물사전 ID를 가지므로(게보린 = 아세트아미노펜 + 카페인), ID 집합끼리 비교한다."""
    found, seen = [], set()
    for x, y in combinations(drugs, 2):
        ids_x, ids_y = set(rule_ids_of(x)), set(rule_ids_of(y))
        for rule in DEMO_INTERACTIONS:
            a, b = rule["drug_a"], rule["drug_b"]
            hit = (a in ids_x and b in ids_y) or (b in ids_x and a in ids_y)
            if hit and rule["interaction_id"] not in seen:
                seen.add(rule["interaction_id"])
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

def _axis_polypharmacy(drugs, n_unresolved=0):
    """
    약 개수에 따른 상호작용 쌍 수와 다제약물 위험 수준을 계산.
    쌍의 수 = nC2. 약이 늘수록 상호작용 가능성이 급증함을 보여준다.
    사전에서 찾지 못한 약도 '복용 중인 약'이므로 개수에 포함한다.
    """
    n = len(drugs) + n_unresolved
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

def _overall_risk(axis1, axis2, axis3, axis4, unresolved=()):
    """
    확인하지 못한 약이 있으면: 위험·주의가 발견된 경우에는 그 레벨을 유지하되 이유에 덧붙이고,
    아무것도 발견되지 않은 경우에는 '낮음'이 아니라 '판단 불가'로 답한다.
    (모르는 약을 검사하지 못한 것과, 검사해서 문제가 없는 것은 다르다.)
    """
    risk = _overall_risk_known(axis1, axis2, axis3)
    if axis3["count"] < 2:
        return {"level": "판단 불가", "code": "UNKNOWN",
                "reasons": ["약이 2가지 이상 있어야 함께 먹을 때의 위험을 확인할 수 있어요"]}
    if unresolved:
        names = ", ".join(unresolved)
        if risk["code"] == "LOW":
            return {"level": "판단 불가", "code": "UNKNOWN",
                    "reasons": [f"확인하지 못한 약이 {len(unresolved)}개 있어요: {names}",
                                "이 약들은 검사하지 못했기 때문에 위험도를 말씀드릴 수 없어요. 약사에게 확인하세요"]}
        risk["reasons"].append(f"확인하지 못한 약 {len(unresolved)}개({names})는 검사에 포함되지 않았어요")
    return risk


def _overall_risk_known(axis1, axis2, axis3):
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


def _english_ingredient(drug):
    """약물사전 항목의 '대표 성분(영문)'에서 영문 성분명을 뽑는다. 예: '와파린(Warfarin)' → 'Warfarin'.
    허가정보 API의 item_ingr_name(영문)로 쓰려는 것. 없으면 None."""
    raw = drug.get("대표 성분(영문)", "")
    m = re.findall(r"\(([A-Za-z][A-Za-z0-9 .\-]+)\)", raw)
    return m[0].strip() if m else None


def augment_with_dur(result, with_cautions=True):
    """
    check() 결과에 식약처 DUR 공식 데이터를 보강한다(네트워크 필요).
    - result["dur"]: {"available", "combination_taboo":[...], "profiles":[...], "unresolved":[...]}
      · combination_taboo 는 DUR이 '절대 병용금기'로 등재한 쌍(출처='식약처 DUR').
      · profiles[].cautions 에 노인주의·임부금기 등 품목 단위 주의.
    - 로컬 규칙 판정(axis1~4)은 그대로 두고 DUR을 별도로 덧붙인다(대체하지 않음).
    키가 없거나 조회 실패 시 available=False로만 표시하고 로컬 결과는 유지한다.
    """
    if not (_DUR_CHECK and _DUR_AVAILABLE and getattr(dur_api, "SERVICE_KEY", "")):
        result["dur"] = {"available": False,
                         "reason": "DUR 서비스키가 없거나 DUR 모듈을 불러오지 못했습니다."}
        return result
    drugs = [{"label": d["약물군"], "product_name": q, "eng_ingredient": _english_ingredient(d)}
             for q, d in result["resolved"]]
    try:
        dur = dur_check.check_interactions(drugs, with_cautions=with_cautions)
    except Exception as e:
        result["dur"] = {"available": False, "reason": f"DUR 조회 실패: {e}"}
        return result
    result["dur"] = {"available": True, **dur}
    result["mode"] = "LOCAL_RULES+DUR"
    return result


def check(drug_queries, age=None, use_dur=False):
    """
    drug_queries: 약 이름/ID 목록.
    age: (선택) 나이. 노인주의 축에 사용.
    use_dur: True면 식약처 DUR 공식 데이터로 보강(네트워크 필요). 기본은 로컬 규칙만.
    반환: 4개 축의 분석 결과 + 근거 모드.
    """
    resolved, unresolved, seen = [], [], set()
    for q in drug_queries:
        q = str(q or "").strip()
        if not q:
            continue                                  # 빈 입력은 약이 아니다
        d = resolve_drug(q)
        if d is None:
            if q not in unresolved:
                unresolved.append(q)
        elif d["drug_id"] not in seen:                # 같은 약을 두 번 적어도 한 번만 센다
            seen.add(d["drug_id"])                    # (타이레놀 + 타이레놀정 → 1개)
            resolved.append((q, d))

    # 제품명과 그 제품의 성분명을 함께 적은 경우("타이레놀, 아세트아미노펜")는 같은 약으로 본다.
    # 단일 성분 제품일 때만 해당한다. 서로 다른 제품 두 개(타이레놀 + 써스펜)는 그대로 중복으로 잡힌다.
    single = {d["rule_ids"][0] for _, d in resolved
              if d.get("_from_product") and len(d.get("rule_ids", [])) == 1}
    resolved = [(q, d) for q, d in resolved
                if not (not d.get("_from_product") and d["drug_id"] in single
                        and _norm(q) in _INGREDIENT_TO_RX)]
    drugs = [d for _, d in resolved]

    a1 = _axis_pairwise(drugs)
    a2 = _axis_duplicate(drugs)
    a3 = _axis_polypharmacy(drugs, len(unresolved))
    a4 = _axis_elderly(drugs, age)

    result = {
        # 로컬 규칙 판정이 기본. use_dur=True면 아래에서 식약처 DUR 공식 데이터로 보강한다.
        "mode": "LOCAL_RULES",
        "age": age,
        "resolved": resolved,
        "unresolved": unresolved,
        "overall_risk": _overall_risk(a1, a2, a3, a4, unresolved),
        "axis1_interactions": a1,
        "axis2_duplicates": a2,
        "axis3_polypharmacy": a3,
        "axis4_elderly": a4,
    }
    if use_dur:
        augment_with_dur(result)
    return result


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

    dur = result.get("dur")
    if dur and dur.get("available"):
        L.append(f"\n[근거] 자체 구축 규칙 {len(DEMO_INTERACTIONS)}건 + 식약처 DUR 공식 데이터 실시간 조회 · 참고용")
    else:
        L.append(f"\n[근거] 자체 구축 규칙 {len(DEMO_INTERACTIONS)}건 기준 (식약처 DUR API는 이번 조회에 사용되지 않음 · 참고용)")

    # 종합 위험도 (근거 명시)
    risk = result["overall_risk"]
    L.append(f"\n[종합 위험도] {risk['level']}")
    L.append("  이 판단의 이유:")
    for r in risk["reasons"]:
        L.append(f"    · {r}")

    # 축 3: 다제약물 (전체 요약 먼저)
    poly = result["axis3_polypharmacy"]
    n_known = len(result["resolved"])
    if result["unresolved"]:
        L.append(f"\n[다제약물] 총 {poly['count']}가지 · 가능한 조합 {poly['pairs']}쌍 "
                 f"(찾지 못한 약을 뺀 {n_known * (n_known - 1) // 2}쌍만 검사)")
    else:
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
        if result["unresolved"]:
            L.append("  확인된 약 사이에는 겹치는 성분이 없어요. (찾지 못한 약은 검사하지 못했어요)")
        else:
            L.append("  겹치는 성분이 없어요. (미등재가 안전을 뜻하진 않아요)")
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
        # 나이를 모르면 모든 사용자에게 단정하지 않고 조건을 붙여 안내한다
        L.append("\n[노인주의]" if result.get("age") is not None else "\n[노인주의 — 65세 이상인 경우]")
        for f in elderly:
            lvl = f.get("evidence_level_ko", "")
            lvl_str = f" · 근거 {lvl}" if lvl else ""
            L.append(f"  · {f['drug']}{lvl_str}: {f['message']}")
            if f.get("evidence_note"):
                L.append(f"      근거: {f['evidence_note']}")
            src_names = _src_links(f.get("source_ids", []))
            if src_names:
                L.append(f"      출처: {src_names}")

    # 식약처 DUR 공식 조회 결과 (use_dur=True일 때만)
    dur = result.get("dur")
    if dur and dur.get("available"):
        L.append("\n[식약처 DUR 공식 조회]")
        taboo = dur.get("combination_taboo", [])
        if taboo:
            for h in taboo:
                L.append(f"  [병용금기 · 식약처 DUR] {h['a']} + {h['b']}")
                L.append(f"      · 사유: {h['reason']}")
        else:
            L.append("  · DUR에 등재된 '절대 병용금기' 조합은 없어요. "
                     "(DUR 병용금기는 절대 금기만 등재하며, 미등재가 안전을 뜻하진 않아요)")
        for p in dur.get("profiles", []):
            cz = [f"{k} {len(v)}건" for k, v in (p.get("cautions") or {}).items() if v]
            if cz:
                L.append(f"  · {p['label']} (품목기준코드 {p['item_seq']}): {', '.join(cz)}")
        if dur.get("unresolved"):
            L.append(f"  · 허가정보에서 품목코드를 찾지 못한 약: {', '.join(dur['unresolved'])}")
    elif dur and not dur.get("available"):
        L.append(f"\n[식약처 DUR 공식 조회] 사용 안 됨 — {dur.get('reason', '')}")

    L.append("\n" + "-" * 62)
    L.append("※ 참고용입니다. 진단·처방이 아니며 최종 판단은 의사·약사가 합니다.")
    L.append("※ 위험이 확인되면 가까운 약국·병원에서 상담하세요.")
    return "\n".join(L)


# README와 demo_output.txt에 실린 시나리오. 실행:  python drug_interaction.py > demo_output.txt
DEMO_SCENARIOS = [
    ("게보린+타이레놀+자낙스 (70세)", ["게보린", "타이레놀", "자낙스"], 70),
    ("노바스크+클래리스로마이신+리피토", ["노바스크", "클래리스로마이신", "리피토"], None),
    ("와파린+부루펜+넥시움", ["와파린", "부루펜", "넥시움"], None),
    ("와파린+탁센+사전에 없는 약", ["와파린", "탁센", "플라빅스"], None),
]

if __name__ == "__main__":
    for title, names, age in DEMO_SCENARIOS:
        print(f"########## {title} ##########")
        print(format_report(check(names, age=age)))
        print("\n")
