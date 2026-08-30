"""
식약처 DUR(의약품안전사용서비스) API 클라이언트
================================================

이 플랫폼의 약물 상호작용 판정은 **식약처 공식 DUR 데이터**가 담당한다.
이 모듈은 임의 판단을 하지 않는다 — 오직 식약처 API를 조회해서 그 결과를
그대로 전달할 뿐이다.

제공 기능(엔드포인트):
- 병용금기       getUsjntTabooInfoList03
- 노인주의       getElderlyCautionInfoList03
- 특정연령대금기  getSpcifyAgrdeTabooInfoList03
- 임부금기       getPwnmTabooInfoList03
- 용량주의       getCpctyAtentInfoList03
- 투여기간주의    getMdctnPdAtentInfoList03
- 효능군중복주의  getEfcyDplctInfoList03
- 서방정분할주의  getSeobangjeongPartitnAtentInfoList03

기준 서비스: DURPrdlstInfoService03
요청 호스트: https://apis.data.go.kr/1471000/DURPrdlstInfoService03/

* 이 파일은 API 연동 코드다. 실제 조회에는 data.go.kr에서 발급받은 서비스키가
  필요하다(무료, 개발계정 자동승인). 환경변수 DUR_SERVICE_KEY 로 주입한다.
* 의료기기가 아니며 진단·처방을 하지 않는다. 식약처 공식 데이터를 '조회'해
  전달하는 참고용이며, 최종 판단은 의사·약사가 한다.
* DB 미등재가 안전을 의미하지 않는다 — 등재되지 않은 위험이 있을 수 있다.
"""

import os
import requests

BASE = "https://apis.data.go.kr/1471000/DURPrdlstInfoService03"
SERVICE_KEY = os.environ.get("DUR_SERVICE_KEY", "")

ENDPOINTS = {
    "병용금기": "getUsjntTabooInfoList03",
    "노인주의": "getElderlyCautionInfoList03",
    "특정연령대금기": "getSpcifyAgrdeTabooInfoList03",
    "임부금기": "getPwnmTabooInfoList03",
    "용량주의": "getCpctyAtentInfoList03",
    "투여기간주의": "getMdctnPdAtentInfoList03",
    "효능군중복주의": "getEfcyDplctInfoList03",
    "서방정분할주의": "getSeobangjeongPartitnAtentInfoList03",
}


class DURError(Exception):
    pass


def _call(endpoint, params):
    if not SERVICE_KEY:
        raise DURError(
            "DUR_SERVICE_KEY 환경변수가 없습니다. "
            "data.go.kr에서 'DUR품목정보' 활용신청 후 서비스키를 설정하세요."
        )
    url = f"{BASE}/{endpoint}"
    q = {"serviceKey": SERVICE_KEY, "type": "json", "numOfRows": 100, "pageNo": 1}
    q.update(params)
    resp = requests.get(url, params=q, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    # 공공데이터포털 표준 응답 구조 파싱
    body = data.get("body") or data.get("response", {}).get("body", {})
    items = body.get("items", [])
    if isinstance(items, dict):  # 단건이면 dict로 오는 경우
        items = items.get("item", [])
    return items


def check_combination_taboo(ingredient_name):
    """
    병용금기 조회: 특정 성분과 함께 쓰면 안 되는 성분을 식약처 DB에서 조회.
    ingredient_name: 주성분명 (예: "와파린", "Warfarin")
    반환: 식약처가 등록한 병용금기 항목 리스트 (가공하지 않은 공식 데이터)
    각 항목에는 대개 다음이 포함됨:
      - 대상 성분 / 함께 금기인 성분
      - 금기 사유(PROHBT_CONTENT)
      - 고시일자 등
    """
    return _call(ENDPOINTS["병용금기"], {"ingrKorName": ingredient_name})


def check_elderly_caution(ingredient_name):
    """노인주의 조회: 고령자에게 주의가 필요한 성분인지 식약처 DB에서 확인."""
    return _call(ENDPOINTS["노인주의"], {"ingrKorName": ingredient_name})


def check_age_taboo(ingredient_name):
    """특정연령대금기 조회(예: 소아 금기 등)."""
    return _call(ENDPOINTS["특정연령대금기"], {"ingrKorName": ingredient_name})


def check_all(ingredient_name):
    """
    한 성분에 대해 주요 안전 정보를 한 번에 조회.
    반환: {"병용금기": [...], "노인주의": [...], "특정연령대금기": [...]}
    각 값은 식약처 공식 데이터 그대로. 이 함수는 판정하지 않고 '조회'만 한다.
    """
    return {
        "병용금기": check_combination_taboo(ingredient_name),
        "노인주의": check_elderly_caution(ingredient_name),
        "특정연령대금기": check_age_taboo(ingredient_name),
    }


if __name__ == "__main__":
    # 실제 실행에는 서비스키가 필요하다.
    # 예: DUR_SERVICE_KEY=... python3 dur_api.py
    try:
        result = check_combination_taboo("와파린")
        print(f"식약처 병용금기 조회 결과: {len(result)}건")
        for item in result[:5]:
            print(" -", item)
    except DURError as e:
        print("[안내]", e)
        print("이 파일은 실제 서비스키가 있을 때 식약처 공식 데이터를 조회합니다.")
