"""
약물 상담 로직 — 4축 엔진을 챗봇용으로 감싼다.
키(Pinecone/LLM) 없이도 항상 작동한다. 판정은 shared 엔진의 자체 규칙 데이터로 한다.

한계: 문장에서 사전에 있는 약 이름만 찾는다. 사전에 없는 약 이름은 문장에서 알아볼 수 없어
      검사에서 빠지며, 빠졌다는 사실도 알려 주지 못한다. "안 먹어요" 같은 부정 표현도 구분하지 못한다.
"""

import os
import sys
import json

# shared 엔진 경로 추가
HERE = os.path.dirname(__file__)
sys.path.append(os.path.join(HERE, "..", "shared", "engine"))
sys.path.append(os.path.join(HERE, "..", "shared", "dur_client"))

import drug_interaction as engine

# 일상어 매핑 로드 (혈압약 → RX002 등)
_COLLOQUIAL = {}
try:
    _colloq_path = os.path.join(HERE, "..", "shared", "data", "colloquial_drugs.json")
    with open(_colloq_path, encoding="utf-8") as f:
        _COLLOQUIAL = json.load(f).get("colloquial_map", {})
except Exception:
    _COLLOQUIAL = {}


def extract_drugs_detailed(text: str):
    """
    사용자 메시지에서 약을 뽑되, 정확한 것과 일상어(대략적)를 구분한다.
    반환: {"precise": [이름...], "colloquial": [(일상어, drug_id)...]}
    """
    precise = []          # 문장에 나온 순서와 무관하게, 긴 이름부터 찾은 순서
    seen_ids = set()
    colloquial = []

    # 1) 정확한 매칭 (제품명·성분명·별칭)
    #    긴 이름부터 찾고, 찾은 자리는 가린다. 이렇게 하지 않으면 약 하나가 여러 개로 세어진다.
    #    예: "타이레놀8시간이알서방정" 안의 "타이레놀"이 또 잡혀 '아세트아미노펜 중복'으로 나오던 문제
    masked = text
    for name in _CANDIDATE_NAMES:
        if name not in masked:
            continue
        masked = masked.replace(name, "▪" * len(name))
        d = engine.resolve_drug(name)
        if d is None or d["drug_id"] in seen_ids:     # 같은 약의 다른 표기는 한 번만
            continue
        seen_ids.add(d["drug_id"])
        precise.append(name)

    # 2) 일상어 매칭 (혈압약, 당뇨약 등) — 정확한 걸로 안 잡힌 것만
    #    '혈압', '당뇨' 같은 질환명은 약이 아니므로 쓰지 않는다.
    #    ("혈압이 높은데 타이레놀 먹어도 되나"에서 혈압약을 먹는 것으로 해석하던 문제)
    precise_rx = {rx for n in precise for rx in engine.rule_ids_of(engine.resolve_drug(n))}
    for word in sorted(_COLLOQUIAL.keys(), key=len, reverse=True):
        if not word.endswith(_DRUG_WORD_ENDINGS) or word not in masked:
            continue
        drug_id = _COLLOQUIAL[word]
        masked = masked.replace(word, "▪" * len(word))
        if drug_id not in precise_rx and drug_id not in [c[1] for c in colloquial]:
            colloquial.append((word, drug_id))

    return {"precise": precise, "colloquial": colloquial}


# 일상어 중 '약'을 가리키는 말의 끝 글자. 질환명('혈압', '당뇨', '고지혈증')은 제외된다.
_DRUG_WORD_ENDINGS = ("약", "제", "항히스타민")


def _build_candidate_names():
    """문장에서 찾을 약 이름 후보(두 글자 이상), 긴 것부터."""
    names = set()
    for d in engine.DRUG_DICT:
        for fld in ("국내 제품명·별칭 예시", "대표 성분(영문)"):
            for part in str(d.get(fld, "")).split("|"):
                for token in part.replace(")", "(").split("("):
                    token = token.strip()
                    if len(token) >= 2 and engine.resolve_drug(token) is not None:
                        names.add(token)
    try:
        import product_resolver
        for p in product_resolver._PRODUCT_MAP:
            names.update(n for n in [p["product"]] + p.get("aliases", []) if len(n) >= 2)
    except Exception:
        pass
    return sorted(names, key=len, reverse=True)


_CANDIDATE_NAMES = _build_candidate_names()


def _find_id(name):
    """정확 매칭된 이름의 drug_id를 찾는다 (중복 방지용)."""
    d = engine.resolve_drug(name)
    return d.get("drug_id") if d else None


def extract_drug_names(text: str) -> list:
    """상호작용 검사에 넣을 약 목록. 정확+일상어 합친 최종 리스트."""
    detail = extract_drugs_detailed(text)
    names = list(detail["precise"])
    # 일상어는 대표 성분명으로 변환해서 추가
    for word, drug_id in detail["colloquial"]:
        d = next((x for x in engine.DRUG_DICT if x["drug_id"] == drug_id), None)
        if d:
            names.append(d["약물군"])  # 계열명으로 (엔진이 인식)
    return names


def is_drug_question(text: str) -> bool:
    """이 메시지가 약물 상담인지 판단."""
    # '약', '같이', '함께'만으로는 판단하지 않는다.
    # ("예약 변경하고 싶어요", "같이 쓰기 좋은 청소기 추천"이 약물 상담으로 가던 문제)
    keywords = ["먹어도", "복용", "상호작용", "부작용", "병용", "약을", "약이랑", "약하고", "약 먹", "무슨 약", "어떤 약"]
    has_keyword = any(k in text for k in keywords) and "예약" not in text
    has_drug = len(extract_drug_names(text)) > 0
    return has_drug or has_keyword


def answer_drug_question(text: str, age: int = None) -> dict:
    """
    약물 상담 답변 생성.
    반환: {"type": "drug", "drugs": [...], "report": "...", "risk": "..."}
    """
    detail = extract_drugs_detailed(text)
    drugs = extract_drug_names(text)

    if not drugs:
        return {
            "type": "drug",
            "drugs": [],
            "report": "어떤 약을 확인해 드릴까요? 약 이름을 알려주세요.\n"
                      "· 상비약이면 제품 이름으로: '타이레놀', '게보린', '판피린'\n"
                      "· 처방약이면 약 봉지·처방전의 이름으로: '노바스크', '리피토'\n"
                      "· 잘 모르면 종류로: '혈압약', '당뇨약', '소화제'",
            "risk": None,
        }

    if len(drugs) == 1:
        return {
            "type": "drug",
            "drugs": drugs,
            "report": f"'{drugs[0]}' 하나만으로는 상호작용을 확인할 수 없어요.\n"
                      "함께 드시는 다른 약도 알려주시면 같이 확인해 드릴게요.",
            "risk": None,
        }

    result = engine.check(drugs, age=age)
    report = engine.format_report(result)
    risk = result["overall_risk"]["level"]

    # 일상어로 잡힌 게 있으면 안내 문구 추가
    note = ""
    if detail["colloquial"]:
        colloq_words = ", ".join(w for w, _ in detail["colloquial"])
        note = (
            f"\n\n[참고] '{colloq_words}'은(는) 종류가 여러 가지라 대표적인 약으로 "
            "대략 확인한 거예요. 정확히 하려면 약 봉지·처방전의 제품 이름을 "
            "알려주세요. (예: 혈압약 → '노바스크', '디오반')"
        )

    return {
        "type": "drug",
        "drugs": drugs,
        "report": report + note,
        "risk": risk,
        "risk_reasons": result["overall_risk"]["reasons"],
        "has_colloquial": bool(detail["colloquial"]),
    }
