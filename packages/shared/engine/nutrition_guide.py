"""
필체크 — 영양소 안내 엔진 (약물 연계)
=====================================

직업·나이·수면/근무 패턴을 입력하면 '부족하기 쉬운' 영양소를 안내한다.
복용 중인 약이 있으면 영양제-약물 상호작용도 함께 점검한다.

법적 원칙 (약사법·건강기능식품법):
  - 질병 치료·예방 효과를 표방하지 않는다.
  - 특정 제품·브랜드를 판매 유도하지 않는다(성분 수준 정보만).
  - '무조건 먹으라'가 아니라 '부족할 수 있으니 참고, 전문가 상담'으로 안내.
  - 과잉 섭취 위험도 함께 고지한다.

이 엔진은 진단·처방을 하지 않는다. 결핍 여부는 혈액검사로 확인해야 하며,
여기 정보는 일반적 경향 안내일 뿐이다.
"""

import json
import os

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "..", "data")


def _load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


PROFILES = _load("nutrition_profiles.json")
NUTRIENTS = PROFILES["nutrients"]

# 영양소 → 약물 상호작용 (근거 있는 대표 사례)
# 우리 약물사전의 성분 태그/약물군과 연결
NUTRIENT_DRUG_INTERACTIONS = {
    "omega3": [
        ("항응고제", "오메가3는 혈액을 묽게 하는 작용이 있어 와파린 등과 함께 드시면 출혈 위험이 커질 수 있어요."),
    ],
    "vitamin_k": [
        ("항응고제", "비타민K는 와파린의 항응고 작용을 방해해요. '끊으라'가 아니라 평소 섭취량을 일정하게 유지하는 게 중요해요."),
    ],
    "vitamin_e": [
        ("항응고제", "고용량 비타민E는 출혈 위험을 높일 수 있어 와파린 등과 함께라면 주의가 필요해요."),
    ],
    "coq10": [
        ("항응고제", "코엔자임Q10은 와파린 효과에 영향을 줄 수 있다는 보고가 있어요."),
    ],
    "calcium": [
        ("항생제", "칼슘은 일부 항생제(테트라·퀴놀론)의 흡수를 방해해요. 복용 간격을 두세요."),
        ("갑상선약", "칼슘은 갑상선약(레보티록신) 흡수를 방해해요. 4시간 이상 간격을 두세요."),
        ("골다공증약", "칼슘은 골다공증약 흡수를 방해해요. 복용 시간을 분리하세요."),
    ],
    "zinc": [
        ("항생제", "아연은 일부 항생제(퀴놀론·테트라)의 흡수를 방해할 수 있어요. 간격을 두세요."),
    ],
    "vitamin_d": [
        ("이뇨제", "비타민D+칼슘 보충이 일부 이뇨제와 겹치면 고칼슘혈증 위험이 있을 수 있어요."),
    ],
    "iron": [
        ("갑상선약", "철분은 갑상선약 흡수를 방해해요. 복용 간격을 두세요."),
        ("제산제", "제산제와 철분은 서로 흡수를 방해할 수 있어요."),
        ("항생제", "철분은 일부 항생제 흡수를 방해할 수 있어요. 간격을 두세요."),
    ],
    "magnesium": [
        ("항생제", "마그네슘은 일부 항생제 흡수를 방해할 수 있어요. 간격을 두세요."),
    ],
}


def check_nutrient_drug(nutrient_ids, drug_list):
    """
    사용자가 먹는/고려하는 영양제와 복용약을 직접 대조한다(추천과 별개).
    nutrient_ids: 영양소 id 목록 (예: ["omega3","vitamin_k","calcium"])
    drug_list: 복용약 목록
    """
    warnings = []
    for nutrient in nutrient_ids:
        for drug_class, msg in NUTRIENT_DRUG_INTERACTIONS.get(nutrient, []):
            if _class_in_druglist(drug_class, drug_list) or drug_class in " ".join(drug_list):
                name = NUTRIENTS.get(nutrient, {}).get("name", nutrient)
                warnings.append((name, msg))
    return warnings


