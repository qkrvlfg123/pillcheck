"""
제품명·성분명 → 품목기준코드(ITEM_SEQ) 변환기
=============================================

식약처 '의약품 제품 허가정보' API(DrugPrdtPrmsnInfoService08)로 제품명/영문
성분명을 품목기준코드(ITEM_SEQ)로 바꾼다. 이 코드는 DUR품목정보 API의 itemSeq와
같은 값이라 그대로 DUR 조회(dur_api)에 넘길 수 있다.

실측으로 확인한 동작(2026-11-22):
- End Point: apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService08
- getDrugPrdtPrmsnInq08: 허가 목록 조회. 검색 파라미터
    · item_name      제품명(한글, LIKE 부분검색)
    · item_ingr_name 주성분(**영문**, 예: "Warfarin". 한글은 매칭 안 됨)
  응답 필드: ITEM_SEQ, ITEM_NAME, ITEM_ENG_NAME, ENTP_NAME, ITEM_INGR_NAME(영문),
            CANCEL_NAME(정상/취소), ETC_OTC_CODE 등.
- **중요**: 한글 쿼리는 UTF-8로 인코딩해야 한다. (Windows 셸의 curl 인자는 한글을
  깨뜨려 0건이 되므로, requests/urllib로 UTF-8 호출한다.)

서비스키는 dur_api와 같은 DUR_SERVICE_KEY를 쓴다(.env 또는 환경변수).
정적 캐시(dur_resolve_cache.json)에 결과를 저장해, 다음부터는 API 없이 쓴다
(사용자 요청: 정적 매핑 + 실시간 폴백).

* 제품 성분·허가는 바뀔 수 있다. 최종 확인은 식약처 데이터/약사가 한다.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from dur_api import SERVICE_KEY, _UA  # 같은 키·UA 재사용

BASE = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService08"
LIST_OP = "getDrugPrdtPrmsnInq08"

_CACHE_PATH = os.path.join(os.path.dirname(__file__), "dur_resolve_cache.json")


class ResolveError(Exception):
    pass


def _load_cache():
    if os.path.exists(_CACHE_PATH):
        try:
            with open(_CACHE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _save_cache(cache):
    with open(_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


_CACHE = _load_cache()


def _get(params, retries=2):
    if not SERVICE_KEY:
        raise ResolveError("DUR_SERVICE_KEY 없음 — dur_client/.env 또는 환경변수 설정 필요")
    q = {"serviceKey": SERVICE_KEY, "type": "json", "numOfRows": 50, "pageNo": 1}
    q.update(params)
    url = f"{BASE}/{LIST_OP}?" + urllib.parse.urlencode(q)  # 한글 UTF-8 인코딩
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    import time
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
            break
        except urllib.error.HTTPError as e:
            if e.code in (500, 502, 503) and attempt < retries:
                time.sleep(0.6 * (attempt + 1))
                continue
            raise ResolveError(f"HTTP {e.code}") from e
        except urllib.error.URLError as e:
            if attempt < retries:
                time.sleep(0.6 * (attempt + 1))
                continue
            raise ResolveError(f"네트워크 오류: {e}") from e
    data = json.loads(raw)
    if "OpenAPI_ServiceResponse" in data:
        hdr = data["OpenAPI_ServiceResponse"].get("cmmMsgHeader", {})
        raise ResolveError(f"서비스 오류: {hdr.get('errMsg')}")
    body = data.get("body") or {}
    items = body.get("items") or []
    if isinstance(items, dict):
        items = items.get("item", [])
    return items


def _simplify(items):
    """허가정보 원본 항목 → 간단한 형태. 허가취소된 것은 뒤로."""
    out = []
    for it in items:
        out.append({
            "item_seq": it.get("ITEM_SEQ"),
            "item_name": it.get("ITEM_NAME"),
            "ingr_name_eng": it.get("ITEM_INGR_NAME"),
            "entp_name": it.get("ENTP_NAME"),
            "cancelled": (it.get("CANCEL_NAME") not in (None, "", "정상")),
        })
    out.sort(key=lambda x: x["cancelled"])  # 정상 품목 우선
    return out


def resolve_by_product_name(korean_name):
    """제품명(한글)으로 허가 품목 조회. 리스트 반환(정상 품목 우선)."""
    key = f"P::{korean_name}"
    if key in _CACHE:
        return _CACHE[key]
    result = _simplify(_get({"item_name": korean_name}))
    _CACHE[key] = result
    _save_cache(_CACHE)
    return result


def resolve_by_ingredient_eng(eng_ingredient):
    """영문 주성분명으로 허가 품목 조회. 리스트 반환(정상 품목 우선)."""
    key = f"I::{eng_ingredient}"
    if key in _CACHE:
        return _CACHE[key]
    result = _simplify(_get({"item_ingr_name": eng_ingredient}))
    _CACHE[key] = result
    _save_cache(_CACHE)
    return result


def representative_item_seq(korean_name=None, eng_ingredient=None):
    """
    대표 품목기준코드 하나를 반환(정상 품목 우선). 없으면 None.
    제품명 우선 조회 후, 없으면 영문 성분명으로.
    """
    cands = []
    if korean_name:
        cands = resolve_by_product_name(korean_name)
    if not cands and eng_ingredient:
        cands = resolve_by_ingredient_eng(eng_ingredient)
    for c in cands:
        if not c["cancelled"] and c["item_seq"]:
            return c["item_seq"]
    return cands[0]["item_seq"] if cands else None


if __name__ == "__main__":
    import functools
    print = functools.partial(print, flush=True)
    try:
        for name in ["타이레놀", "노바스크", "쿠파린정5밀리그램"]:
            r = resolve_by_product_name(name)
            top = r[0] if r else None
            print(f"[제품] {name:16} → {len(r)}건, 대표 ITEM_SEQ={top['item_seq'] if top else None} ({top['item_name'] if top else '없음'})")
        for eng in ["Warfarin", "Simvastatin"]:
            r = resolve_by_ingredient_eng(eng)
            top = next((x for x in r if not x["cancelled"]), r[0] if r else None)
            print(f"[성분] {eng:16} → {len(r)}건, 대표 ITEM_SEQ={top['item_seq'] if top else None} ({top['item_name'] if top else '없음'})")
    except ResolveError as e:
        print("[안내]", e)
