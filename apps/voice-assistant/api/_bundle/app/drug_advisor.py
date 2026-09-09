"""
약물 상담 로직 — 4축 엔진을 챗봇용으로 감싼다.
키(Pinecone/LLM) 없이도 항상 작동한다. 판정은 shared 엔진(→식약처 DUR)이 한다.
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
    precise = set()
    colloquial = []

    # 1) 정확한 매칭 (제품명·성분명)
    for d in engine.DRUG_DICT:
        for token in str(d.get("국내 제품명·별칭 예시", "")).split("|"):
            token = token.strip()
            if len(token) >= 2 and token in text:
                precise.add(token)
        for token in str(d.get("대표 성분(영문)", "")).split("|"):
            ko = token.split("(")[0].strip()
            if len(ko) >= 2 and ko in text:
                precise.add(ko)

    try:
        import product_resolver
        for p in product_resolver._PRODUCT_MAP:
            for name in [p["product"]] + p.get("aliases", []):
                if name in text:
                    precise.add(name)
    except Exception:
        pass

    # 2) 일상어 매칭 (혈압약, 당뇨약 등) — 정확한 걸로 안 잡힌 것만
    #    긴 단어부터 매칭하고, 이미 매칭된 텍스트 위치는 가려서 부분중복 방지
    #    (예: "소염진통제"가 잡히면 그 안의 "진통제"는 다시 안 잡힘)
    masked = text
    for word in sorted(_COLLOQUIAL.keys(), key=len, reverse=True):
        if word in masked:
            drug_id = _COLLOQUIAL[word]
            # 이미 이 계열이 정확히 잡혔으면 스킵
            if not any(drug_id == _find_id(pname) for pname in precise):
                if drug_id not in [c[1] for c in colloquial]:
                    colloquial.append((word, drug_id))
            # 매칭된 부분을 가려서 부분 문자열 재매칭 방지
            masked = masked.replace(word, "▪" * len(word))

    return {"precise": list(precise), "colloquial": colloquial}


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
    keywords = ["약", "먹어도", "복용", "같이", "함께", "상호작용", "부작용", "병용"]
    has_keyword = any(k in text for k in keywords)
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