def guide(occupation_ids=None, age_band=None, sleep_short=False, drug_list=None):
    """
    occupation_ids: by_work_pattern의 id 목록 (예: ["shift_worker","sedentary_office"])
    age_band: "20s"|"30s"|"40s"|"50s"
    sleep_short: 수면 6시간 미만이면 True (sleep_deprived 자동 포함)
    drug_list: 복용 약 목록 (영양제-약물 상호작용 점검용)
    """
    occupation_ids = list(occupation_ids or [])
    if sleep_short and "sleep_deprived" not in occupation_ids:
        occupation_ids.append("sleep_deprived")

    # 관련 영양소 수집: 등장 횟수가 아니라 '어떤 조건 때문인지' 근거를 모은다.
    # 각 영양소마다 그것을 지목한 조건(직업/나이)과 이유를 함께 저장한다.
    nutrient_basis = {}   # nutrient -> [(조건라벨, 이유), ...]
    reasons = []

    def _add(source_label, nutrients, reason):
        for n in nutrients:
            nutrient_basis.setdefault(n, []).append((source_label, reason))

    for wp in PROFILES["by_work_pattern"]:
        if wp["id"] in occupation_ids:
            _add(wp["label"], wp["nutrients"], wp["reason"])
            reasons.append((wp["label"], wp["nutrients"], wp["reason"]))

    if age_band:
        for ab in PROFILES["by_age"]:
            if ab["age_band"] == age_band:
                _add(ab["label"], ab["nutrients"], ab["reason"])
                reasons.append((ab["label"], ab["nutrients"], ab["reason"]))

    # 정렬 근거: '몇 개의 조건이 이 영양소를 지목했나'를 쓰되,
    # 그 숫자 자체를 점수로 보여주지 않고 '어떤 조건들 때문인지'를 보여준다.
    # 동점이면 이름 안정정렬. (조건이 많이 겹칠수록 더 관련성이 크다는 근거)
    ranked = sorted(nutrient_basis.keys(),
                    key=lambda n: (-len(nutrient_basis[n]), n))

    # 영양제-약물 상호작용 점검
    drug_warnings = []
    if drug_list:
        drug_blob = " ".join(drug_list)
        for nutrient in ranked:
            for drug_class, msg in NUTRIENT_DRUG_INTERACTIONS.get(nutrient, []):
                # 약 목록에 해당 계열이 있으면 경고
                if drug_class in drug_blob or _class_in_druglist(drug_class, drug_list):
                    drug_warnings.append((NUTRIENTS[nutrient]["name"], msg))

    return {
        "nutrients": ranked,
        "nutrient_basis": nutrient_basis,
        "reasons": reasons,
        "drug_warnings": drug_warnings,
    }


def _class_in_druglist(drug_class, drug_list):
    """간단 매칭: 약 이름에 계열 키워드가 들어있는지."""
    keywords = {
        "항응고제": ["와파린", "쿠마딘"],
        "항생제": ["항생제", "시프로", "독시", "크라비트"],
        "갑상선약": ["갑상선", "씬지로이드", "레보티록신"],
        "골다공증약": ["골다공증", "포사맥스", "알렌드로"],
        "이뇨제": ["이뇨제", "라식스", "히드로클로로"],
        "제산제": ["제산제", "겔포스", "알마겔"],
    }
    for kw in keywords.get(drug_class, []):
        for d in drug_list:
            if kw in d:
                return True
    return False


def format_report(result):
    L = ["=" * 62, "필체크 — 영양소 참고 안내", "=" * 62]

    L.append("\n[입력한 상황]")
    for label, nutrients, reason in result["reasons"]:
        names = ", ".join(NUTRIENTS[n]["name"] for n in nutrients)
        L.append(f"  · {label}: {names}")
        L.append(f"      이유: {reason}")

    L.append("\n[참고하면 좋은 영양소] (여러 조건에 겹칠수록 위로)")
    basis = result.get("nutrient_basis", {})
    for n in result["nutrients"]:
        info = NUTRIENTS[n]
        conds = basis.get(n, [])
        cond_labels = ", ".join(sorted(set(label for label, _ in conds)))
        L.append(f"  · {info['name']} — 음식: {info['food']}")
        if cond_labels:
            L.append(f"      관련 이유: {cond_labels} 조건에 해당")
        L.append(f"      주의: {info['caution']}")

    if result["drug_warnings"]:
        L.append("\n[복용약과의 상호작용 주의]")
        for nutrient_name, msg in result["drug_warnings"]:
            L.append(f"  · {nutrient_name}: {msg}")

    L.append("\n" + "-" * 62)
    L.append("※ 이 안내는 '치료·예방'이 아니라 일반적인 영양 정보 참고입니다.")
    L.append("※ 결핍 여부는 혈액검사로 확인하고, 보충 전 약사·의사와 상담하세요.")
    L.append("※ 영양소도 과하면 해로울 수 있습니다. 특정 제품 추천이 아닙니다.")
    return "\n".join(L)


if __name__ == "__main__":
    # 예시: 교대근무 + 오래앉음 + 30대 + 수면부족 + 와파린 복용
    r = guide(
        occupation_ids=["shift_worker", "sedentary_office"],
        age_band="30s",
        sleep_short=True,
        drug_list=["와파린"],
    )
    print(format_report(r))
