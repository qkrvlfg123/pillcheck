"""
식약처 e약은요 / 의약품 제품허가정보 API 클라이언트
==================================================

로컬 제품 매핑에 없는 제품명을 식약처 공식 데이터로 조회한다.

- 의약품개요정보(e약은요): 제품명·주성분·효능·상호작용·주의사항 등
  요청 예: apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList
- 의약품 제품허가정보: 품목명·주성분 조회

실제 조회에는 data.go.kr에서 발급받은 서비스키(DUR_SERVICE_KEY 재사용 가능)가
필요하다. 키가 없으면 로컬 매핑만으로 동작한다.

* 제품 성분은 리뉴얼로 바뀔 수 있으므로 최신은 API로 확인한다.
"""

import os
import requests

EDRUG_BASE = "https://apis.data.go.kr/1471000/DrbEasyDrugInfoService"
SERVICE_KEY = os.environ.get("DUR_SERVICE_KEY", "")


def lookup_product_ingredients(product_name):
    """
    제품명으로 e약은요를 조회해 주성분 정보를 반환.
    반환: {"product", "ingredients", "ingredient_tags", "source", "raw"} 또는 None.

    주의: e약은요는 성분을 자연어 텍스트로 주는 경우가 많아, 태그(ingredient_tags)
    자동 부여는 제한적이다. 정확한 태깅이 필요하면 성분명을 로컬 규칙과 대조한다.
    """
    if not SERVICE_KEY:
        return None
    url = f"{EDRUG_BASE}/getDrbEasyDrugList"
    params = {
        "serviceKey": SERVICE_KEY,
        "itemName": product_name,
        "type": "json",
        "numOfRows": 3,
        "pageNo": 1,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    body = data.get("body", {})
    items = body.get("items", [])
    if not items:
        return None
    item = items[0]
    return {
        "product": item.get("itemName", product_name),
        # e약은요는 주성분을 별도 필드로 항상 주진 않으므로 원본을 함께 보관
        "ingredients": [item.get("itemName", "")],
        "ingredient_tags": [],  # 태그는 성분명 확인 후 로컬 규칙으로 부여 필요
        "source": "식약처 e약은요",
        "raw": item,
    }


if __name__ == "__main__":
    if not SERVICE_KEY:
        print("[안내] DUR_SERVICE_KEY 미설정 — e약은요 조회를 건너뜁니다.")
        print("로컬 매핑(product_ingredient_map.json)만으로도 흔한 제품은 동작합니다.")
    else:
        r = lookup_product_ingredients("타이레놀")
        print(r)
