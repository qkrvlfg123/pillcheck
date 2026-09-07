"""
제품명 → 성분 해석기
====================

사용자가 '게보린', '이지엔6에이스' 같은 제품명을 입력하면 주성분으로 바꾼다.
같은 브랜드도 종류별로 성분이 다를 수 있으므로(예: 이지엔6 시리즈) 제품 단위로
매핑한다.

해석 순서:
  1순위 - 로컬 검증 매핑(product_ingredient_map.json) — 흔한 제품, 오프라인 동작
  2순위 - 식약처 e약은요/의약품허가정보 API — 매핑에 없는 제품 실시간 조회

* 제품 성분은 리뉴얼로 바뀔 수 있다. 최종 확인은 식약처 API/약사가 한다.
"""

import json
import os
import sys

HERE = os.path.dirname(__file__)
DATA_DIR = os.path.join(HERE, "..", "data")
DUR_DIR = os.path.join(HERE)  # e약은요 클라이언트도 dur_client에 둔다


def _load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


_PRODUCT_MAP = _load("product_ingredient_map.json")["products"]

# e약은요 API는 선택적 (서비스키 없으면 로컬만)
try:
    from edrug_api import lookup_product_ingredients  # noqa
    _EDRUG_AVAILABLE = True
except Exception:
    _EDRUG_AVAILABLE = False


def resolve_product(query):
    """
    제품명 → {"product", "ingredients", "ingredient_tags", "source", ...} 또는 None.
    로컬 매핑 우선, 없으면 식약처 API(가능 시).
    """
    q = query.strip()

    # 1순위: 로컬 검증 매핑 (제품명·별칭 부분매칭)
    for p in _PRODUCT_MAP:
        names = [p["product"]] + p.get("aliases", [])
        for name in names:
            if q == name or q in name or name in q:
                return {**p, "resolved_by": "local_map"}

    # 2순위: 식약처 e약은요 API
    if _EDRUG_AVAILABLE and os.environ.get("DUR_SERVICE_KEY"):
        try:
            api_result = lookup_product_ingredients(q)
            if api_result:
                return {**api_result, "resolved_by": "mfds_api"}
        except Exception:
            pass

    return None


def resolve_many(queries):
    """여러 제품명을 한 번에 해석. (해석된 것, 못 찾은 것) 반환."""
    resolved, unresolved = [], []
    for q in queries:
        r = resolve_product(q)
        if r:
            resolved.append((q, r))
        else:
            unresolved.append(q)
    return resolved, unresolved


if __name__ == "__main__":
    tests = ["게보린", "타이레놀", "이지엔6에이스", "이지엔6프로", "판피린큐", "은교산", "듣보약"]
    for t in tests:
        r = resolve_product(t)
        if r:
            print(f"{t:12} → 성분 {r['ingredients']} / 태그 {r['ingredient_tags']} ({r['resolved_by']})")
        else:
            print(f"{t:12} → 못 찾음 (식약처 API 연동 시 조회 가능)")
