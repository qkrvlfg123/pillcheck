"""
식약처 DUR(의약품안전사용서비스) 품목정보 API 클라이언트
=========================================================

식약처 공식 DUR 데이터를 조회해 그대로 전달한다. 이 모듈은 자체 판단을 하지
않는다 — 식약처 API 결과를 정규화해서 넘길 뿐이다.

중요(실측으로 확인된 API 동작, 2026-11-22):
- 기준 서비스: DURPrdlstInfoService03
  End Point: https://apis.data.go.kr/1471000/DURPrdlstInfoService03
- 이 API는 **코드로만** 필터링된다. 실제로 동작하는 필터는 다음뿐이다:
    · itemSeq  (품목기준코드)      예: "200000913"
    · ingrCode (DUR 성분코드)      예: "D000027"(심바스타틴)
  한글 성분명(ingrName/ingrKorName 등)과 itemName(부분검색)은 **동작하지 않는다**
  (무시되어 전체가 반환되거나 0건). 따라서 제품명은 먼저 품목기준코드로
  바꿔야 한다(product_resolver / e약은요 참고).
- 한 품목의 병용금기는 상대 품목 단위로 중복 나열되므로(품목 폭증),
  상호작용 판정에는 MIXTURE_INGR_CODE(상대 성분코드)로 중복 제거해서 쓴다.

요청에는 data.go.kr에서 발급받은 서비스키가 필요하다. 환경변수 DUR_SERVICE_KEY
또는 이 디렉터리의 .env(DUR_SERVICE_KEY=...) 로 주입한다(.env는 커밋 금지).

* 의료기기가 아니며 진단·처방을 하지 않는다. 식약처 공식 데이터를 조회해 전달하는
  참고용이며, 최종 판단은 의사·약사가 한다.
* DB 미등재가 안전을 의미하지 않는다 — 등재되지 않은 위험이 있을 수 있다.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://apis.data.go.kr/1471000/DURPrdlstInfoService03"
_UA = "pillcheck-dur-client/1.0"

# 실제 승인 상세기능에서 확인한 오퍼레이션명 (2026-11-22)
ENDPOINTS = {
    "병용금기": "getUsjntTabooInfoList03",
    "노인주의": "getOdsnAtentInfoList03",            # (스캐폴드의 getElderlyCautionInfoList03 는 오류였음)
    "특정연령대금기": "getSpcifyAgrdeTabooInfoList03",
    "임부금기": "getPwnmTabooInfoList03",
    "용량주의": "getCpctyAtentInfoList03",
    "투여기간주의": "getMdctnPdAtentInfoList03",
    "효능군중복주의": "getEfcyDplctInfoList03",
    "서방정분할주의": "getSeobangjeongPartitnAtentInfoList03",
    "DUR품목정보": "getDurPrdlstInfoList03",
}

# 단일 품목(itemSeq)으로 조회 가능한, 품목 자체에 대한 주의 유형
CAUTION_TYPES = [
    "노인주의",
    "특정연령대금기",
    "임부금기",
    "용량주의",
    "투여기간주의",
    "효능군중복주의",
    "서방정분할주의",
]


class DURError(Exception):
    pass


def _load_service_key():
    key = os.environ.get("DUR_SERVICE_KEY", "").strip()
    if key:
        return key
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "DUR_SERVICE_KEY":
                    return v.strip()
    return ""


SERVICE_KEY = _load_service_key()


def _get(endpoint, params, _retries=2):
    """엔드포인트를 호출해 응답 body(dict)를 반환. 오류면 DURError."""
    if not SERVICE_KEY:
        raise DURError(
            "DUR_SERVICE_KEY 가 없습니다. data.go.kr에서 'DUR품목정보'를 활용신청한 뒤 "
            "환경변수 DUR_SERVICE_KEY 또는 dur_client/.env 에 서비스키를 넣으세요."
        )
    q = {"serviceKey": SERVICE_KEY, "type": "json", "numOfRows": 100, "pageNo": 1}
    q.update(params)
    url = f"{BASE}/{endpoint}?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    last_err = None
    for attempt in range(_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
            break
        except urllib.error.HTTPError as e:
            # data.go.kr은 일시적으로 500을 반환하는 경우가 있다 → 재시도
            last_err = e
            if e.code in (500, 502, 503) and attempt < _retries:
                time.sleep(0.6 * (attempt + 1))
                continue
            detail = ""
            try:
                detail = e.read(300).decode("utf-8", "replace").replace("\n", " ").strip()
            except Exception:
                pass
            raise DURError(f"HTTP {e.code} 오류: {endpoint} :: {detail[:200]}") from e
        except urllib.error.URLError as e:
            last_err = e
            if attempt < _retries:
                time.sleep(0.6 * (attempt + 1))
                continue
            raise DURError(f"네트워크 오류: {e}") from e
    else:  # pragma: no cover
        raise DURError(f"요청 실패: {last_err}")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise DURError(f"JSON 파싱 실패: {raw[:200]}") from e

    # 공공데이터포털 오류 응답 형태
    if "OpenAPI_ServiceResponse" in data:
        hdr = data["OpenAPI_ServiceResponse"].get("cmmMsgHeader", {})
        raise DURError(
            f"서비스 오류: {hdr.get('errMsg')} / {hdr.get('returnAuthMsg')} "
            f"(code {hdr.get('returnReasonCode')})"
        )
    header = data.get("header") or {}
    code = header.get("resultCode")
    if code not in (None, "00"):
        raise DURError(f"resultCode={code} {header.get('resultMsg')}")
    return data.get("body") or {}


def _iter_items(endpoint, params, max_pages=40):
    """페이지네이션하며 items를 순회."""
    page = 1
    while page <= max_pages:
        body = _get(endpoint, {**params, "pageNo": page})
        total = body.get("totalCount") or 0
        items = body.get("items") or []
        if isinstance(items, dict):  # 단건이면 dict로 오는 경우
            items = items.get("item", [])
        if not items:
            break
        for it in items:
            yield it
        if page * 100 >= total:
            break
        page += 1


# ── 병용금기(두 성분을 함께 쓰면 안 되는 조합) ──────────────────────────

def taboo_partners_by_item_seq(item_seq):
    """
    품목기준코드(itemSeq)로 병용금기 상대 성분을 중복 제거해 반환.
    반환: [{"ingr_code","ingr_name","reason","base_ingr_code","base_ingr_name"}, ...]
    (ingr_code = 함께 쓰면 안 되는 상대 성분의 DUR 코드)
    """
    out = {}
    for it in _iter_items(ENDPOINTS["병용금기"], {"itemSeq": str(item_seq)}):
        code = it.get("MIXTURE_INGR_CODE")
        if code and code not in out:
            out[code] = {
                "ingr_code": code,
                "ingr_name": it.get("MIXTURE_INGR_KOR_NAME"),
                "reason": it.get("PROHBT_CONTENT"),
                "base_ingr_code": it.get("INGR_CODE"),
                "base_ingr_name": it.get("INGR_KOR_NAME"),
            }
    return list(out.values())


def taboo_partners_by_ingr_code(ingr_code):
    """DUR 성분코드(ingrCode)로 병용금기 상대 성분을 중복 제거해 반환."""
    out = {}
    for it in _iter_items(ENDPOINTS["병용금기"], {"ingrCode": str(ingr_code)}):
        code = it.get("MIXTURE_INGR_CODE")
        if code and code not in out:
            out[code] = {
                "ingr_code": code,
                "ingr_name": it.get("MIXTURE_INGR_KOR_NAME"),
                "reason": it.get("PROHBT_CONTENT"),
                "base_ingr_code": it.get("INGR_CODE"),
                "base_ingr_name": it.get("INGR_KOR_NAME"),
            }
    return list(out.values())


def own_ingr_codes_by_item_seq(item_seq):
    """
    해당 품목의 주성분 DUR 코드 집합을 반환.
    병용금기 응답의 INGR_CODE(기준 성분)에서 수집한다. 병용금기 등재가 없으면
    DUR품목정보 조회로 보완한다.
    """
    codes = {}
    for it in _iter_items(ENDPOINTS["병용금기"], {"itemSeq": str(item_seq)}, max_pages=3):
        c = it.get("INGR_CODE")
        if c:
            codes[c] = it.get("INGR_KOR_NAME")
    if codes:
        return codes
    for it in _iter_items(ENDPOINTS["DUR품목정보"], {"itemSeq": str(item_seq)}, max_pages=3):
        c = it.get("INGR_CODE")
        if c:
            codes[c] = it.get("INGR_KOR_NAME")
    return codes


# ── 품목 단위 주의(노인주의/임부금기/용량주의 등) ───────────────────────

def cautions_by_item_seq(item_seq, types=None):
    """
    품목기준코드로 단일 품목 주의 유형을 조회.
    반환: {"노인주의":[...], "임부금기":[...], ...} (각 값은 식약처 원본 항목 리스트)
    """
    types = types or CAUTION_TYPES
    result = {}
    for t in types:
        rows = list(_iter_items(ENDPOINTS[t], {"itemSeq": str(item_seq)}, max_pages=5))
        if rows:
            result[t] = rows
    return result


# ── 상호작용 판정(여러 품목을 함께 복용할 때) ───────────────────────────

def check_combination(items):
    """
    여러 품목을 함께 복용할 때의 병용금기를 식약처 데이터로 대조.
    items: {라벨: 품목기준코드} 매핑. 예: {"쿠마딘정": "199500000", ...}
    반환: [{"a","b","reason"}] — a, b는 라벨, reason은 식약처 금기 사유.

    각 품목의 주성분 코드 집합과 병용금기 파트너 집합을 구해, 한쪽의 파트너에
    다른 쪽의 주성분이 들어 있으면 병용금기로 본다.
    """
    labels = list(items.keys())
    own = {}
    partners = {}
    for label in labels:
        seq = items[label]
        own[label] = set(own_ingr_codes_by_item_seq(seq).keys())
        partners[label] = {p["ingr_code"]: p["reason"] for p in taboo_partners_by_item_seq(seq)}

    hits = []
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            a, b = labels[i], labels[j]
            reason = None
            shared = own[b] & set(partners[a].keys())
            if shared:
                reason = partners[a][next(iter(shared))]
            else:
                shared = own[a] & set(partners[b].keys())
                if shared:
                    reason = partners[b][next(iter(shared))]
            if reason:
                hits.append({"a": a, "b": b, "reason": reason})
    return hits


if __name__ == "__main__":
    # 라이브 데모 (실제 서비스키 필요)
    import functools
    print = functools.partial(print, flush=True)  # 버퍼링 방지
    try:
        print("[1] 이트라코나졸 품목(itemSeq=200000913)의 병용금기 상대 성분:")
        partners = taboo_partners_by_item_seq("200000913")
        print(f"    고유 파트너 성분 {len(partners)}개")
        for p in partners[:6]:
            print(f"      - {p['ingr_name']} ({p['ingr_code']}) => {p['reason']}")
        print("[2] 품목 자체 주의(itemSeq=200000913) 유형:")
        c = cautions_by_item_seq("200000913", types=["노인주의", "임부금기", "용량주의"])
        for t, rows in c.items():
            print(f"      - {t}: {len(rows)}건")
        if not c:
            print("      - (해당 없음)")
    except DURError as e:
        print("[안내]", e)
